"""Trip 账本（任务书第 5 节）：清零快照的本地持久账。

「汽车小计」的完整隐喻还差一块：清零前的那段旅程应该记进总账本，而不是
一笔勾销。账本与 TripStore 同目录、同生命周期：

* **写入时机**：清零（含撤销过期后的落定）时，把清零前的读数存成一册。
* **数字一致性**：账册数字直接取自 TripStore.summary() 的清零前快照，
  与界面上显示的是同一份数据——「账本数字与清零前显示完全一致」由构造保证。
* **恢复为当前区间**：把账册读数写回 Trip 对应段（撤销的等价物）。
* **仅存本机**：JSON 文件随数据目录，无上传、无自动清理；导出 CSV 由
  bridge 层完成（这里给纯数据）。

ODO 总里程不在这里：它 = 日志累计（ActivityLog 全量口径），永不落盘、
永不清零，UI 直接读 activity 汇总——「总里程必须等于日志累计」由同源
保证，不需要第二份账。
"""
from __future__ import annotations

import csv
import copy
import io
import json
import threading
import time
import uuid
from pathlib import Path

from storage import atomic_write

LEDGER_FILE = "microglow-relay-trip-ledger.json"
LEDGER_VERSION = 1


class TripLedger:
    """清零快照账本。数字从 TripStore 来，回到 TripStore 去。"""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / LEDGER_FILE
        self.lock = threading.RLock()
        self._entries = self._load()

    # ------------------------------------------------------------------ 存储
    def _load(self) -> list[dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return []
        if not isinstance(data, dict) or data.get("version") != LEDGER_VERSION:
            return []
        entries = data.get("entries")
        return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []

    def _save(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        atomic_write(self.path, json.dumps(
            {"version": LEDGER_VERSION, "entries": self._entries},
            ensure_ascii=False, indent=1))

    # ------------------------------------------------------------------ 操作
    def snapshot(self, key: str, trip_summary: dict) -> dict:
        """清零前调用：把某段的当前读数存成一册，返回账册（含 id 与起止时间）。

        ``trip_summary`` 就是 ``TripStore.summary()`` ——同一份数据，
        保证账册数字与界面清零前显示完全一致。整包 scopes（全局/Codex/Claude
        三口径）一并存档：恢复时三本账一起回来，口径选择也原样保留。
        """
        slot = trip_summary.get(key) if isinstance(trip_summary, dict) else None
        if not isinstance(slot, dict):
            raise ValueError("snapshot 需要 TripStore.summary() 的快照")
        started = slot.get("started_at")
        scopes = slot.get("scopes") if isinstance(slot.get("scopes"), dict) else {}
        entry = {
            "id": "led-" + uuid.uuid4().hex[:12],
            "key": key,
            "name": str(slot.get("name") or "")[:12],
            "scope": slot.get("scope") or "all",
            "created_at": time.time(),
            "from": None if started is None else float(started),
            "to": time.time(),
            "input_tokens": int(slot.get("input_tokens") or 0),
            "output_tokens": int(slot.get("output_tokens") or 0),
            "cached_input_tokens": int(slot.get("cached_input_tokens") or 0),
            "cache_creation_tokens": int(slot.get("cache_creation_tokens") or 0),
            "elapsed": slot.get("elapsed"),
            "reset_at": slot.get("reset_at"),
            "details_complete": bool(slot.get("details_complete", False)),
            "requests": int(slot.get("requests") or 0),
            # 三口径读数全量存档（旧版账册没有：读取侧按顶层字段兜底）。
            "scopes": copy.deepcopy(scopes),
            # 模型占比与化解次数：由调用方从日志聚合补充（可选字段）。
            "models": copy.deepcopy(slot.get("models") or {}),
            "mitigated": int(slot.get("mitigated") or 0),
        }
        with self.lock:
            self._entries.append(entry)
            self._save()
        return entry

    def entries(self, key: str | None = None) -> list[dict]:
        """全部账册；指定 key 只返回该段的（最新在前）。"""
        with self.lock:
            items = list(self._entries)
        if key is not None:
            items = [entry for entry in items if entry.get("key") == key]
        return list(reversed(items))

    def rename(self, entry_id: str, name: str) -> bool:
        with self.lock:
            for entry in self._entries:
                if entry.get("id") == entry_id:
                    entry["name"] = str(name).strip()[:12]
                    self._save()
                    return True
        return False

    def delete(self, entry_id: str) -> bool:
        with self.lock:
            before = len(self._entries)
            self._entries = [entry for entry in self._entries if entry.get("id") != entry_id]
            if len(self._entries) != before:
                self._save()
                return True
        return False

    def restore(self, entry_id: str, trip_store) -> bool:
        """把账册读数恢复为对应 Trip 段的当前读数（撤销的等价物）。

        v2 账册带整包 scopes：三本账 + 口径一起原样写回；恢复动作本身不改
        账册（账册是历史，不是状态）。旧版账册（无 scopes）只有总量——
        写回会破坏分桶，这种情况不恢复计数，只把口径与清零时刻带回去。
        """
        with self.lock:
            entry = next((e for e in self._entries if e.get("id") == entry_id), None)
        if entry is None:
            return False
        scopes = copy.deepcopy(entry.get("scopes") or {})
        if not scopes:
            # Legacy entries have one selected reading, not protocol-level detail.
            scope = entry.get("scope") or "all"
            scopes["anthropic" if scope == "anthropic" else "responses"] = dict(
                entry, started_at=entry.get("from"), elapsed=entry.get("elapsed") or
                max(0, (entry.get("to") or 0) - (entry.get("from") or entry.get("to") or 0)))
        current = trip_store.summary()
        if int(current[entry["key"]].get("tokens") or 0):
            self.snapshot(entry["key"], current)
        trip_store.restore_reading(entry["key"], {
            "reset_at": time.time(),  # Do not replay requests from the intervening gap.
            "resume_at": time.time(),
            "scope": entry.get("scope") or "all",
            "name": entry.get("name") or "",
            "scopes": scopes,
        })
        self.delete(entry_id)
        return True

    def to_csv(self, entries: list[dict] | None = None) -> str:
        """导出 CSV 文本（UTF-8 with BOM，Excel 直接打开不乱码）。"""
        scope_labels = {"all": "全局", "responses": "Codex", "anthropic": "Claude"}
        rows = entries if entries is not None else self.entries()
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(("区间名称", "段落", "口径", "开始时间", "结束时间", "时长（秒）",
                         "新输入 Token", "输出 Token", "缓存读取 Token", "缓存写入 Token",
                         "总 Token", "请求数", "化解波动", "模型占比"))
        for entry in rows:
            incoming = int(entry.get("input_tokens") or 0)
            outgoing = int(entry.get("output_tokens") or 0)
            started = entry.get("from")
            models = entry.get("models") or {}
            model_total = sum(int(v.get("tokens") or 0) for v in models.values())
            shares = {name: dict(value, share=int(value.get("tokens") or 0) / model_total if model_total else 0)
                      for name, value in models.items()}
            writer.writerow((
                entry.get("name") or "",
                entry.get("key") or "",
                scope_labels.get(entry.get("scope") or "all", "全局"),
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started)) if started else "尚未开始",
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("to") or 0)),
                int(entry.get("elapsed") or max(0, (entry.get("to") or 0) - (started or entry.get("to") or 0))),
                max(0, incoming - int(entry.get("cached_input_tokens") or 0)) if "cached_input_tokens" in entry else "", outgoing,
                entry.get("cached_input_tokens", ""),
                entry.get("cache_creation_tokens", ""), incoming + outgoing,
                int(entry.get("requests") or 0),
                int(entry.get("mitigated") or 0) if entry.get("details_complete") else "",
                json.dumps(shares, ensure_ascii=False) if entry.get("details_complete") else "",
            ))
        return "\ufeff" + buffer.getvalue()
