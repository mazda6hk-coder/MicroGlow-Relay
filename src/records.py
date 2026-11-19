"""Small, bounded telemetry stores. Request and response bodies are never saved."""
from __future__ import annotations

from collections import deque
from datetime import date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import threading
import time

from storage import atomic_write, redact
from trips import TripStore
from telemetry.store import ERROR_CATEGORIES, error_category_for_status


DAY = 24 * 60 * 60
LOG_NAME = "microglow-relay-usage.jsonl"
ARCHIVE_GLOB = "microglow-relay-usage-*.jsonl"
INDEX_NAME = "microglow-relay-usage-index.json"
INDEX_VERSION = 1
INDEX_SAVE_INTERVAL = 60
ROTATE_BYTES = 8 * 1024 * 1024
MEMORY_ROWS = 20_000
LOAD_WINDOW_DAYS = 30
TAIL_BYTES = 64
LOAD_TAIL_LINES = MEMORY_ROWS * 2


def _empty_bucket() -> dict:
    # cache_* 三个计数只统计「上游确实上报了缓存明细」的那些请求：老记录和没上报的
    # 上游不参与分母，否则历史天数会被误读成「命中率 0%」。
    # mitigated 计数同理：字段存在才算（老日志行无此列）。
    return {"requests": 0, "success": 0, "failures": 0, "tokens": 0,
            "input_tokens": 0, "output_tokens": 0,
            "cache_reported": 0, "cache_input_tokens": 0, "cached_tokens": 0,
            "reasoning_tokens": 0,
            "mitigated": 0, "mitigated_by": {},
            "models": {}, "errors": dict.fromkeys(ERROR_CATEGORIES, 0),
            "hours": [{"requests": 0, "tokens": 0} for _ in range(24)], "channels": {}}


def _row_int(row, key) -> int | None:
    """Integer field, or `None` when the row does not carry that field at all."""
    if not isinstance(row, dict) or key not in row:
        return None
    try:
        value = int(row.get(key) or 0)
    except (AttributeError, TypeError, ValueError):
        return None
    return value if value >= 0 else None


def cache_hit_rate(cached: int, input_tokens: int, reported: int) -> float | None:
    """命中部分占输入的比例（%）。没有可用样本时返回 None，不假装成 0%。"""
    if reported <= 0 or input_tokens <= 0:
        return None
    return cached / input_tokens * 100.0


# 错误三分类（口径 2026-11-10）：UI 的「标准化错误类别」每类拆三态。
OUTCOME_MITIGATED = "mitigated"          # 已自动化解：请求被救活
OUTCOME_SUCCESS = "success"              # 直通成功
OUTCOME_AGENT_NOTIFIED = "agent_notified"  # 已告知 Agent：最终失败且属上游侧
OUTCOME_NEEDS_ATTENTION = "needs_attention"  # 需你处理：认证/模型不存在/本地配置


def classify_outcome(row: dict) -> str:
    """一行日志 → 三分类 + 成功。救活优先于成功，Agent 与需处理按状态码分。"""
    if row.get("ok"):
        return OUTCOME_MITIGATED if row.get("mitigated") else OUTCOME_SUCCESS
    status = int(row.get("status") or 0)
    # 5xx 与超时/不可用是上游侧的事，Relay 已把错误信封告知 Agent；
    # 4xx 与本地错误（401/404/400/429 本地拒绝等）需要用户处理。
    if 500 <= status < 600:
        return OUTCOME_AGENT_NOTIFIED
    return OUTCOME_NEEDS_ATTENTION


def _day_key(row) -> str | None:
    """Local calendar day of one saved row, or `None` when the row is unusable."""
    try:
        timestamp = float(row.get("timestamp") or 0)
    except (AttributeError, TypeError, ValueError):
        return None
    try:
        return datetime.fromtimestamp(timestamp).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _make_day_tagger():
    """`timestamp -> local day` with a one-entry cache; logs arrive in order."""
    state = [0.0, -1.0, ""]

    def tag(timestamp: float) -> str | None:
        if state[0] <= timestamp < state[1]:
            return state[2]
        try:
            day = datetime.fromtimestamp(timestamp).date()
            start = datetime.combine(day, datetime.min.time()).timestamp()
            stop = datetime.combine(day + timedelta(days=1), datetime.min.time()).timestamp()
        except (OverflowError, OSError, ValueError):
            return None
        state[:] = [start, stop, day.isoformat()]
        return state[2]

    return tag


