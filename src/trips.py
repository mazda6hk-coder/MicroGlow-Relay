"""分段 Token 计数（TRIP A / B）。

与汽车的小计里程表同构：随时清零，从零累计，跨自然日、跨重启都不中断。
计数口径与 `records.py` 完全一致——读的就是同一份日志行，`input + output`。

计时语义：清零键只把读数归零，**计时器要等本段第一次调用入账才启动**
（`started_at` 记的是那一行日志的时间戳）。清零后一直没有调用，界面显示
"尚未开始"，而不是一个从按键时刻空转的秒表。

**这里的数字只是缓存，真值永远在日志里。** `anchor` 记着每个日志文件已经读到第
几字节，对不上就重扫。因此进程被杀、断电、日志轮转，最多让数字短暂落后，下一次
`sync()` 补回来，不会算错。

两条不能破的规矩：

1. **计数和 anchor 必须在同一次原子写里落盘。** 只写一半，重启后的重扫就会把
   已经算过的行再算一遍，小计凭空变大，而且没人看得出来。
2. **`note_row` 只在 anchor 正好停在写前位置时才推进。** 否则说明中间有本实例
   没读过的行（另一个临时实例写过、或日志被外部追加），此时只标记待同步，把补齐
   交给 `sync()`——宁可晚一步，不能跳着记。
"""

from __future__ import annotations

import json
import copy
import threading
import time
from pathlib import Path

from storage import atomic_write

TRIP_KEYS = ("A", "B")
TRIP_FILE = "microglow-relay-trips.json"
TRIP_VERSION = 2
# 读数口径（UI 三选一）：全局 = 两协议合并；Codex = responses；Claude = anthropic。
# 口径只是**读数的视角**，不是三本独立的账——账按协议分桶并行累计，
# 切换口径零重算、零丢失，随时可以切回来。
TRIP_SCOPES = ("all", "responses", "anthropic")
# 落盘节流：每个请求都 fsync 一次没有必要，丢掉的这几秒会在下次 sync 时从 anchor
# 之后补回来。所以这里可以放心地慢。
SAVE_INTERVAL = 2.0

# 日志行 client 字段的两个真实取值：Claude Code 走 anthropic，其余（Codex 等）
# 走 responses。老日志行没有这列，读取侧按 responses 兜底——与 records.py 同口径。
_CLIENT_KEYS = ("responses", "anthropic")


def _zero_counts() -> dict:
    """一个协议桶的零状态：五项计数 + 本桶自己的计时起点。"""
    return {"input_tokens": 0, "output_tokens": 0, "requests": 0,
            "cached_input_tokens": 0, "cache_creation_tokens": 0,
            "started_at": None, "models": {}, "mitigated": 0,
            "details_complete": True, "paused_seconds": 0.0}


def _clean_counts(raw) -> dict:
    counts = _zero_counts()
    if not isinstance(raw, dict):
        return counts
    for name in ("input_tokens", "output_tokens", "requests",
                 "cached_input_tokens", "cache_creation_tokens", "mitigated"):
        try:
            counts[name] = max(0, int(raw.get(name) or 0))
        except (AttributeError, TypeError, ValueError):
            pass
    started = raw.get("started_at")
    try:
        counts["started_at"] = float(started) if started is not None else None
    except (AttributeError, TypeError, ValueError):
        counts["started_at"] = None
    counts["models"] = copy.deepcopy(raw.get("models") or {})
    counts["details_complete"] = bool(raw.get("details_complete", not counts["requests"]))
    counts["paused_seconds"] = max(0.0, float(raw.get("paused_seconds") or 0))
    return counts


