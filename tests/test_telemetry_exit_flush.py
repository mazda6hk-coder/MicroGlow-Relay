"""退出上传预算：积压批次不得传到一半被进程退出掐断（MG-TELEMETRY-EXIT-FLUSH-001）。"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from server import Gateway, TELEMETRY_EXIT_JOIN_SECONDS  # noqa: E402
from storage import Settings  # noqa: E402
from telemetry import HttpTelemetryUploadClient, UploadResponse  # noqa: E402
from telemetry.consent import CONSENT_VERSION_V2  # noqa: E402
from telemetry.runtime import (  # noqa: E402
    TELEMETRY_EXIT_UPLOAD_SECONDS,
    TELEMETRY_MIN_UPLOAD_SECONDS,
    TelemetryRuntime,
)


class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = json.dumps(body).encode("utf-8")

    def read(self, size=-1):
        return self._body

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _SlowClient:
    """Records every attempt and answers with a valid ACK after ``delay``."""

    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.called = []
        self.timeouts = []

    def upload(self, payload):
        self.called.append(payload)
        if self.delay:
            time.sleep(self.delay)
        return UploadResponse(status_code=202, body={"ack": True, "batch_id": payload["batch_id"]})


class _BudgetAwareClient(_SlowClient):
    """Transport-style client that accepts the remaining per-batch budget."""

    def upload(self, payload, timeout=None):
        self.timeouts.append(timeout)
        return super().upload(payload)


def _seed_pending(runtime: TelemetryRuntime, count: int) -> list[str]:
    runtime.consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
    batch_ids = []
    for index in range(count):
        batch_id = f"batch_exit_fixture_{index}"
        payload = {"schema_version": 2, "batch_id": batch_id,
                   "aggregated_rows": [{"provider": "openai"}]}
        with runtime.database.connect() as connection:
            connection.execute("INSERT INTO batches VALUES (?, 'pending', ?, 'now', 'now')",
                               (batch_id, json.dumps(payload)))
        batch_ids.append(batch_id)
    return batch_ids


class ExitBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="relay-exit-flush-")
        self.path = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_exit_budget_covers_a_real_backlog_of_slow_batches(self):
        # 单批公网实测 1.3~2.5 秒，预算必须明显大于旧的 3 秒窗口。
        self.assertGreaterEqual(TELEMETRY_EXIT_UPLOAD_SECONDS, 15.0)
        self.assertLessEqual(TELEMETRY_MIN_UPLOAD_SECONDS, 3.0)
        self.assertGreater(TELEMETRY_EXIT_UPLOAD_SECONDS, TELEMETRY_MIN_UPLOAD_SECONDS)

    def test_upload_deadline_stops_before_starting_unaffordable_batches(self):
        runtime = TelemetryRuntime(self.path, "5.0")
        _seed_pending(runtime, 5)
        client = _SlowClient(delay=1.0)
        runtime.uploader = client

        acknowledged = runtime.upload_pending(deadline=time.monotonic() + 2.5)

        self.assertLessEqual(acknowledged, 3)
        self.assertEqual(len(client.called), acknowledged)
        leftover = runtime.batches.list_retryable()
        self.assertTrue(leftover, "未跑完的批次必须保留待下次重试")
        for batch in leftover:
            self.assertEqual(batch["state"], "pending",
                             "退出时没轮到的批次不得停在 uploading")

    def test_exhausted_budget_never_starts_a_batch(self):
        runtime = TelemetryRuntime(self.path, "5.0")
        _seed_pending(runtime, 2)
        client = _SlowClient()
        runtime.uploader = client

        self.assertEqual(runtime.upload_pending(deadline=time.monotonic() + 0.5), 0)
        self.assertEqual(client.called, [])
        self.assertEqual(len(runtime.batches.list_retryable()), 2)

    def test_remaining_budget_is_handed_to_budget_aware_transports(self):
        runtime = TelemetryRuntime(self.path, "5.0")
        _seed_pending(runtime, 1)
        client = _BudgetAwareClient()
        runtime.uploader = client

        self.assertEqual(runtime.flush(timeout=6.0), 1)
        self.assertEqual(len(client.timeouts), 1)
        self.assertIsNotNone(client.timeouts[0])
        self.assertGreater(client.timeouts[0], 0)
        self.assertLessEqual(client.timeouts[0], 6.0)

    def test_legacy_uploader_without_timeout_parameter_still_works(self):
        runtime = TelemetryRuntime(self.path, "5.0")
        _seed_pending(runtime, 1)
        client = _SlowClient()
        runtime.uploader = client

        self.assertEqual(runtime.flush(timeout=6.0), 1)
        self.assertEqual(len(client.called), 1)


class ExitThreadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="relay-exit-thread-")
        self.path = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_exit_upload_runs_on_a_non_daemon_thread(self):
        gateway = Gateway(Settings(self.path))
        seen = {}

        class _Runtime:
            def flush(self):
                seen["thread"] = threading.current_thread()

        gateway.telemetry = _Runtime()
        gateway.shutdown()

        self.assertIn("thread", seen)
        self.assertFalse(seen["thread"].daemon,
                         "守护线程会在解释器退出时被掐断，批次只能传一半")
        self.assertEqual(seen["thread"].name, "microglow-telemetry-exit-upload")

    def test_exit_returns_quickly_then_drains_the_whole_backlog(self):
        gateway = Gateway(Settings(self.path))
        runtime = gateway.telemetry
        _seed_pending(runtime, 6)
        # 每批 0.3 秒：六批合计 1.8 秒，仍长于 1.5 秒的同步 join 窗口，
        # 但远小于 20 秒的退出上传预算。原先的 0.8 秒（合计 4.8 秒）在整机
        # 满载、测试吞吐下降数倍时会逼近预算上限，制造与产品行为无关的偶发失败。
        runtime.uploader = _SlowClient(delay=0.3)

        started = time.monotonic()
        gateway.shutdown()
        self.assertLess(time.monotonic() - started, 2.0,
                        "退出不得为了上传把界面卡满整段预算")
        self.assertLessEqual(TELEMETRY_EXIT_JOIN_SECONDS, 2.0)

        # 等待窗口必须包住退出线程的完整预算（20 秒），否则会在产品自己
        # 的截止时刻附近产生两个时钟的竞态。
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline and runtime.batches.list_retryable():
            time.sleep(0.1)
        self.assertEqual(runtime.batches.list_retryable(), [],
                         "退出线程必须把积压批次跑完，而不是只跑前一两批")

    def test_shutdown_is_still_idempotent_and_silent_on_failure(self):
        gateway = Gateway(Settings(self.path))
        calls = []

        class _Runtime:
            def flush(self):
                calls.append(1)
                raise OSError("synthetic failure")

        gateway.telemetry = _Runtime()
        gateway.shutdown()
        gateway.shutdown()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and len(calls) < 1:
            time.sleep(0.05)
        self.assertEqual(len(calls), 1)


class TransportTimeoutTests(unittest.TestCase):
    def test_upload_accepts_a_budget_override(self):
        captured = {}

        def opener(http_request, timeout):
            captured["timeout"] = timeout
            return _FakeResponse(202, {"ack": True, "batch_id": "batch_fixture"})

        client = HttpTelemetryUploadClient("5.0", opener=opener)
        response = client.upload({"batch_id": "batch_fixture"}, timeout=3.5)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(captured["timeout"], 3.5)

    def test_upload_keeps_configured_timeout_when_none_is_given(self):
        captured = {}

        def opener(http_request, timeout):
            captured["timeout"] = timeout
            return _FakeResponse(202, {"ack": True, "batch_id": "batch_fixture"})

        client = HttpTelemetryUploadClient("5.0", timeout=9.0, opener=opener)
        client.upload({"batch_id": "batch_fixture"})

        self.assertEqual(captured["timeout"], 9.0)


if __name__ == "__main__":
    unittest.main()