def _row_day(row, tag) -> str | None:
    try:
        timestamp = float(row.get("timestamp") or 0)
    except (AttributeError, TypeError, ValueError):
        return None
    return tag(timestamp)


def _accumulate(bucket: dict, row) -> None:
    """Fold one row into a day bucket; the totals are the historical ones."""
    try:
        incoming = int(row.get("input_tokens") or 0)
        outgoing = int(row.get("output_tokens") or 0)
        tokens = incoming + outgoing
        status = int(row.get("status") or 0)
    except (AttributeError, TypeError, ValueError):
        return
    bucket["requests"] += 1
    bucket["success" if row.get("ok") else "failures"] += 1
    bucket["tokens"] += tokens
    bucket["input_tokens"] += incoming
    bucket["output_tokens"] += outgoing
    cached = _row_int(row, "cached_tokens")
    if cached is not None:
        bucket["cache_reported"] += 1
        bucket["cache_input_tokens"] += incoming
        bucket["cached_tokens"] += min(cached, incoming)
    reasoning = _row_int(row, "reasoning_tokens")
    if reasoning is not None:
        bucket["reasoning_tokens"] += reasoning
    model = str(row.get("model") or "—")
    group = bucket["models"].get(model)
    if group is None:
        group = bucket["models"][model] = {"requests": 0, "tokens": 0}
    group["requests"] += 1
    group["tokens"] += tokens
    # 化解波动：按请求计。救活的请求 ok=True，但带 mitigated 标记。
    mitigated = str(row.get("mitigated") or "")
    if mitigated:
        bucket["mitigated"] += 1
        bucket["mitigated_by"][mitigated] = bucket["mitigated_by"].get(mitigated, 0) + 1
    try:
        hour = datetime.fromtimestamp(float(row.get("timestamp") or 0)).hour
        bucket["hours"][hour]["requests"] += 1
        bucket["hours"][hour]["tokens"] += tokens
    except (ValueError, OSError, OverflowError, KeyError):
        pass
    if "channel_index" in row:
        channel_key = f"{row.get('profile_id', '')}:{max(0, int(row['channel_index']))}"
        channel = bucket["channels"].setdefault(channel_key, {"requests": 0, "elapsed": 0.0})
        channel["requests"] += 1
        channel["elapsed"] += float(row.get("elapsed") or 0)
    if not row.get("ok"):
        bucket["errors"][error_category_for_status(status)] += 1


def _merge(target: dict, bucket: dict) -> None:
    target["requests"] += bucket["requests"]
    target["success"] += bucket["success"]
    target["failures"] += bucket["failures"]
    target["tokens"] += bucket["tokens"]
    for key in ("input_tokens", "output_tokens", "cache_reported",
                "cache_input_tokens", "cached_tokens", "reasoning_tokens",
                "mitigated"):
        target[key] += int(bucket.get(key) or 0)
    # 旧索引文件的 bucket 没有 mitigated_by 键：缺失按空处理，不炸。
    for reason, count in (bucket.get("mitigated_by") or {}).items():
        slot = target.setdefault("mitigated_by", {})
        slot[reason] = slot.get(reason, 0) + count
    for model, group in bucket["models"].items():
        slot = target["models"].setdefault(model, {"requests": 0, "tokens": 0})
        slot["requests"] += group["requests"]
        slot["tokens"] += group["tokens"]
    for category, count in bucket["errors"].items():
        if category in target["errors"]:
            target["errors"][category] += count


def _tail_hash(path: Path, offset: int) -> str:
    """Fingerprint of the bytes just before `offset`, used to prove append-only growth."""
    length = min(TAIL_BYTES, max(int(offset), 0))
    try:
        with path.open("rb") as handle:
            handle.seek(offset - length)
            return hashlib.blake2b(handle.read(length), digest_size=16).hexdigest()
    except OSError:
        return ""


