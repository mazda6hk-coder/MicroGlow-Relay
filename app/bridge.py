# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Bridge between the reusable core (``src``) and the Qt interface.

Everything here runs on the GUI thread apart from the worker pool used for
network calls such as ``fetch_models`` and ``probe_profile``.
"""
from __future__ import annotations

from collections import deque
from datetime import date
from pathlib import Path
import time

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot

from codex_config import (
    STATUS_ACTIVE,
    STATUS_DRIFTED,
    STATUS_NONE,
    codex_view,
    export_files,
    integrate,
    integration_conflicts,
    integration_status,
    refresh_catalog_if_active,
    receipt_path,
    restore_native,
)
import claude_config
from session_compat.rpc import ensure_codex_closed, CodexRunningError, CompatibilityError
from server import fetch_models, probe_profile
from telemetry import CONSENT_VERSION_V2, TelemetryConsent

from .i18n import tr, trf


class _TaskHub(QObject):
    """进程级任务派发中枢：worker 只投递，回调一律回主线程执行。

    为什么不用"每个任务自己挂一对信号"：跨线程 emit 时若页面/窗口已经销毁，
    PySide 那边回调是裸 lambda，没有 receiver 可供 Qt 自动断开连接，worker
    线程于是直接调用已析构的控件——Python 侧的 try/except 兜不住 C++ 级
    崩溃，表现为进程 139（offscreen 批量测试里被放大，真机上"关窗瞬间
    后台还在拉模型"同样会踩）。

    改成 worker → 中枢（主线程、进程级永生）→ 队列事件 → 主线程调用回调：
    控件销毁与回调调用从此都在主线程串行，最坏只得到一次 RuntimeError，
    静默丢弃即可。
    """

    delivery = Signal(object)

    def __init__(self):
        super().__init__()
        self.delivery.connect(self._deliver)

    @Slot(object)
    def _deliver(self, pack) -> None:
        try:
            pack["callback"](pack["value"])
        except RuntimeError:
            pass          # 控件已销毁：结果无人认领，丢弃
        except Exception:  # noqa: BLE001 - 记录但不污染事件循环
            import traceback
            traceback.print_exc()


_HUB: "_TaskHub | None" = None


def task_hub() -> "_TaskHub":
    """取派发中枢（首次调用须在主线程，即 Bridge 构造时）。"""
    global _HUB
    if _HUB is None:
        _HUB = _TaskHub()
    return _HUB


class Task(QRunnable):
    """Runs a blocking callable and hands the result to the hub."""

    def __init__(self, payload, callbacks=None):
        super().__init__()
        self.payload = payload
        self._callbacks = callbacks or {}

    def run(self):
        try:
            value = self.payload()
            kind = "finished"
        except Exception as error:  # noqa: BLE001 - forwarded to the UI
            value, kind = error, "failed"
        try:
            from shiboken6 import isValid
            hub = task_hub()
            if not isValid(hub):
                return
        except RuntimeError:
            return
        for callback in self._callbacks.get(kind, ()):
            try:
                hub.delivery.emit({"kind": kind, "value": value,
                                   "callback": callback})
            except RuntimeError:
                return


class Bridge(QObject):
    """Owns the settings store, the local gateway and all derived UI state."""

    models_changed = Signal()
    events_appended = Signal(list)
    io_changed = Signal(bool)
    service_changed = Signal()
    status_changed = Signal(str)
    busy_changed = Signal(bool)
    task_finished = Signal(object)
    task_failed = Signal(object)

    POLL_INTERVAL = 150
    # 状态轮询只做「Codex 配置是否仍指向本路由」的存在性判断，30 秒足够灵敏；
    # 每次轮询要读 config.toml + receipt 两个文件，不宜放在秒级节奏上反复做。
    STATUS_INTERVAL = 30_000
    EVENT_LIMIT = 600

    def __init__(self, settings, gateway):
        super().__init__()
        self.settings = settings
        self.gateway = gateway
        self.events: deque[dict] = deque(maxlen=self.EVENT_LIMIT)
        self._incoming: deque[dict] = deque()
        self._queue_box = []
        self._pool = QThreadPool.globalInstance()
        task_hub()          # 暖一下：中枢必须在主线程创建，队列才能落在主线程
        self._last_io = (0, 0)
        self._io_hot_until = 0.0
        self._io_state = False
        self._live_tasks = 0
        self.compatibility_busy = False
        try:
            self.telemetry_consent = TelemetryConsent(self.settings.directory)
        except Exception:  # Telemetry state must never block the application.
            self.telemetry_consent = None

        self.gateway.subscribe(self._collect)
        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_INTERVAL)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

        # Codex 的配置可能被其它工具改写，必须持续确认自己还在生效。
        self._status = self.status()
        self._claude_status = self.claude_status()
        if self._claude_status == STATUS_ACTIVE:
            # 老 receipt（没有上下文窗口键）在这里补写一次，升级后不用重新接入。
            self._sync_claude_context()
            self._note_claude_overrides()
        self._codex_running = self.codex_running()
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(self.STATUS_INTERVAL)
        self._status_timer.timeout.connect(self._watch_status)
        self._status_timer.start()

    @Slot()
    def _watch_status(self) -> None:
        codex_running = self.codex_running()
        if codex_running != self._codex_running:
            self._codex_running = codex_running
            self.service_changed.emit()
        current = self.status()
        codex_changed = current != self._status
        if codex_changed:
            previous, self._status = self._status, current
            if current == STATUS_DRIFTED:
                self.gateway.log("warning", tr("接入已失效") + " · " + tr("让 Codex 使用 Relay"))
            elif current == STATUS_ACTIVE:
                self.gateway.log("success", tr("Codex 已重新指向本路由器"))
            elif previous == STATUS_ACTIVE:
                self.gateway.log("warning", tr("Codex 已不再使用本路由器"))
            self.status_changed.emit(current)
            self.models_changed.emit()
        if codex_changed or self._watch_claude_status():
            self.service_changed.emit()

    def _watch_claude_status(self) -> bool:
        """Claude Code 的 settings.json 同样可能被外部改写，与 Codex 同款盯梢。"""
        current = self.claude_status()
        if current == self._claude_status:
            return False
        previous, self._claude_status = self._claude_status, current
        if current == STATUS_DRIFTED:
            self.gateway.log("warning", tr("接入已失效") + " · " + tr("让 Claude Code 使用 Relay"))
        elif current == STATUS_ACTIVE and previous != STATUS_ACTIVE:
            self.gateway.log("success", tr("Claude Code 已重新指向本路由器"))
        return True

    # ---------------------------------------------------------------- events
    def _collect(self, event: dict) -> None:
        """Called from gateway threads; only buffers, never touches widgets."""
        self._incoming.append(event)

    @Slot()
    def _poll(self) -> None:
        incoming = []
        while self._incoming:
            try:
                incoming.append(self._incoming.popleft())
            except IndexError:
                break
        if incoming:
            for event in incoming:
                self.events.append(event)
            self.events_appended.emit(incoming)

        current = (self.gateway.input_bytes, self.gateway.output_bytes)
        if current != self._last_io:
            self._last_io = current
            self._io_hot_until = time.monotonic() + 0.4
        hot = time.monotonic() < self._io_hot_until
        if hot != self._io_state:
            self._io_state = hot
            self.io_changed.emit(hot)

    # ------------------------------------------------------------- settings
    def theme(self) -> str:
        """当前主题组合键（如 spring-day）；旧键读写时自动迁移。"""
        from .theme import migrate_theme

        with self.settings.lock:
            value = str(self.settings.data.get("theme") or "spring-day")
            migrated = migrate_theme(value)
            if migrated != value:
                self.settings.data["theme"] = migrated
                self.settings.save()
            return migrated

    def set_theme(self, name: str) -> None:
        from .theme import migrate_theme

        with self.settings.lock:
            self.settings.data["theme"] = migrate_theme(name)
            self.settings.save()

    def day_night_mode(self) -> str:
        """昼夜偏好（system/day/night），与皮肤键分开存。"""
        from .theme import DAY_NIGHT_CHOICES

        with self.settings.lock:
            value = str(self.settings.data.get("day_night") or "day")
            return value if value in DAY_NIGHT_CHOICES else "day"

    def set_day_night_mode(self, mode: str) -> None:
        from .theme import DAY_NIGHT_CHOICES

        if mode not in DAY_NIGHT_CHOICES:
            return
        with self.settings.lock:
            self.settings.data["day_night"] = mode
            self.settings.save()

    def language(self) -> str:
        from .i18n import LANGUAGE_CODES

        with self.settings.lock:
            value = str(self.settings.data.get("language") or "en")
            return value if value in LANGUAGE_CODES else "en"

    def set_language(self, code: str) -> None:
        from .i18n import LANGUAGE_CODES

        if code not in LANGUAGE_CODES:
            raise ValueError(code)
        with self.settings.lock:
            self.settings.data["language"] = code
            self.settings.save()

    def port(self) -> int:
        return int(self.settings.snapshot()["port"])

    def is_busy(self) -> bool:
        """是否有后台任务在跑（模型发现、探测、会话备份等都走同一队列）。"""
        return self._live_tasks > 0

    # ---------------------------------------------------------------- tasks
    def run(self, payload, on_done=None, on_error=None) -> None:
        self._live_tasks += 1
        self.busy_changed.emit(True)
        callbacks = {"finished": [self._on_finished],
                     "failed": [self._on_failed]}
        if on_done is not None:
            callbacks["finished"].append(on_done)
        if on_error is not None:
            callbacks["failed"].append(on_error)
        task = Task(payload, callbacks)
        self._queue_box.append(task)
        callbacks["finished"].append(lambda _value, t=task: self._forget(t))
        callbacks["failed"].append(lambda _error, t=task: self._forget(t))
        self._pool.start(task)

    def _release(self) -> None:
        self._live_tasks = max(0, self._live_tasks - 1)
        if self._live_tasks == 0:
            self.busy_changed.emit(False)

    @Slot(object)
    def _on_finished(self, value) -> None:
        self._release()
        self.task_finished.emit(value)

    @Slot(object)
    def _on_failed(self, error) -> None:
        self._release()
        self.task_failed.emit(error)

    @Slot(object)
    def _forget(self, task) -> None:
        """任务完成后把它从保活列表里删掉，否则 _queue_box 只增不减。"""
        try:
            self._queue_box.remove(task)
        except ValueError:
            pass

    # -------------------------------------------------------------- profiles
    def profiles(self) -> list[dict]:
        return self.settings.profiles()

    def profile(self, profile_id: str, include_key: bool = False) -> dict:
        return self.settings.profile(profile_id, include_key=include_key)

    def selected(self):
        try:
            return self.settings.selected()
        except ValueError:
            return None

    def _sync_claude_context(self) -> None:
        """模型目录变了：同步 Claude Code 的「上下文窗口」声明。

        接入中的 settings.json 里有一个值随「当前生效模型」变化
        （`CLAUDE_CODE_MAX_CONTEXT_TOKENS`）。切换默认模型、改 input_tokens
        之后必须立刻重写并刷新 receipt，否则下一次状态轮询会把我们自己写进去的
        值当成外部篡改，报一个假的「配置漂移」。
        """
        try:
            claude_config.sync_context_window(self.settings)
        except Exception:  # noqa: BLE001 - 同步失败不该让保存流程失败
            pass

    def save_profile(self, profile: dict, api_key: str | None = None) -> dict:
        saved = self.settings.upsert(profile, api_key)
        refresh_catalog_if_active(self.settings)
        self._sync_claude_context()
        self.models_changed.emit()
        return saved

    def select_profile(self, profile_id: str) -> None:
        self.settings.select(profile_id)
        refresh_catalog_if_active(self.settings)
        self._sync_claude_context()
        self.models_changed.emit()

    def save_profiles(self, profiles: list[dict], api_key: str, channel_keys=None) -> list[dict]:
        saved = self.settings.upsert_many(profiles, api_key, channel_keys=channel_keys)
        refresh_catalog_if_active(self.settings)
        self._sync_claude_context()
        self.models_changed.emit()
        return saved

    def save_channel_models(self, profile_id: str, index: int,
                            profiles: list[dict], api_key: str) -> list[dict]:
        saved = self.settings.upsert_channel_models(profile_id, index, profiles, api_key)
        refresh_catalog_if_active(self.settings)
        self._sync_claude_context()
        self.models_changed.emit()
        return saved

    def delete_profile(self, profile_id: str) -> None:
        self.settings.delete(profile_id)
        refresh_catalog_if_active(self.settings)
        self._sync_claude_context()
        self.models_changed.emit()

    # ---------------------------------------------------- channels（0.9 渠道组）
    def update_channels(self, profile_id: str, channels: list[dict],
                        channel_keys: list[str] | None = None) -> dict:
        """替换一个模型配置的渠道组（整体替换语义，与渠道编辑器的表单对应）。

        channels 为空列表 = 回退单渠道语义（主 base_url/api_key 接管）。
        """
        profile = self.settings.profile(profile_id)
        updated = dict(profile, channels=channels)
        saved = self.settings.upsert(updated, None, channel_keys=channel_keys)
        refresh_catalog_if_active(self.settings)
        self._sync_claude_context()
        self.models_changed.emit()
        return saved

    def channel_health(self) -> dict[str, list[dict]]:
        """全部模型配置的渠道健康快照（UI 模型页展开行用）。

        返回 {profile_id: [{index, label, healthy, cooldown_seconds}]}；
        冷却中的渠道 healthy=False 且带剩余秒数。数据来自网关内存路由器
        ——重启即视为全部健康，与路由行为一致。
        """
        cooling = self.gateway.channel_router.cooling()
        now = __import__("time").monotonic()
        snapshot: dict[str, list[dict]] = {}
        for profile in self.settings.profiles():
            channels = profile.get("channels") or []
            if not channels:
                continue
            entries = []
            for index, channel in enumerate(channels):
                deadline = cooling.get((profile["id"], index), cooling.get(index, 0.0))
                entries.append({
                    "index": index,
                    "label": channel.get("label") or f"渠道 {index + 1}",
                    "weight": int(channel.get("weight") or 1),
                    "enabled": bool(channel.get("enabled", True)),
                    "healthy": deadline <= now,
                    "cooldown_seconds": max(0, round(deadline - now)) if deadline > now else 0,
                })
            snapshot[profile["id"]] = entries
        return snapshot

    def set_port(self, port: int) -> None:
        self.settings.set_port(port)

    # ------------------------------------------------------- autostart / 更新
    def autostart_enabled(self) -> bool:
        from . import autostart

        return autostart.is_enabled()

    def autostart_supported(self) -> bool:
        from . import autostart

        return autostart.supported()

    def set_autostart(self, enabled: bool) -> bool:
        from . import autostart

        return autostart.set_enabled(enabled)

    def auto_update_enabled(self) -> bool:
        """自动检查更新（任务书 8.1）：默认开启，每天启动最多一次。"""
        try:
            return bool(self.settings.data.get("auto_update", True))
        except Exception:  # noqa: BLE001 - 读失败按默认值
            return True

    def set_auto_update(self, enabled: bool) -> bool:
        try:
            self.settings.data["auto_update"] = bool(enabled)
            self.settings.save()
            return self.auto_update_enabled()
        except Exception:  # noqa: BLE001 - 写失败如实返回当前值
            return self.auto_update_enabled()

    def last_update_check(self) -> str:
        try:
            return str(self.settings.data.get("last_update_check") or "")
        except Exception:  # noqa: BLE001
            return ""

    def mark_update_checked(self) -> None:
        import time

        try:
            self.settings.data["last_update_check"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.settings.save()
        except Exception:  # noqa: BLE001 - 时间戳失败不影响检查
            pass

    def telemetry_enabled(self) -> bool:
        try:
            return bool(self.telemetry_consent and self.telemetry_consent.is_granted(2))
        except Exception:
            return False

    def telemetry_upload_enabled(self) -> bool:
        try:
            return bool(self.telemetry_consent and self.telemetry_consent.upload_is_granted(2))
        except Exception:
            return False

    def telemetry_preview_payload(self):
        """The actual first upload-eligible sealed batch, without network I/O."""
        if not self.telemetry_upload_enabled():
            return None
        runtime = getattr(self.gateway, "telemetry", None)
        if runtime is None or getattr(runtime, "batches", None) is None:
            return None
        runtime.checkpoint()
        for batch in runtime.batches.list_retryable(2):
            payload = batch.get("payload")
            if isinstance(payload, dict) and not any("country_code" in row for row in payload.get("aggregated_rows", [])):
                return payload
        return None

    def set_telemetry_consent(self, enabled: bool) -> bool:
        """Persist an explicit choice without touching Router state."""
        try:
            if self.telemetry_consent is None:
                return False
            if enabled:
                self.telemetry_consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
            else:
                self.telemetry_consent.withdraw()
            return self.telemetry_enabled() == bool(enabled)
        except Exception:
            return False

    # --------------------------------------------------------------- service
    def start_service(self, port: int | None = None) -> None:
        self.gateway.start(port)
        self.service_changed.emit()

    def stop_service(self) -> None:
        self.gateway.stop()
        self.service_changed.emit()

    def connect_codex(self) -> str:
        ensure_codex_closed()
        if not self.settings.profiles():
            raise ValueError(tr("请先保存至少一个模型配置。"))
        state = self.status()
        started_here = False
        try:
            if not self.gateway.running:
                self.gateway.start()
                started_here = True
            if state == STATUS_NONE:
                backup = integrate(self.settings)
                return trf('Codex 已接入 · 已备份 {0}', backup.name)
            if state == STATUS_DRIFTED:
                backup = integrate(self.settings, force=True)
                return trf('Codex 已重新接入 · 已备份 {0}', backup.name)
            export_files(self.settings)
            return tr("接入信息已刷新")
        except Exception:
            if started_here:
                self.gateway.stop()
            raise
        finally:
            self.service_changed.emit()

    def stop_access(self) -> None:
        self.gateway.stop()
        self.service_changed.emit()

    def restore_codex(self, force: bool = False) -> str:
        restore_native(self.settings)
        # 另一家客户端还接着时不能停共享服务，否则 Claude 的请求会跟着断。
        if not claude_config.is_integrated(self.settings):
            self.gateway.stop()
        self.service_changed.emit()
        return tr("已切回原生 Codex")

    # ------------------------------------------------------------------ Claude
    def claude_status(self) -> str:
        """``none`` | ``active`` | ``drifted`` — from the live Claude settings."""
        return claude_config.integration_status(self.settings)

    def claude_target(self) -> dict:
        return claude_config.claude_view(self.settings)

    def claude_conflicts(self) -> list[str]:
        return claude_config.integration_conflicts(self.settings)

    def claude_high_priority_sources(self) -> list[str]:
        """优先级高于用户级 settings.json、但 Relay 不去改的文件。"""
        try:
            return claude_config.high_priority_sources(self.settings)
        except Exception:  # noqa: BLE001 - 探测失败只是少一条提示
            return []

    def _note_claude_overrides(self) -> None:
        """企业策略/项目级配置会架空接入：只记一条 Info，不阻塞任何流程。"""
        for path in self.claude_high_priority_sources():
            self.gateway.log("info", trf(
                "检测到更高优先级的 Claude 配置：{0} · 可能覆盖 Relay 接入，未改动", path))

    def claude_restore_pending(self) -> bool:
        return claude_config.receipt_path(self.settings).exists()

    def connect_claude(self) -> str:
        """接入 Claude Code。settings.json 只在启动时读取，运行中的会话要重启才生效。"""
        if not self.settings.profiles():
            raise ValueError(tr("请先保存至少一个模型配置。"))
        state = self.claude_status()
        started_here = False
        try:
            if not self.gateway.running:
                self.gateway.start()
                started_here = True
            if state == STATUS_NONE:
                backup = claude_config.integrate(self.settings)
                self._note_claude_overrides()
                return trf('Claude Code 已接入 · 已备份 {0}', backup.name)
            if state == STATUS_DRIFTED:
                backup = claude_config.integrate(self.settings, force=True)
                self._note_claude_overrides()
                return trf('Claude Code 已重新接入 · 已备份 {0}', backup.name)
            claude_config.sync_context_window(self.settings)
            self._note_claude_overrides()
            return tr("接入信息已刷新")
        except Exception:
            if started_here:
                self.gateway.stop()
            raise
        finally:
            self.service_changed.emit()

    def restore_claude(self, force: bool = False) -> str:
        claude_config.restore(self.settings, force=force)
        # Codex 还接着时不能停共享服务，否则 Codex 的请求会跟着断。
        if not self.integrated():
            self.gateway.stop()
        self.service_changed.emit()
        return tr("已恢复 Claude Code 配置")

    def connection_restore_pending(self) -> bool:
        return receipt_path(self.settings).exists()

    def restore_on_exit(self) -> None:
        # Keep the gateway available until every pending client is restored.
        # Shell only stops it after this method succeeds; errors remain retryable.
        errors = []
        if self.connection_restore_pending():
            try:
                restore_native(self.settings)
            except Exception as error:
                errors.append(f"Codex: {error}")
        if self.claude_restore_pending():
            try:
                claude_config.restore(self.settings, force=True)
            except Exception as error:
                errors.append(f"Claude Code: {error}")
        if errors:
            raise RuntimeError("\n".join(errors))

    def status(self) -> str:
        """``none`` | ``active`` | ``drifted`` — from the live Codex config."""
        return integration_status(self.settings)

    def codex_target(self) -> dict:
        return codex_view(self.settings)

    def codex_conflicts(self) -> list[str]:
        return integration_conflicts(self.settings)

    def resync_codex_catalog(self) -> bool:
        """把当前模型目录重新写入 Codex 侧文件。

        增删改模型配置时 bridge 已自动热更新；这里给用户一个显式入口，
        用于手工改过 models.json 或换Codex 版本后重新对齐。
        """
        return refresh_catalog_if_active(self.settings)

    def integrated(self) -> bool:
        return self.status() == STATUS_ACTIVE

    def codex_running(self) -> bool:
        """Read process names only; an unavailable check must not light the lamp."""
        try:
            ensure_codex_closed()
        except CodexRunningError:
            return True
        except CompatibilityError:
            return False
        return False

    def local_url(self) -> str:
        return f"http://127.0.0.1:{self.port()}/v1"

    def today_stats(self) -> dict:
        return self.gateway.activity.today()

    def day_stats(self, day) -> dict:
        """任意一天的汇总（requests/success/tokens 等）；读取失败给空 dict。"""
        try:
            return self.gateway.activity.range_summary(day, day)
        except Exception:  # noqa: BLE001 - 统计展示绝不允许打穿页面
            return {}

    def token_series(self, limit: int = 24) -> list[float]:
        """最近 N 笔请求的 Token（入+出），按时间先后排列——走势图数据。"""
        try:
            rows = self.gateway.activity.recent(limit)
        except Exception:  # noqa: BLE001
            return []
        series = [int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0)
                  for row in rows]
        series.reverse()
        return series

    def recent_activity(self, limit: int = 8) -> list[dict]:
        return self.gateway.activity.recent(limit)

    def trip_stats(self) -> dict:
        """TRIP A/B 的当前读数。只读内存，不碰磁盘，可以随刷新反复调用。"""
        return self.gateway.activity.trip_summary()

    def odo_stats(self) -> dict:
        """总里程 ODO：全量累计（自安装以来），永不清零（任务书第 5 节）。

        与日志同源，不设第二份账；days 为陪伴天数（最早记录日至今，含当天）。
        """
        try:
            total = self.gateway.activity.grand_total()
        except Exception:  # noqa: BLE001 - 展示层永不阻塞
            total = {"requests": 0, "tokens": 0, "first_day": None}
        days = 0
        if total.get("first_day"):
            try:
                from datetime import date
                first = date.fromisoformat(total["first_day"])
                days = (date.today() - first).days + 1
            except ValueError:
                days = 0
        return {"tokens": int(total.get("tokens") or 0),
                "requests": int(total.get("requests") or 0),
                "days": days}

    def reset_trip(self, key: str) -> dict:
        """清零一段小计：先快照入账本（撤销凭据），再清零，返回读数。

        账本数字直接取自清零前的 summary()——「账本与清零前显示完全
        一致」由构造保证（任务书第 5 节）。快照含三口径整包与当前口径。
        """
        import time
        reading = self.gateway.activity.trips.summary()[key]
        entry = None
        if int(reading.get("tokens") or 0):
            entry = self.gateway.trip_ledger.snapshot(key, {key: reading})
        if not hasattr(self, "_trip_undo"):
            self._trip_undo = {}
        self._trip_undo[key] = (time.monotonic() + 10, reading, entry)
        return self.gateway.activity.reset_trip(key)

    def rename_trip(self, key: str, name: str) -> dict:
        """给一段小计命名（任务书 5：名称可点击就地编辑，空名显示 A / B）。"""
        return self.gateway.activity.trips.rename(key, name)

    def set_trip_scope(self, key: str, scope: str) -> dict:
        """切换一段小计的读数口径（all/responses/anthropic）。

        三本账并行累计、口径只是视角：切换零重算零丢失，立即落盘，
        重启后 UI 停在用户选的那一档。
        """
        return self.gateway.activity.set_trip_scope(key, scope)

    def undo_reset_trip(self, key: str, reading: dict) -> dict:
        """撤销清零：把快照读数写回该段（等于清零从未发生）。"""
        import time
        pending = getattr(self, "_trip_undo", {}).pop(key, None)
        if pending is None or time.monotonic() > pending[0]:
            return self.trip_stats()
        import copy
        reading = copy.deepcopy(pending[1])
        fresh = self.trip_stats()[key]
        for scope in ("responses", "anthropic"):
            previous = reading["scopes"][scope]
            current = fresh["scopes"][scope]
            for field in ("input_tokens", "output_tokens", "requests", "cached_input_tokens", "cache_creation_tokens", "mitigated"):
                previous[field] = int(previous.get(field) or 0) + int(current.get(field) or 0)
            stamps = [v for v in (previous.get("started_at"), current.get("started_at")) if v is not None]
            previous["started_at"] = min(stamps) if stamps else None
            for model, values in current.get("models", {}).items():
                target = previous.setdefault("models", {}).setdefault(model, {"requests": 0, "tokens": 0})
                for field in ("requests", "tokens"): target[field] += int(values.get(field) or 0)
        result = self.gateway.activity.trips.restore_reading(key, reading)
        if pending[2] is not None:
            self.gateway.trip_ledger.delete(pending[2]["id"])
        return result

    def trip_ledger_entries(self) -> list[dict]:
        return self.gateway.trip_ledger.entries()

    def delete_trip_ledger_entry(self, entry_id: str) -> None:
        self.gateway.trip_ledger.delete(entry_id)

    def rename_trip_ledger_entry(self, entry_id: str, name: str) -> None:
        self.gateway.trip_ledger.rename(entry_id, name)

    def restore_trip_ledger_entry(self, entry_id: str) -> bool:
        entry = next((e for e in self.trip_ledger_entries() if e["id"] == entry_id), None)
        if entry is None:
            return False
        getattr(self, "_trip_undo", {}).pop(entry["key"], None)
        return self.gateway.trip_ledger.restore(entry_id, self.gateway.activity.trips)

    def export_trip_ledger_csv(self, path, entries=None) -> int:
        text = self.gateway.trip_ledger.to_csv(entries)
        Path(path).write_text(text, encoding="utf-8", newline="")
        return len(entries if entries is not None else self.trip_ledger_entries())

    def model_usage(self) -> dict:
        """按模型名的今日真实用量，供模型管理页展示。

        走 range_summary 而非 today()：只有前者带models 分组，
        且与日志页统计同源（持久化日索引），不会因重启而清零。
        """
        today = date.today()
        try:
            stats = self.gateway.activity.range_summary(today, today)
        except Exception:  # noqa: BLE001 - usage display must never break the page
            return {}
        return {name: dict(group) for name, group in (stats.get("models") or {}).items()}

    def clear_events(self) -> None:
        with self.gateway.lock:
            self.gateway.events.clear()
        self.events.clear()
        self._incoming.clear()

    # ------------------------------------------------------------ network IO
    def discover_models(self, profile: dict, on_done, on_error) -> None:
        self.run(lambda: fetch_models(dict(profile)), on_done, on_error)

    def probe(self, profile: dict, api_key: str, on_done, on_error) -> None:
        self.run(lambda: probe_profile(self.settings, dict(profile), api_key), on_done, on_error)

    def log(self, level: str, message: str) -> None:
        self.gateway.log(level, message)