def _merged_counts(buckets: dict) -> dict:
    """全局口径 = 两协议桶合并。计时起点取两桶最早的那笔调用。"""
    parts = [buckets.get(name) or _zero_counts() for name in _CLIENT_KEYS]
    merged = _zero_counts()
    started = [part["started_at"] for part in parts if part["started_at"] is not None]
    merged["started_at"] = min(started) if started else None
    for name in ("input_tokens", "output_tokens", "requests",
                 "cached_input_tokens", "cache_creation_tokens", "mitigated"):
        merged[name] = sum(part.get(name, 0) for part in parts)
    merged["details_complete"] = all(part.get("details_complete", False) for part in parts)
    if merged["started_at"] is not None:
        now = time.time()
        elapsed = max(max(0, now - part["started_at"] - float(part.get("paused_seconds") or 0))
                      for part in parts if part["started_at"] is not None)
        merged["paused_seconds"] = max(0, now - merged["started_at"] - elapsed)
    for part in parts:
        for model, values in part.get("models", {}).items():
            target = merged["models"].setdefault(model, {"requests": 0, "tokens": 0})
            for field in ("requests", "tokens"):
                target[field] += int(values.get(field) or 0)
    return merged


def _empty_trip(reset_at: float, scope: str = "all") -> dict:
    # started_at 不在段级保存：每个协议桶自己记第一笔调用的时间戳，
    # 全局起点由合并派生。清零只是"准备好起跑"，枪声是第一笔调用。
    return {"reset_at": float(reset_at), "scope": scope, "name": "",
            "by_client": {name: _zero_counts() for name in _CLIENT_KEYS}}