def _last_timestamp(path: Path) -> float | None:
    """Timestamp of a file's last complete line, for cheap chronological pruning."""
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            block = min(size, 4096)
            handle.seek(size - block)
            data = handle.read(block)
    except OSError:
        return None
    chunks = [chunk for chunk in data.split(b"\n") if chunk.strip()]
    if len(chunks) < (1 if block >= size else 2):
        return None
    for chunk in reversed(chunks):
        try:
            row = json.loads(chunk.decode("utf-8", errors="replace"))
            return float(row.get("timestamp") or 0)
        except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return None


def _tail_lines(path: Path, limit: int) -> list[str] | None:
    """The newest `limit` lines of a file (oldest first) without reading all of it.

    启动只需要最近的记录，因此从文件尾部按块回读；文件本身小于一个块时等价于整读。
    `None` 表示读取失败，调用方应退回完整的顺序读。
    """
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            position = handle.tell()
            block = 1 << 20
            buffer = b""
            while position > 0 and buffer.count(b"\n") <= limit:
                size = min(block, position)
                position -= size
                handle.seek(position)
                buffer = handle.read(size) + buffer
                block = min(block * 4, 16 << 20)
            lines = buffer.decode("utf-8", errors="replace").split("\n")
            if position > 0:
                handle.seek(position - 1)
                if handle.read(1) != b"\n":
                    lines = lines[1:]  # 开头这半行属于更早的块
    except OSError:
        return None
    return lines[-limit:]


def _scan_file(path: Path, start: int, on_row) -> int:
    """Feed complete lines from `start` on to `on_row`; return the new byte offset.

    以换行结束的行一律按整行处理；文件末尾没有换行的半行只有在自己已是完整 JSON
    时才算数（兼容旧版留下的无尾换行文件），否则留待下一次扫描重读。
    """
    offset = start
    try:
        with path.open("rb") as handle:
            handle.seek(start)
            while True:
                raw = handle.readline()
                if not raw:
                    break
                offset += len(raw)
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    if raw.endswith(b"\n"):
                        continue
                    offset -= len(raw)  # 半行：等它写完整再算
                    break
                on_row(row)
    except OSError:
        return offset
    return offset


def _validate_bucket(bucket) -> dict:
    if not isinstance(bucket, dict):
        raise ValueError("malformed usage index bucket")
    clean = _empty_bucket()
    # 老索引文件没有缓存字段：缺失即按 0 处理，不强制重建（历史行本来也没有这些数）。
    for key in ("requests", "success", "failures", "tokens", "input_tokens", "output_tokens",
                "cache_reported", "cache_input_tokens", "cached_tokens", "reasoning_tokens", "mitigated"):
        clean[key] = int(bucket.get(key) or 0)
    clean["mitigated_by"] = dict(bucket.get("mitigated_by") or {})
    clean["details_indexed"] = "hours" in bucket
    hours = bucket.get("hours")
    if isinstance(hours, list) and len(hours) == 24:
        clean["hours"] = [{"requests": int(h.get("requests") or 0), "tokens": int(h.get("tokens") or 0)} for h in hours]
    clean["channels"] = dict(bucket.get("channels") or {})
    models = bucket.get("models")
    if not isinstance(models, dict):
        raise ValueError("malformed usage index models")
    for model, group in models.items():
        if not isinstance(group, dict):
            raise ValueError("malformed usage index model group")
        clean["models"][str(model)] = {"requests": int(group.get("requests") or 0),
                                       "tokens": int(group.get("tokens") or 0)}
    errors = bucket.get("errors")
    if not isinstance(errors, dict):
        raise ValueError("malformed usage index errors")
    for category, count in errors.items():
        if category in clean["errors"]:
            clean["errors"][category] = int(count or 0)
    return clean


def _validate_index(data) -> dict:
    """Reject anything unexpected so a damaged cache is rebuilt, never trusted."""
    if not isinstance(data, dict) or data.get("version") != INDEX_VERSION:
        raise ValueError("unsupported usage index")
    files = data.get("files")
    if not isinstance(files, dict):
        raise ValueError("malformed usage index")
    clean = {}
    for name, entry in files.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError("malformed usage index entry")
        days = entry.get("days")
        if not isinstance(days, dict):
            raise ValueError("malformed usage index days")
        clean[name] = {
            "size": int(entry.get("size") or 0),
            "mtime_ns": int(entry.get("mtime_ns") or 0),
            "offset": int(entry.get("offset") or 0),
            "tail": str(entry.get("tail") or ""),
            "days": {str(day): _validate_bucket(bucket) for day, bucket in days.items()},
        }
    return {"version": INDEX_VERSION, "files": clean}


