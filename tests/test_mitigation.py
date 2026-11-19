"""化解波动统计与错误三分类专项（MG-RELAY-MITIGATION-001）。

口径（2026-11-10 与刘总对齐）：
- 按请求计：一次请求被重试/换渠道救活 = 化解 1 次；
- 分项按首次失败原因归类：rate_limit / timeout / unavailable /
  transient_400 / switched_channel；
- 错误三分类 = 已自动化解（救活的）/ 已告知 Agent（最终失败且上游侧
  5xx）/ 需你处理（认证失败、模型不存在、本地配置错）。
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from records import ActivityLog, _empty_bucket, _accumulate  # noqa: E402
from server import Gateway  # noqa: E402
from storage import Settings  # noqa: E402

from test_router import MockSupplier, profile  # noqa: E402


class RowTests(unittest.TestCase):
    def _row(self, **changes):
        row = {"timestamp": 0.0, "time": "2026-11-10 12:00:00", "status": 200,
               "ok": True, "input_tokens": 10, "output_tokens": 5,
               "model": "demo", "elapsed": 0.5}
        row.update(changes)
        return row

    def test_mitigated_row_accumulates_once_per_request(self):
        bucket = _empty_bucket()
        _accumulate(bucket, self._row(mitigated="rate_limit"))
        _accumulate(bucket, self._row(mitigated="rate_limit"))
        _accumulate(bucket, self._row(mitigated="switched_channel"))
        _accumulate(bucket, self._row())     # 直通请求不计
        self.assertEqual(bucket["requests"], 4)
        self.assertEqual(bucket["mitigated"], 3)
        self.assertEqual(bucket["mitigated_by"], {"rate_limit": 2, "switched_channel": 1})

    def test_legacy_rows_without_field_are_ignored(self):
        bucket = _empty_bucket()
        _accumulate(bucket, self._row())     # 老日志行没有 mitigated 列
        self.assertEqual(bucket["mitigated"], 0)
        self.assertEqual(bucket["mitigated_by"], {})


class EndToEndTests(unittest.TestCase):
    """网关端到端：渠道内重试救活的请求带 mitigated 标记落日志。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.supplier = MockSupplier()
        self.settings = Settings(Path(self.temp.name))
        self.settings.upsert(profile(base_url=self.supplier.url + "/chat/completions"), "sk-test")
        self.settings.select(self.settings.snapshot()["profiles"][0]["id"])

    def tearDown(self):
        self.supplier.close()
        self.temp.cleanup()

    def _post(self, gateway):
        import time
        before = len(gateway.activity.recent(100))
        response = httpx.post(
            f"http://127.0.0.1:{gateway.port}/v1/responses",
            headers={"Authorization": "Bearer " + self.settings.local_token()},
            json={"model": "microglow-relay", "input": "hi", "stream": False},
            timeout=60)
        deadline = time.monotonic() + 2
        while len(gateway.activity.recent(100)) <= before and time.monotonic() < deadline:
            time.sleep(.005)
        return response

    def test_retry_rescued_request_is_marked_mitigated(self):
        # 第一发 503 被渠道内重试救活，第二发直通。
        self.supplier.status_sequence = [503, 200, 200]
        gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)
        gateway.start(0)
        try:
            response = self._post(gateway)
            self.assertEqual(response.status_code, 200)
            rows = gateway.activity.recent(10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].get("mitigated"), "unavailable",
                             "503 重试救活应记 unavailable")
            self.assertTrue(rows[0]["ok"])
            # 直通的第二发不带标记。
            self._post(gateway)
            rows = gateway.activity.recent(10)
            self.assertEqual(len(rows), 2)
            self.assertNotIn("mitigated", rows[0])   # recent 倒序：最新在前
            # 日聚合：mitigated 计数 = 1。
            summary = gateway.activity.range_summary(
                __import__("datetime").date.today(), __import__("datetime").date.today())
            self.assertEqual(summary.get("mitigated"), 1)
        finally:
            gateway.stop()

    def test_final_failure_is_not_marked_mitigated(self):
        self.supplier.status = 503     # 持续失败
        gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)
        gateway.start(0)
        try:
            response = self._post(gateway)
            self.assertEqual(response.status_code, 503)
            rows = gateway.activity.recent(10)
            self.assertEqual(len(rows), 1)
            self.assertNotIn("mitigated", rows[0],
                             "最终失败的请求不算化解——救活才算")
        finally:
            gateway.stop()


class ErrorTrichotomyTests(unittest.TestCase):
    """错误三分类的纯函数口径：救活 / 上游侧 / 需用户处理。"""

    def test_classify(self):
        from records import classify_outcome
        # 救活：任何带 mitigated 的成功行。
        self.assertEqual(classify_outcome({"ok": True, "mitigated": "rate_limit"}), "mitigated")
        # 直通成功。
        self.assertEqual(classify_outcome({"ok": True}), "success")
        # 上游侧失败（5xx / 超时 / 不可用）：已告知 Agent。
        self.assertEqual(classify_outcome({"ok": False, "status": 503}), "agent_notified")
        self.assertEqual(classify_outcome({"ok": False, "status": 504}), "agent_notified")
        # 需用户处理：认证、模型不存在、本地配置。
        self.assertEqual(classify_outcome({"ok": False, "status": 401}), "needs_attention")
        self.assertEqual(classify_outcome({"ok": False, "status": 404}), "needs_attention")
        self.assertEqual(classify_outcome({"ok": False, "status": 400}), "needs_attention")


if __name__ == "__main__":
    unittest.main()