class TripStore:
    """A/B 两段独立的小计。各自有自己的清零时刻与累计量。"""

    def __init__(self, directory, *, log_name: str):
        self.directory = Path(directory)
        self.path = self.directory / TRIP_FILE
        self.log_name = log_name
        self.lock = threading.RLock()
        # 文件还不存在 = 这是第一次运行，需要把初始状态写下去；
        # 已存在就先当作干净，避免每次构造实例都白白 fsync 一次。
        self._dirty = not self.path.exists()
        self._saved_at = time.time()
        self._state = self._load()

    # ------------------------------------------------------------------ 读取

    def _blank(self) -> dict:
        """全新安装：两段都从此刻开始计，显示 0，和汽车小计出厂状态一致。"""
        now = time.time()
        return {"version": TRIP_VERSION,
                "trips": {key: _empty_trip(now) for key in TRIP_KEYS},
                "anchor": {}}

    @staticmethod
    def _clean_trip(slot: dict) -> dict:
        """清洗一段：v2 原样保留，v1 旧段（无 by_client）按清零时刻重建空桶。

        v1 段的旧计数**有意丢弃**：老行没有按协议分桶，合并旧计数进"全局"会与
        重扫日志得到的真值冲突。真值永远在日志里——空桶 + 保留 reset_at 意味着
        重启后的全量重扫会从日志精确重建每一桶，口径反而比迁移更准。
        """
        try:
            reset_at = float(slot.get("reset_at") or 0)
        except (AttributeError, TypeError, ValueError):
            reset_at = 0.0
        scope = slot.get("scope") if isinstance(slot.get("scope"), str) else "all"
        if scope not in TRIP_SCOPES:
            scope = "all"
        by_client = slot.get("by_client")
        if not isinstance(by_client, dict):
            by_client = {}  # v1 段：没有分桶，丢弃旧计数、等待重扫重建
        name = slot.get("name")
        return {"reset_at": reset_at, "scope": scope,
                "name": name.strip()[:12] if isinstance(name, str) else "",
                "by_client": {name_key: _clean_counts(by_client.get(name_key))
                              for name_key in _CLIENT_KEYS}}

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return self._blank()
        if not isinstance(data, dict) or data.get("version") not in (1, TRIP_VERSION):
            return self._blank()
        state = self._blank()
        trips = data.get("trips")
        if isinstance(trips, dict):
            for key in TRIP_KEYS:
                slot = trips.get(key)
                if isinstance(slot, dict):
                    state["trips"][key] = self._clean_trip(slot)
        if data.get("version") == TRIP_VERSION:
            anchor = data.get("anchor")
            if isinstance(anchor, dict):
                for name, offset in anchor.items():
                    if isinstance(offset, int) and offset >= 0:
                        state["anchor"][str(name)] = offset
        # v1 → v2：锚点有意丢弃——分桶结构变了，必须从日志头全量重扫重建
        # 各桶计数；段的 reset_at 已在 _clean_trip 里保留，重扫不会把清零
        # 之前的行折回来。这是一次性迁移成本，之后回到增量锚点模式。
        return state

    # ------------------------------------------------------------------ 记账

    def _fold(self, row) -> None:
        """把一行日志折进两段小计；早于清零时刻的行只对晚清零的那一段有效。

        每行同时折进「本协议桶 + 全局（由桶合并派生）」——三口径并行累计，
        切换读数口径只是换一个视角看同一本账，不动账本身。
        """
        try:
            if row.get("path", "").rstrip("/").endswith("/messages/count_tokens"):
                return
            timestamp = float(row.get("timestamp") or 0)
            incoming = int(row.get("input_tokens") or 0)
            outgoing = int(row.get("output_tokens") or 0)
        except (AttributeError, TypeError, ValueError):
            return
        # 协议归桶：老日志行没有 client 列，按 responses 兜底（records 同口径）。
        client = row.get("client")
        bucket_name = client if client in _CLIENT_KEYS else "responses"
        # 缓存读取是输入的一部分（上游口径：cached_tokens ⊆ prompt tokens）。
        # 小计里单独存「缓存读取」，供 UI 的入字悬停拆分（新输入/缓存读/缓存写）。
        cached = row.get("cached_tokens")
        try:
            cached = min(int(cached), incoming) if cached is not None else None
        except (AttributeError, TypeError, ValueError):
            cached = None
        # 缓存写入：Anthropic 口径的 cache_creation_input_tokens，独立于 input。
        creation = row.get("cache_creation_input_tokens")
        try:
            creation = max(0, int(creation)) if creation is not None else None
        except (AttributeError, TypeError, ValueError):
            creation = None
        for key in TRIP_KEYS:
            trip = self._state["trips"][key]
            if timestamp < trip["reset_at"]:
                continue
            bucket = trip["by_client"][bucket_name]
            if bucket["started_at"] is None:
                # 本桶第一笔入账：计时从这一刻开始（用日志行的时间戳，不用墙钟——
                # 重扫补账时起点依然是"那一笔真实发生的时间"，不会被补账时刻污染）。
                bucket["started_at"] = timestamp
            bucket["input_tokens"] += incoming
            bucket["output_tokens"] += outgoing
            bucket["requests"] += 1
            if row.get("mitigated"):
                bucket["mitigated"] = int(bucket.get("mitigated") or 0) + 1
            model = str(row.get("model") or "")
            if model:
                values = bucket.setdefault("models", {}).setdefault(
                    model, {"requests": 0, "tokens": 0})
                values["requests"] += 1
                values["tokens"] += incoming + outgoing
            if cached is not None:
                bucket["cached_input_tokens"] = bucket.get("cached_input_tokens", 0) + cached
            if creation is not None:
                bucket["cache_creation_tokens"] = bucket.get("cache_creation_tokens", 0) + creation

    def _read_from(self, path: Path) -> None:
        """从 anchor 续读到文件末尾；半行不读，留到下次写完再来。"""
        name = path.name
        offset = self._state["anchor"].get(name, 0)
        try:
            size = path.stat().st_size
        except OSError:
            return
        if offset > size:
            offset = 0  # 同名文件被重建/截断，旧偏移失效
        if offset == size:
            return
        position = offset
        try:
            with path.open("rb") as handle:
                handle.seek(offset)
                while True:
                    line = handle.readline()
                    if not line or not line.endswith(b"\n"):
                        break  # 正在写的半行：停在这里，下次从同一位置再读
                    try:
                        row = json.loads(line)
                    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                        position = handle.tell()  # 坏行跳过，但读位置必须前进
                        continue
                    self._fold(row)
                    position = handle.tell()
        except OSError:
            return  # 读不动就保留旧 anchor，下次再试
        self._state["anchor"][name] = position
        self._dirty = True

    def sync(self, files) -> None:
        """补齐历史：只在启动时调用，之后靠 `note_row` 增量跟进。"""
        with self.lock:
            names = {Path(path).name for path in files}
            for name in list(self._state["anchor"]):
                if name not in names:
                    self._state["anchor"].pop(name)  # 归档被清理，忘掉这个锚点
            for path in files:
                self._read_from(Path(path))
            if self._dirty:
                self._save()

    def note_row(self, row, *, filename: str, before: int, after: int) -> bool:
        """刚写完一条日志时调用（在 records 的锁内）。

        返回 True 表示锚点正好接上、这一行已经入账；返回 False 表示锚点对不上
        ——中间夹着本实例没读过的行（另一个临时实例写过，或日志被外部追加）。
        此时**不能**入账，否则会跳记；调用方应当立刻 `sync()` 顺序补齐。
        """
        with self.lock:
            known = self._state["anchor"].get(filename)
            # 锚点缺失但正好从第 0 字节开始写 = 全新的日志文件，第一条就该记账。
            aligns = known == before or (known is None and before == 0)
            if aligns:
                self._fold(row)
                self._state["anchor"][filename] = int(after)
            self._dirty = True
            if time.time() - self._saved_at >= SAVE_INTERVAL:
                self._save()
            return aligns

    def rename_anchor(self, old: str, new: str) -> None:
        """日志轮转：记忆跟着名字搬两处。

        归档那份的锚点必须搬到新名字上，否则下次启动会把整份归档从头重算一遍，
        小计凭空翻倍；同名活动文件轮转后是全新的，锚点必须归零，否则第一条写入
        会因为"锚点对不上"被跳过，一直卡到下次重启才补。
        """
        with self.lock:
            moved = self._state["anchor"].pop(old, None)
            if moved is not None:
                self._state["anchor"][new] = moved
            self._state["anchor"][old] = 0
            self._dirty = True

    # ------------------------------------------------------------------ 对外

    def summary(self) -> dict:
        """给界面用的快照；`elapsed` 由调用时刻算出，不落盘，所以永远是实时值。

        每段返回三口径读数：顶层字段（tokens/requests/…）= 该段**选中口径**的
        读数（兼容既有 UI/账本消费方），`scopes` 子字典给三口径完整读数，
        `scope` 是当前选中项。`elapsed` 为 None 表示该口径下还没有任何调用。
        """
        now = time.time()
        with self.lock:
            result = {}
            for key in TRIP_KEYS:
                trip = self._state["trips"][key]
                readings = {}
                for scope in TRIP_SCOPES:
                    counts = (_merged_counts(trip["by_client"]) if scope == "all"
                              else trip["by_client"].get(scope) or _zero_counts())
                    started_at = counts["started_at"]
                    incoming = int(counts["input_tokens"])
                    outgoing = int(counts["output_tokens"])
                    readings[scope] = {
                        "input_tokens": incoming,
                        "output_tokens": outgoing,
                        "tokens": incoming + outgoing,
                        "requests": int(counts["requests"]),
                        # 缓存拆分（任务书 5：入 = 新输入 / 缓存读取 / 缓存写入）。
                        "cached_input_tokens": int(counts.get("cached_input_tokens") or 0),
                        "cache_creation_tokens": int(counts.get("cache_creation_tokens") or 0),
                        "models": copy.deepcopy(counts.get("models") or {}),
                        "mitigated": int(counts.get("mitigated") or 0),
                        "details_complete": bool(counts.get("details_complete", False)),
                        "paused_seconds": float(counts.get("paused_seconds") or 0),
                        "reset_at": float(trip["reset_at"]),
                        "started_at": None if started_at is None else float(started_at),
                        "elapsed": None if started_at is None
                                   else max(0.0, now - float(started_at) - float(counts.get("paused_seconds") or 0)),
                    }
                chosen = trip.get("scope") if trip.get("scope") in TRIP_SCOPES else "all"
                slot = dict(readings[chosen])
                slot["scope"] = chosen
                slot["name"] = trip.get("name") or ""
                slot["scopes"] = readings
                result[key] = slot
            return result

    def reset(self, key: str) -> dict:
        """清零一段。另一段、日总量、历史日志都不受影响——只动这一段自己的账。"""
        if key not in TRIP_KEYS:
            raise ValueError(f"unknown trip: {key}")
        with self.lock:
            trip = self._state["trips"][key]
            # 清零保留读数口径：清零前看的是 Codex，清零后依然看 Codex。
            self._state["trips"][key] = _empty_trip(time.time(), trip.get("scope", "all"))
            self._dirty = True
            self._save()  # 清零必须立刻落盘：这是用户唯一会察觉"丢数据"的动作
            return self.summary()

    def set_scope(self, key: str, scope: str) -> dict:
        """切换一段的读数口径。只动"看哪个视角"，不动任何计数。"""
        if key not in TRIP_KEYS:
            raise ValueError(f"unknown trip: {key}")
        if scope not in TRIP_SCOPES:
            raise ValueError(f"unknown scope: {scope}")
        with self.lock:
            self._state["trips"][key]["scope"] = scope
            self._dirty = True
            self._save()  # 口径切换立即落盘：重启后 UI 停在用户选的那一档
            return self.summary()

    def rename(self, key: str, name: str) -> dict:
        """给一段起名（任务书 5：名称可点击就地编辑；空名显示 A / B）。"""
        if key not in TRIP_KEYS:
            raise ValueError(f"unknown trip: {key}")
        with self.lock:
            self._state["trips"][key]["name"] = str(name or "").strip()[:12]
            self._dirty = True
            self._save()
            return self.summary()

    def restore_reading(self, key: str, reading: dict) -> dict:
        """把账本快照的读数写回一段（撤销/恢复为当前区间）。

        快照带 scopes（v2）时按桶原样写回；旧格式快照（撤销条里残留的 v1
        读数）只有总量——写进两桶之一会污染分桶，直接保留当前账不动，
        撤销条 10 秒过期后不再有这种快照。
        """
        if key not in TRIP_KEYS:
            raise ValueError(f"unknown trip: {key}")
        scopes = reading.get("scopes") if isinstance(reading, dict) else None
        if not isinstance(scopes, dict) or not scopes:
            # v1 快照/旧版账册没有分桶明细：写回会破坏分桶，放弃写回，
            # 账保持现状。撤销条 10 秒过期后不再有 v1 快照；旧账册恢复
            # 同理——数字宁可保持现状，不能错着回来。
            self._dirty = True
            return self.summary()
        try:
            reset_at = float(reading.get("reset_at") or 0)
        except (AttributeError, TypeError, ValueError):
            reset_at = 0.0
        buckets = {}
        for name in _CLIENT_KEYS:
            source = scopes.get(name) if isinstance(scopes.get(name), dict) else {}
            started = source.get("started_at")
            try:
                started_at = float(started) if started is not None else None
            except (AttributeError, TypeError, ValueError):
                started_at = None
            buckets[name] = {
                "input_tokens": int(source.get("input_tokens") or 0),
                "output_tokens": int(source.get("output_tokens") or 0),
                "requests": int(source.get("requests") or 0),
                "cached_input_tokens": int(source.get("cached_input_tokens") or 0),
                "cache_creation_tokens": int(source.get("cache_creation_tokens") or 0),
                "models": copy.deepcopy(source.get("models") or {}),
                "mitigated": int(source.get("mitigated") or 0),
                "details_complete": bool(source.get("details_complete", False)),
                "paused_seconds": (max(0, float(reading["resume_at"]) - started_at - float(source.get("elapsed") or 0))
                                   if reading.get("resume_at") and started_at is not None
                                   else float(source.get("paused_seconds") or 0)),
                "started_at": started_at,
            }
        scope = reading.get("scope") if reading.get("scope") in TRIP_SCOPES else "all"
        with self.lock:
            self._state["trips"][key] = {"reset_at": reset_at, "scope": scope,
                                         "name": str(reading.get("name") or "").strip()[:12],
                                         "by_client": buckets}
            self._dirty = True
            self._save()
            return self.summary()

    # ------------------------------------------------------------------ 落盘

    def _save(self) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            atomic_write(self.path, json.dumps(self._state, ensure_ascii=False))
        except OSError:
            return  # 写不进去就保持 dirty，下一次 add 再试；内存里的账仍然正确
        self._dirty = False
        self._saved_at = time.time()

    def flush(self) -> None:
        with self.lock:
            if self._dirty:
                self._save()