class ActivityLog:
    """Append-only JSONL request log plus a persisted calendar-day index.

    写入仍然是同一条 `microglow-relay-usage.jsonl`；超过 `ROTATE_BYTES` 后改名
    归档为 `microglow-relay-usage-<时间戳>.jsonl`，历史文件始终可读，旧版本留下的
    单文件也照常读取。`period_summary()` 只解析索引之后新增的字节，并把每个文件
    每天的累计量缓存在 `microglow-relay-usage-index.json`，因此统计耗时与历史总行数
    解耦；首次运行或缓存失效时才会全量重建一次并落盘。
    """

    def __init__(self, directory: Path, *, load: bool = True):
        """`load=False` skips reading the log for short-lived callers.

        连接测试这类一次性网关只需要写这一行记录，不需要把整份历史读进来；
        统计入口会自己按需补齐，因此跳读不会让任何数字失真。
        """
        self.path = Path(directory) / LOG_NAME
        self.index_path = Path(directory) / INDEX_NAME
        self.lock = threading.RLock()
        self.rows = deque(maxlen=MEMORY_ROWS)
        self.index = {"version": INDEX_VERSION, "files": {}}
        self._index_loaded = False
        self._index_dirty = False
        self._saved_at = time.time()
        self._rotate_bytes = ROTATE_BYTES
        # 小计与日志同源：口径就是这里的 input+output，不另立一套。
        # load=False 的一次性实例也建一个，只是不补历史。
        self.trips = TripStore(directory, log_name=LOG_NAME)
        if load:
            self._load()
            self.trips.sync(self._log_files())

    # ------------------------------------------------------------------ reads

    def _log_files(self) -> list[Path]:
        """Rotated archives oldest first, then the active log when it exists."""
        directory = self.path.parent
        try:
            archives = sorted(directory.glob(ARCHIVE_GLOB))
        except OSError:
            archives = []
        files = [path for path in archives if path.is_file()]
        if self.path.exists():
            files.append(self.path)
        return files

    def _load(self):
        self._ensure_index()
        cutoff = time.time() - LOAD_WINDOW_DAYS * DAY
        cutoff_day = datetime.fromtimestamp(cutoff).date().isoformat()
        for path in self._log_files():
            entry = self._fresh_entry(path)
            if entry is not None:
                if entry["days"] and max(entry["days"]) < cutoff_day:
                    continue  # 索引已确认整份文件都在 30 天窗口之外
            elif path != self.path:
                newest = _last_timestamp(path)
                if newest is not None and newest < cutoff:
                    continue  # 没有索引时按末行时间戳跳过陈旧归档
            if not self._read_tail_rows(path, cutoff):
                self._read_all_rows(path, cutoff)  # 行序异常（系统时钟回拨）时退回整读

    def _read_tail_rows(self, path: Path, cutoff: float) -> bool:
        """Read only the newest rows needed for the in-memory window."""
        lines = _tail_lines(path, LOAD_TAIL_LINES)
        if lines is None:
            return False
        previous = None
        appended = 0
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                timestamp = float(row.get("timestamp") or 0)
            except (AttributeError, TypeError, ValueError, UnicodeDecodeError):
                continue
            if previous is not None and timestamp < previous:
                for _ in range(appended):
                    self.rows.pop()  # 回退后交给完整顺序读
                return False  # 不是按时间顺序落盘，无法用尾部块代表最新记录
            previous = timestamp
            if timestamp >= cutoff:
                self.rows.append(row)
                appended += 1
        return True

    def _read_all_rows(self, path: Path, cutoff: float) -> None:
        def keep(row):
            try:
                timestamp = float(row.get("timestamp") or 0)
            except (AttributeError, TypeError, ValueError):
                return
            if timestamp >= cutoff:
                self.rows.append(row)

        _scan_file(path, 0, keep)

    def add(self, *, profile: dict, elapsed: float, status: int, input_tokens=0, output_tokens=0,
            cached_tokens=None, reasoning_tokens=None, message="", request_model=None,
            client="", mitigated="", cache_creation_input_tokens=None, channel_index=None):
        row = {
            "timestamp": time.time(),
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "profile_id": profile.get("id", ""),
            "provider": profile.get("provider_name") or profile.get("provider", ""),
            "model": profile.get("model", ""),
            "status": int(status),
            "ok": 200 <= int(status) < 300,
            "elapsed": round(float(elapsed), 2),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "message": redact(message),
            # 入站协议（"responses" / "anthropic"）：老日志行没有这列，
            # 读取侧按 "responses" 兜底。客户端真实身份无从得知，协议是唯一
            # 诚实的区分维度——Claude Code 走 anthropic，其余走 responses。
            "client": str(client or "").strip() or "responses",
        }
        # 化解波动（口径 2026-11-10 与刘总对齐）：一次请求被重试/换渠道救活
        # 记 1 次（重试三次救活也只算 1 次），值是首次失败原因的归类——
        # rate_limit / timeout / unavailable / switched_channel / transient_400。
        # 字段存在 = 这一笔被救活；缺失 = 直通或最终失败。
        mitigated = str(mitigated or "").strip()
        if mitigated:
            row["mitigated"] = mitigated[:40]
        # 请求侧模型与解析出的配置不一致时才落字段：绝大多数请求 model 就是配置 id，
        # 落了等于每行复制一遍 profile_id。真正要看的是「Codex 说用 A、实际路由到 B」——
        # 走默认入口（microglow-relay）和原生透传 slug 时都会落这一列。
        requested = str(request_model or "").strip()
        if requested and requested != str(row["profile_id"]):
            row["request_model"] = requested[:120]
        # 上游上报了缓存/推理明细时才落字段：字段存在 = 这一笔有数据；缺失 = 无从得知。
        if cached_tokens is not None:
            row["cached_tokens"] = int(cached_tokens or 0)
        if cache_creation_input_tokens is not None:
            row["cache_creation_input_tokens"] = int(cache_creation_input_tokens or 0)
        if channel_index is not None:
            row["channel_index"] = int(channel_index)
        if reasoning_tokens is not None:
            row["reasoning_tokens"] = int(reasoning_tokens or 0)
        payload = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        with self.lock:
            self.rows.append(row)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                entry = self.index["files"].get(self.path.name) if self._index_loaded else None
                try:
                    before = self.path.stat().st_size
                except OSError:
                    before = -1
                if entry is None or before < 0 or entry["offset"] != before:
                    entry = None  # 状态未知：累计交给下一次同步重扫
                if before >= self._rotate_bytes:
                    self._rotate(entry)
                    entry, before = None, 0
                with self.path.open("ab") as file:
                    file.write(payload)
                stat = self.path.stat()
                # 写前位置由写后大小反推：整段都在 self.lock 内，不会有并发追加。
                if not self.trips.note_row(row, filename=self.path.name,
                                           before=stat.st_size - len(payload),
                                           after=stat.st_size):
                    # 锚点没接上（另一个实例写过、或文件被外部追加）：
                    # 就地顺序补齐。不补的话这几行要等到下次重启才会出现。
                    self.trips.sync(self._log_files())
                if entry is not None and stat.st_size == before + len(payload):
                    entry["offset"] = stat.st_size
                    entry["size"] = stat.st_size
                    entry["mtime_ns"] = stat.st_mtime_ns
                    entry["tail"] = _tail_hash(self.path, entry["offset"])
                    key = _day_key(row)
                    if key is not None:
                        bucket = entry["days"].get(key)
                        if bucket is None:
                            bucket = entry["days"][key] = _empty_bucket()
                        _accumulate(bucket, row)
                    self._index_dirty = True
                    self._maybe_save_index()
            except OSError:
                pass

    def recent(self, limit=100):
        with self.lock:
            return list(reversed(list(self.rows)[-int(limit):]))

    def trip_summary(self) -> dict:
        """TRIP A/B 的当前读数。只读内存，不碰磁盘。"""
        return self.trips.summary()

    def reset_trip(self, key: str) -> dict:
        """清零一段小计。日总量、历史日志与另一段都保持原样。"""
        return self.trips.reset(key)

    def set_trip_scope(self, key: str, scope: str) -> dict:
        """切换一段小计的读数口径（全局/Codex/Claude）。只换视角，不动账。"""
        return self.trips.set_scope(key, scope)

    def period_summary(self, period: str, anchor: date) -> dict:
        """Calendar totals from the persisted day index, not from a full rescan."""
        start, end = calendar_period(period, anchor)
        return self._day_window(start, end, start, end - timedelta(days=1))

    def range_summary(self, start: date, end: date) -> dict:
        """Inclusive day range; the caller decides both ends explicitly."""
        if end < start:
            start, end = end, start
        return self._day_window(start, end + timedelta(days=1), start, end)

    def _day_window(self, lower: date, upper: date, shown_start: date, shown_end: date) -> dict:
        """Half-open [lower, upper) totals plus the inclusive range to display."""
        result = {"requests": 0, "success": 0, "failures": 0, "tokens": 0,
                  "input_tokens": 0, "output_tokens": 0, "cache_reported": 0,
                  "cache_input_tokens": 0, "cached_tokens": 0, "reasoning_tokens": 0,
                  "mitigated": 0, "mitigated_by": {},
                  "start": shown_start, "end": shown_end,
                  "models": {}, "errors": dict.fromkeys(ERROR_CATEGORIES, 0)}
        with self.lock:
            if self._log_files() or self.index_path.exists():
                self._sync_index()
                for entry in self.index["files"].values():
                    for day, bucket in entry["days"].items():
                        try:
                            current = date.fromisoformat(day)
                        except ValueError:
                            continue
                        if lower <= current < upper:
                            _merge(result, bucket)
            else:
                # 没有落盘文件时（例如写入失败）沿用内存行，保持原有兜底行为。
                first = datetime.combine(lower, datetime.min.time()).timestamp()
                last = datetime.combine(upper, datetime.min.time()).timestamp()
                for row in self.rows:
                    if _in_window(row, first, last):
                        _accumulate(result, row)
        result["cache_rate"] = cache_hit_rate(result["cached_tokens"],
                                              result["cache_input_tokens"],
                                              result["cache_reported"])
        return result

    def daily_details(self, day: date) -> dict:
        """Hourly charts and per-channel metrics share the persisted day index."""
        result = {"hours": [{"requests": 0, "tokens": 0} for _ in range(24)], "channels": {}}
        with self.lock:
            self._sync_index()
            for entry in self.index["files"].values():
                bucket = entry["days"].get(day.isoformat()) or {}
                for index, hour in enumerate(bucket.get("hours") or []):
                    for field in ("requests", "tokens"):
                        result["hours"][index][field] += int(hour.get(field) or 0)
                for key, values in (bucket.get("channels") or {}).items():
                    pid, index = key.rsplit(":", 1)
                    target = result["channels"].setdefault((pid, int(index)), {"requests": 0, "elapsed": 0.0})
                    target["requests"] += int(values.get("requests") or 0)
                    target["elapsed"] += float(values.get("elapsed") or 0)
        return result

    def grand_total(self) -> dict:
        """全量累计（自安装以来）：总里程 ODO 的数据源，永不清零。

        与 range_summary 同源（持久化日索引）——「总里程 = 日志累计」由
        同一份数据保证，不设第二份账。first_day 为最早有记录的日期。
        """
        result = {"requests": 0, "tokens": 0, "first_day": None}
        with self.lock:
            if self._log_files() or self.index_path.exists():
                self._sync_index()
                for entry in self.index["files"].values():
                    for day, bucket in entry["days"].items():
                        try:
                            date.fromisoformat(day)     # 校验格式
                        except ValueError:
                            continue
                        if result["first_day"] is None or day < result["first_day"]:
                            result["first_day"] = day
                        result["requests"] += int(bucket.get("requests") or 0)
                        result["tokens"] += int(bucket.get("tokens") or 0)
            else:
                for row in self.rows:
                    stamp = float(row.get("timestamp") or 0)
                    if not stamp:
                        continue
                    day = datetime.fromtimestamp(stamp).date().isoformat()
                    if result["first_day"] is None or day < result["first_day"]:
                        result["first_day"] = day
                    result["requests"] += 1
                    result["tokens"] += int(row.get("input_tokens") or 0) \
                        + int(row.get("output_tokens") or 0)
        return result

    def today(self):
        midnight = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
        with self.lock:
            rows = [row for row in self.rows if float(row.get("timestamp") or 0) >= midnight]
        successful = [row for row in rows if row.get("ok")]
        average = sum(float(row.get("elapsed") or 0) for row in successful) / len(successful) if successful else 0
        incoming = sum(int(row.get("input_tokens") or 0) for row in rows)
        outgoing = sum(int(row.get("output_tokens") or 0) for row in rows)
        reported = [row for row in rows if _row_int(row, "cached_tokens") is not None]
        mitigated_rows = [row for row in rows if row.get("mitigated")]
        mitigated_by: dict[str, int] = {}
        for row in mitigated_rows:
            reason = str(row["mitigated"])
            mitigated_by[reason] = mitigated_by.get(reason, 0) + 1
        result = {
            "requests": len(rows),
            "success": len(successful),
            "failures": len(rows) - len(successful),
            "average": average,
            "tokens": incoming + outgoing,
            "input_tokens": incoming,
            "output_tokens": outgoing,
            "cache_reported": len(reported),
            "cache_input_tokens": sum(int(row.get("input_tokens") or 0) for row in reported),
            "cached_tokens": sum(min(_row_int(row, "cached_tokens") or 0,
                                     int(row.get("input_tokens") or 0)) for row in reported),
            "reasoning_tokens": sum(_row_int(row, "reasoning_tokens") or 0 for row in rows),
            "mitigated": len(mitigated_rows),
            "mitigated_by": mitigated_by,
        }
        result["cache_rate"] = cache_hit_rate(result["cached_tokens"],
                                              result["cache_input_tokens"],
                                              result["cache_reported"])
        return result

    # ------------------------------------------------------------- day index

    def _ensure_index(self):
        if self._index_loaded:
            return
        self._index_loaded = True
        try:
            self.index = _validate_index(json.loads(self.index_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            self.index = {"version": INDEX_VERSION, "files": {}}
            self._index_dirty = True

    def _fresh_entry(self, path: Path):
        """Index entry whose recorded state matches the file on disk right now."""
        entry = self.index["files"].get(path.name)
        if entry is None:
            return None
        try:
            stat = path.stat()
        except OSError:
            return None
        if entry["size"] != stat.st_size or entry["mtime_ns"] != stat.st_mtime_ns:
            return None
        return entry

    def _sync_index(self):
        """Fold only the bytes appended since the last checkpoint into the index."""
        self._ensure_index()
        changed = False
        names = set()
        for path in self._log_files():
            name = path.name
            names.add(name)
            try:
                stat = path.stat()
            except OSError:
                continue
            entry = self.index["files"].get(name)
            start = None
            if entry is not None:
                if entry["size"] == stat.st_size and entry["mtime_ns"] == stat.st_mtime_ns and all(b.get("details_indexed", True) for b in entry["days"].values()):
                    continue  # 文件未变，缓存即权威
                if stat.st_size > entry["offset"] and _tail_hash(path, entry["offset"]) == entry["tail"] and all(b.get("details_indexed", True) for b in entry["days"].values()):
                    start = entry["offset"]  # 纯追加：只读新增字节
            if start is None:
                entry = {"size": 0, "mtime_ns": 0, "offset": 0, "tail": "", "days": {}}
                self.index["files"][name] = entry
                start = 0
            days = entry["days"]
            tag = _make_day_tagger()

            def collect(row, days=days, tag=tag):
                key = _row_day(row, tag)
                if key is None:
                    return
                bucket = days.get(key)
                if bucket is None:
                    bucket = days[key] = _empty_bucket()
                _accumulate(bucket, row)

            entry["offset"] = _scan_file(path, start, collect)
            try:
                stat = path.stat()
                entry["mtime_ns"] = stat.st_mtime_ns
            except OSError:
                pass
            # `size` 记录的是已经并入索引的前缀长度，而不是文件当前总长度：扫描期间
            # 可能有其它实例继续追加（连接测试网关），这样下一轮一定会补读差额。
            entry["size"] = entry["offset"]
            entry["tail"] = _tail_hash(path, entry["offset"])
            changed = True
        # Keep daily aggregates after raw-log retention; ODO and range totals
        # have the same permanent source, while request bodies are never stored.
        if changed:
            self._index_dirty = True
            self._save_index()

    def _save_index(self):
        self._ensure_index()
        try:
            atomic_write(self.index_path, json.dumps(self.index, ensure_ascii=False, sort_keys=True))
        except OSError:
            return
        self._index_dirty = False
        self._saved_at = time.time()

    def _maybe_save_index(self):
        if self._index_dirty and self._index_loaded and time.time() - self._saved_at >= INDEX_SAVE_INTERVAL:
            self._save_index()

    def _rotate(self, entry: dict | None):
        """Rename the active log into a timestamped archive; never delete data."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        archive = self.path.parent / f"microglow-relay-usage-{stamp}.jsonl"
        counter = 1
        while archive.exists():
            archive = self.path.parent / f"microglow-relay-usage-{stamp}-{counter}.jsonl"
            counter += 1
        try:
            os.replace(self.path, archive)
        except OSError:
            return
        self.trips.rename_anchor(self.path.name, archive.name)
        self.index["files"].pop(self.path.name, None)
        if entry is not None:
            self.index["files"][archive.name] = entry  # 内容未变，条目整体搬过去
        self._index_dirty = True


def _in_window(row, lower: float, upper: float) -> bool:
    try:
        timestamp = float(row.get("timestamp") or 0)
    except (AttributeError, TypeError, ValueError):
        return False
    return lower <= timestamp < upper


def calendar_period(period: str, anchor: date) -> tuple[date, date]:
    if period == "day":
        return anchor, anchor + timedelta(days=1)
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=7)
    if period in {"month", "quarter"}:
        month = anchor.month if period == "month" else (anchor.month - 1) // 3 * 3 + 1
        next_month = month + (1 if period == "month" else 3)
        return date(anchor.year, month, 1), date(anchor.year + (next_month > 12), (next_month - 1) % 12 + 1, 1)
    if period == "year":
        return date(anchor.year, 1, 1), date(anchor.year + 1, 1, 1)
    raise ValueError("Unsupported statistics period")


def period_bounds(period: str, anchor: date) -> tuple[date, date]:
    """Inclusive first/last day of the calendar period that contains ``anchor``."""
    start, end = calendar_period(period, anchor)
    return start, end - timedelta(days=1)


class ReasoningCache:
    """Keeps provider-only reasoning needed when a tool-call turn is replayed."""

    def __init__(self, directory: Path):
        self.path = Path(directory) / "microglow-relay-reasoning.json"
        self.lock = threading.RLock()
        self.entries = {}
        if self.path.exists():
            try:
                value = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    self.entries = value
            except (OSError, json.JSONDecodeError):
                pass
        self._prune()

    def _prune(self):
        cutoff = time.time() - 7 * DAY
        self.entries = {
            str(key): value
            for key, value in self.entries.items()
            if isinstance(value, dict) and float(value.get("timestamp") or 0) >= cutoff
        }
        if len(self.entries) > 2_000:
            ordered = sorted(self.entries.items(), key=lambda pair: pair[1]["timestamp"])
            self.entries = dict(ordered[-2_000:])

    def put(self, call_id: str, text: str):
        if not call_id or not text:
            return
        with self.lock:
            self.entries[str(call_id)] = {"timestamp": time.time(), "text": str(text)}
            self._prune()
            try:
                atomic_write(self.path, json.dumps(self.entries, ensure_ascii=False))
            except OSError:
                pass

    def get(self, call_id: str):
        with self.lock:
            value = self.entries.get(str(call_id))
            if not isinstance(value, dict):
                return None
            if float(value.get("timestamp") or 0) < time.time() - 7 * DAY:
                return None
            return str(value.get("text") or "") or None


# Names kept for simple auxiliary tooling.
UsageLog = ActivityLog
