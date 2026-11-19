"""Non-blocking, failure-isolated adapter used by the Router."""
from __future__ import annotations

from datetime import datetime, timezone
import inspect
from pathlib import Path
from queue import Empty, Full, Queue
import threading
import time

from .consent import CONSENT_VERSION_V2, TelemetryConsent
from .channel import CHANNELS
from .store import TelemetryAggregator, TelemetryBatchStore, TelemetryDatabase, error_category_for_status


# 正常退出的整段上传预算（秒）。单批实测约 1.3~2.5 秒（公网 TLS + POST +
# 入库），旧值把预算压在 3 秒内，积压批次常常传到一半就被进程退出掐断。
TELEMETRY_EXIT_UPLOAD_SECONDS = 20.0
# 剩下的时间不够跑完一批就不要开新批次，留到下一次正常退出重试。
TELEMETRY_MIN_UPLOAD_SECONDS = 2.0


def _accepts_timeout(uploader) -> bool:
    """传输实现可选地接受 ``timeout``；测试替身只实现 ``upload(payload)``。"""
    try:
        parameters = inspect.signature(uploader.upload).parameters
    except (TypeError, ValueError, AttributeError):
        return False
    if "timeout" in parameters:
        return True
    return any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )


class TelemetryRuntime:
    """Queues fixed counters so request threads never perform telemetry I/O."""

    def __init__(
        self,
        directory: Path,
        client_version: str,
        uploader=None,
    ):
        self.directory = Path(directory)
        self.client_version = client_version
        self.uploader = uploader
        self.consent = TelemetryConsent(self.directory)
        self.database = TelemetryDatabase(self.directory)
        self.aggregator = TelemetryAggregator(self.database, self.consent)
        self.batches = TelemetryBatchStore(self.database, self.consent)
        self.queue: Queue[dict] = Queue(maxsize=2048)
        self._worker = threading.Thread(target=self._run, daemon=True, name="microglow-telemetry-local")
        self._worker.start()

    @classmethod
    def create_isolated(
        cls,
        directory: Path,
        client_version: str,
        uploader=None,
    ) -> "TelemetryRuntime | DisabledTelemetryRuntime":
        try:
            return cls(
                directory, client_version,
                uploader=uploader,
            )
        except Exception:
            DisabledTelemetryRuntime.write_safe_error(directory, "TELEMETRY_INIT_FAILED")
            return DisabledTelemetryRuntime(directory)

    def enabled(self) -> bool:
        try:
            return self.consent.is_granted(2)
        except Exception:
            self._safe_error("CONSENT_READ_FAILED")
            return False

    def set_consent(self, enabled: bool) -> bool:
        try:
            if enabled:
                self.consent.grant(2, CONSENT_VERSION_V2)
            else:
                self.consent.withdraw()
            return self.enabled() == bool(enabled)
        except Exception:
            self._safe_error("CONSENT_WRITE_FAILED")
            return False

    def record_request(
        self,
        *,
        provider: str,
        status: int,
        elapsed_seconds: float,
        model: str | None = None,
        model_family: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        fallback: bool = False,
        active_minutes: int = 0,
        call_channel: str = "unknown",
    ) -> bool:
        """Queue an allow-listed counter event; no profile or request object is accepted."""
        if not self.enabled():
            return False
        if call_channel not in CHANNELS:
            return False
        event = {
            "client_version": self.client_version,
            "provider": provider,
            "model": model,
            "model_family": model_family,
            "successful": 200 <= int(status) < 300,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "elapsed_seconds": elapsed_seconds,
            "error_category": None if 200 <= int(status) < 300 else error_category_for_status(status),
            "fallback": bool(fallback),
            "active_minutes": active_minutes,
            "call_channel": call_channel,
            "occurred_at": datetime.now(timezone.utc),
        }
        try:
            self.queue.put_nowait(event)
            return True
        except Full:
            self._safe_error("AGGREGATE_QUEUE_FULL")
            return False

    def _run(self) -> None:
        while True:
            try:
                event = self.queue.get(timeout=0.5)
            except Empty:
                continue
            if event is None:       # stop() 的哨兵：退出循环
                self.queue.task_done()
                return
            try:
                self.aggregator.record_request(**event)
            except Exception:
                self._safe_error("AGGREGATE_WRITE_FAILED")
            finally:
                self.queue.task_done()

    def stop(self, timeout: float = 1.0) -> None:
        """让本地聚合线程退出（不发网络请求）。

        没有这一步，每构造一次 Gateway 就多一条永不退出的守护线程，
        并且都攥着各自目录里的 SQLite 连接。应用内只有一条 Gateway 时
        看不出来；测试/反复启停时是几十条线程与已删目录的文件句柄，
        会在退出阶段之外的时间点给进程带来 C 层访问冲突。
        """
        worker = getattr(self, "_worker", None)
        if worker is None or not worker.is_alive():
            return
        try:
            self.queue.put_nowait(None)
        except Full:
            pass
        worker.join(timeout=max(0.0, float(timeout)))

    def checkpoint(self, timeout: float = 0.25) -> dict | None:
        """Best-effort local sealing only; this method never performs network I/O."""
        deadline = time.monotonic() + max(0.0, timeout)
        while self.queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.005)
        if self.queue.unfinished_tasks:
            self._safe_error("CHECKPOINT_TIMEOUT")
            return None
        try:
            return self.batches.create_pending(2)
        except Exception:
            self._safe_error("BATCH_CREATE_FAILED")
            return None

    def upload_pending(self, schema_version: int = 2, deadline: float | None = None) -> int:
        """Best-effort upload of retryable batches; never raises, returns acked count.

        ``deadline`` 是 ``time.monotonic()`` 的绝对时刻。预算用尽时直接停下，
        未处理的批次保持 pending，等待下一次正常退出重试，而不是传到一半被掐断。
        """
        if self.uploader is None:
            return 0
        try:
            if not self.consent.upload_is_granted(schema_version):
                return 0
        except Exception:
            self._safe_error("CONSENT_READ_FAILED")
            return 0
        acknowledged = 0
        try:
            batches = self.batches.list_retryable(schema_version)
        except Exception:
            self._safe_error("BATCH_LIST_FAILED")
            return 0
        for batch in batches:
            # ``list_retryable`` yields ``read()`` records, so the identifier lives
            # inside the payload; the top-level lookup stays for flattened callers.
            payload = batch.get("payload")
            if not isinstance(payload, dict):
                continue
            # Country is server-derived. Never rewrite a sealed batch.
            if any(isinstance(row, dict) and "country_code" in row
                   for row in payload.get("aggregated_rows", [])):
                continue
            batch_id = str(payload.get("batch_id") or batch.get("batch_id") or "")
            if not batch_id:
                continue
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining < TELEMETRY_MIN_UPLOAD_SECONDS:
                break
            try:
                self.batches.set_state(batch_id, "uploading")
                if remaining is None or not _accepts_timeout(self.uploader):
                    response = self.uploader.upload(payload)
                else:
                    response = self.uploader.upload(payload, timeout=remaining)
                if self.batches.apply_upload_response(batch_id, response):
                    acknowledged += 1
            except Exception:
                self._safe_error("UPLOAD_FAILED")
                try:
                    self.batches.set_state(batch_id, "pending")
                except Exception:
                    pass
        return acknowledged

    def flush(self, timeout: float = TELEMETRY_EXIT_UPLOAD_SECONDS) -> int:
        """本地封批 + 一次有截止时间的上传；用于正常退出。"""
        budget = max(0.0, float(timeout))
        self.checkpoint(timeout=min(0.25, budget))
        return self.upload_pending(deadline=time.monotonic() + budget)

    def _safe_error(self, code: str) -> None:
        self.write_safe_error(self.directory, code)

    @staticmethod
    def write_safe_error(directory: Path, code: str) -> None:
        try:
            path = Path(directory) / "telemetry-safe-errors.log"
            if path.exists() and path.stat().st_size > 32_768:
                path.replace(path.with_suffix(".previous.log"))
            with path.open("a", encoding="utf-8", newline="\n") as file:
                file.write(datetime.now(timezone.utc).isoformat() + " " + code + "\n")
        except Exception:
            pass


class DisabledTelemetryRuntime:
    """No-op fallback used when local telemetry storage cannot initialize."""

    write_safe_error = staticmethod(TelemetryRuntime.write_safe_error)

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.batches = None

    def enabled(self) -> bool:
        return False

    def set_consent(self, enabled: bool) -> bool:
        return False

    def record_request(self, **_values) -> bool:
        return False

    def checkpoint(self, timeout: float = 0.25) -> None:
        return None

    def upload_pending(self, schema_version: int = 2, deadline: float | None = None) -> int:
        return 0

    def flush(self, timeout: float = TELEMETRY_EXIT_UPLOAD_SECONDS) -> int:
        return 0

    def stop(self, timeout: float = 1.0) -> None:
        """无后台线程，停止即空操作（与 TelemetryRuntime 接口对齐）。"""
        return None
