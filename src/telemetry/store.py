# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""SQLite-backed daily aggregates and durable local upload batches."""
from __future__ import annotations

from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Protocol
import uuid

from .channel import CHANNELS
from .consent import CONSENT_VERSIONS, TelemetryConsent


LATENCY_BUCKETS = ("lt_1s", "from_1s_to_3s", "from_3s_to_10s", "gte_10s")
ERROR_CATEGORIES = ("authentication", "rate_limit", "timeout", "unavailable", "invalid_request", "other")
BATCH_STATES = ("pending", "uploading", "acknowledged", "rejected")
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+\-]*$")
DAILY_AGGREGATES_DDL = """
    CREATE TABLE IF NOT EXISTS {table} (
        schema_version INTEGER NOT NULL,
        client_version TEXT NOT NULL,
        operating_system TEXT NOT NULL,
        provider TEXT NOT NULL,
        model_type TEXT NOT NULL,
        model_value TEXT NOT NULL,
        aggregation_day TEXT NOT NULL,
        call_channel TEXT NOT NULL DEFAULT 'unknown',
        active_minutes INTEGER NOT NULL DEFAULT 0,
        api_call_count INTEGER NOT NULL DEFAULT 0,
        success_count INTEGER NOT NULL DEFAULT 0,
        error_count INTEGER NOT NULL DEFAULT 0,
        input_tokens INTEGER NOT NULL DEFAULT 0,
        output_tokens INTEGER NOT NULL DEFAULT 0,
        latency_lt_1s INTEGER NOT NULL DEFAULT 0,
        latency_1s_3s INTEGER NOT NULL DEFAULT 0,
        latency_3s_10s INTEGER NOT NULL DEFAULT 0,
        latency_gte_10s INTEGER NOT NULL DEFAULT 0,
        error_authentication INTEGER NOT NULL DEFAULT 0,
        error_rate_limit INTEGER NOT NULL DEFAULT 0,
        error_timeout INTEGER NOT NULL DEFAULT 0,
        error_unavailable INTEGER NOT NULL DEFAULT 0,
        error_invalid_request INTEGER NOT NULL DEFAULT 0,
        error_other INTEGER NOT NULL DEFAULT 0,
        fallback_count INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (schema_version, client_version, operating_system, provider,
                     model_type, model_value, aggregation_day, call_channel)
    )
"""


def utc_day(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("aggregation time must be timezone-aware")
    return current.astimezone(timezone.utc).date().isoformat()


def latency_bucket(elapsed_seconds: float) -> str:
    elapsed = max(0.0, float(elapsed_seconds))
    if elapsed < 1:
        return "lt_1s"
    if elapsed < 3:
        return "from_1s_to_3s"
    if elapsed < 10:
        return "from_3s_to_10s"
    return "gte_10s"


def error_category_for_status(status: int) -> str:
    status = int(status)
    if status in {401, 403}:
        return "authentication"
    if status == 429:
        return "rate_limit"
    if status in {408, 504}:
        return "timeout"
    if status in {502, 503}:
        return "unavailable"
    if status in {400, 404, 405, 409, 413, 415, 422}:
        return "invalid_request"
    return "other"


class TelemetryDatabase:
    def __init__(self, directory: Path):
        self.path = Path(directory) / "telemetry-v2.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=0.5)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def execute_with_retry(self, sql: str, params=(), *, attempts: int = 5,
                           delay: float = 0.02) -> None:
        """Run a single write, retrying the transient WAL sidecar race.

        每次操作都是「开连接→写→关连接」。当最后一个连接关闭时 SQLite 会
        checkpoint 并删掉 -wal/-shm；另一个线程恰在此刻开的新连接会因找不到
        WAL 索引而把库降级成只读，抛 ``attempt to write a readonly database``。
        这是瞬时状态——-wal 会在下一次写连接时重建——所以换一条全新连接、
        短暂退避后重试即可恢复。UPDATE 本身幂等，重试不会重复计数。
        """
        for attempt in range(attempts):
            try:
                with self.connect() as connection:
                    connection.execute(sql, params)
                return
            except sqlite3.OperationalError as error:
                transient = "readonly" in str(error).lower()
                if not transient or attempt == attempts - 1:
                    raise
                time.sleep(delay * (attempt + 1))

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=FULL;
                CREATE TABLE IF NOT EXISTS batches (
                    batch_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            connection.execute(DAILY_AGGREGATES_DDL.format(table="daily_aggregates"))
        self._migrate_channel_if_needed()
        with self.connect() as connection:
            # An interrupted upload is retryable on the next process start.
            connection.execute("UPDATE batches SET state = 'pending' WHERE state = 'uploading'")

    def _migrate_channel_if_needed(self) -> None:
        with self.connect() as connection:
            old_columns = [row["name"] for row in connection.execute("PRAGMA table_info(daily_aggregates)")]
        if "call_channel" in old_columns:
            return
        # Snapshot the user's existing database before replacing its aggregate table.
        backup = self.path.with_name("telemetry-v2.pre-channel.sqlite3")
        if backup.exists():
            backup = self.path.with_name("telemetry-v2.pre-channel-" + uuid.uuid4().hex + ".sqlite3")
        with closing(sqlite3.connect(self.path)) as source, closing(sqlite3.connect(backup)) as destination:
            source.backup(destination)
        columns = ", ".join(old_columns)
        with self.connect() as connection:
            connection.execute(DAILY_AGGREGATES_DDL.format(table="daily_aggregates_channel"))
            connection.execute(
                f"INSERT INTO daily_aggregates_channel ({columns}, call_channel) "
                f"SELECT {columns}, 'unknown' FROM daily_aggregates"
            )
            connection.execute("DROP TABLE daily_aggregates")
            connection.execute("ALTER TABLE daily_aggregates_channel RENAME TO daily_aggregates")


class TelemetryAggregator:
    """Aggregates only fixed counters.  It never accepts request/response text."""

    def __init__(self, database: TelemetryDatabase, consent: TelemetryConsent):
        self.database = database
        self.consent = consent

    def record_request(
        self,
        *,
        client_version: str,
        operating_system: str | None = None,
        provider: str,
        model: str | None = None,
        model_family: str | None = None,
        successful: bool,
        input_tokens: int = 0,
        output_tokens: int = 0,
        elapsed_seconds: float = 0,
        error_category: str | None = None,
        fallback: bool = False,
        active_minutes: int = 0,
        call_channel: str = "unknown",
        occurred_at: datetime | None = None,
        schema_version: int = 2,
    ) -> bool:
        if schema_version not in {1, 2} or not self.consent.is_granted(schema_version):
            return False
        # Retain the legacy SQLite slot, but never store or infer the host OS.
        # The optional argument is ignored for older local callers.
        operating_system = ""
        self._validate_dimensions(client_version, provider, model, model_family)
        if call_channel not in CHANNELS:
            raise ValueError("unsupported call_channel")
        input_tokens = max(0, int(input_tokens or 0))
        output_tokens = max(0, int(output_tokens or 0))
        active_minutes = max(0, min(1_440, int(active_minutes or 0)))
        bucket = latency_bucket(elapsed_seconds)
        category = None if successful else (error_category or "other")
        if category is not None and category not in ERROR_CATEGORIES:
            raise ValueError("unsupported error category")
        model_type, model_value = ("model", model) if model is not None else ("model_family", model_family)
        values = {
            "active_minutes": active_minutes,
            "api_call_count": 1,
            "success_count": int(bool(successful)),
            "error_count": int(not successful),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_lt_1s": int(bucket == "lt_1s"),
            "latency_1s_3s": int(bucket == "from_1s_to_3s"),
            "latency_3s_10s": int(bucket == "from_3s_to_10s"),
            "latency_gte_10s": int(bucket == "gte_10s"),
            "error_authentication": int(category == "authentication"),
            "error_rate_limit": int(category == "rate_limit"),
            "error_timeout": int(category == "timeout"),
            "error_unavailable": int(category == "unavailable"),
            "error_invalid_request": int(category == "invalid_request"),
            "error_other": int(category == "other"),
            "fallback_count": int(bool(fallback)),
        }
        columns = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)
        updates = ", ".join(f"{name} = MIN({name} + excluded.{name}, 1440)" if name == "active_minutes"
                            else f"{name} = {name} + excluded.{name}" for name in values)
        identity = (schema_version, client_version, operating_system, provider, model_type, model_value,
                    utc_day(occurred_at), call_channel)
        with self.database.connect() as connection:
            connection.execute(f"""
                INSERT INTO daily_aggregates
                    (schema_version, client_version, operating_system, provider, model_type,
                     model_value, aggregation_day, call_channel, {columns})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, {placeholders})
                ON CONFLICT(schema_version, client_version, operating_system, provider,
                            model_type, model_value, aggregation_day, call_channel)
                DO UPDATE SET {updates}
            """, identity + tuple(values.values()))
        return True

    @staticmethod
    def _validate_dimensions(client_version, provider, model, model_family) -> None:
        if not isinstance(client_version, str) or not SAFE_NAME.fullmatch(client_version) or len(client_version) > 64:
            raise ValueError("invalid client_version")
        if not isinstance(provider, str) or not SAFE_NAME.fullmatch(provider) or len(provider) > 64:
            raise ValueError("invalid provider")
        if (model is None) == (model_family is None):
            raise ValueError("exactly one of model or model_family is required")
        value = model if model is not None else model_family
        if not isinstance(value, str) or not value or len(value) > 128 or any(ord(char) < 32 for char in value):
            raise ValueError("invalid model dimension")


def _row_payload(row: sqlite3.Row, schema_version: int) -> dict:
    payload = {
        "client_version": row["client_version"],
        "provider": row["provider"],
        row["model_type"]: row["model_value"],
        "active_minutes": row["active_minutes"],
        "api_call_count": row["api_call_count"],
        "success_count": row["success_count"],
        "error_count": row["error_count"],
        "input_tokens": row["input_tokens"],
        "output_tokens": row["output_tokens"],
        "total_tokens": row["input_tokens"] + row["output_tokens"],
        "aggregation_day": row["aggregation_day"],
        "call_channel": row["call_channel"],
    }
    if schema_version == 2:
        payload.update({
            "latency_buckets": {
                "lt_1s": row["latency_lt_1s"],
                "from_1s_to_3s": row["latency_1s_3s"],
                "from_3s_to_10s": row["latency_3s_10s"],
                "gte_10s": row["latency_gte_10s"],
            },
            "error_category_counts": {
                "authentication": row["error_authentication"],
                "rate_limit": row["error_rate_limit"],
                "timeout": row["error_timeout"],
                "unavailable": row["error_unavailable"],
                "invalid_request": row["error_invalid_request"],
                "other": row["error_other"],
            },
            "fallback_count": row["fallback_count"],
        })
    return payload


@dataclass(frozen=True, slots=True)
class UploadResponse:
    """Transport-neutral result for the  implementation."""

    status_code: int | None = None
    body: dict | None = None
    failure_kind: str | None = None


class TelemetryUploadClient(Protocol):
    """No implementation is provided in 003-A; implementations arrive in 003-B."""

    def upload(self, payload: dict) -> UploadResponse: ...


class TelemetryBatchStore:
    def __init__(self, database: TelemetryDatabase, consent: TelemetryConsent):
        self.database = database
        self.consent = consent

    def create_pending(self, schema_version: int = 2) -> dict | None:
        if not self.consent.is_granted(schema_version):
            return None
        state = self.consent.state()
        expected = CONSENT_VERSIONS.get(schema_version)
        if state["consent_version"] != expected:
            return None
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM daily_aggregates WHERE schema_version=? "
                "ORDER BY aggregation_day, provider, model_value, call_channel LIMIT 500",
                (schema_version,),
            ).fetchall()
            if not rows:
                return None
            client_versions = {row["client_version"] for row in rows}
            if len(client_versions) != 1:
                # Server requires every row to match the outer client version.
                selected = sorted(client_versions)[0]
                rows = [row for row in rows if row["client_version"] == selected]
            client_version = rows[0]["client_version"]
            batch_id = "batch_" + uuid.uuid4().hex
            payload = {
                "schema_version": schema_version,
                "batch_id": batch_id,
                "installation_id": self.consent.installation_id(),
                "consent_version": expected,
                "consent": True,
                "client_version": client_version,
                "aggregated_rows": [_row_payload(row, schema_version) for row in rows],
            }
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "INSERT INTO batches(batch_id, state, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (batch_id, "pending", json.dumps(payload, ensure_ascii=False, sort_keys=True), now, now),
            )
            connection.executemany("""
                DELETE FROM daily_aggregates
                WHERE schema_version=? AND client_version=? AND operating_system=? AND provider=?
                  AND model_type=? AND model_value=? AND aggregation_day=? AND call_channel=?
            """, [tuple(row[key] for key in (
                "schema_version", "client_version", "operating_system", "provider",
                "model_type", "model_value", "aggregation_day", "call_channel")) for row in rows])
        return {"state": "pending", "payload": payload}

    def read(self, batch_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT state, payload_json, created_at, updated_at FROM batches WHERE batch_id = ?", (batch_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "state": row["state"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_retryable(self, schema_version: int = 2) -> list[dict]:
        # Withdrawal makes all stored batches ineligible for upload while
        # retaining them locally. A later explicit grant may make them
        # retryable again without changing any counters.
        if not self.consent.is_granted(schema_version):
            return []
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT batch_id FROM batches WHERE state IN ('pending', 'uploading', 'rejected') ORDER BY created_at"
            ).fetchall()
        batches = [self.read(row["batch_id"]) for row in rows]
        return [batch for batch in batches if batch and batch["payload"].get("schema_version") == schema_version]

    def set_state(self, batch_id: str, state: str) -> None:
        if state not in BATCH_STATES:
            raise ValueError("invalid telemetry batch state")
        self.database.execute_with_retry(
            "UPDATE batches SET state=?, updated_at=? WHERE batch_id=?",
            (state, datetime.now(timezone.utc).isoformat(), batch_id),
        )

    def apply_upload_response(self, batch_id: str, response: UploadResponse) -> bool:
        """Guard the state transition without implementing any network transport."""
        valid_http = response.status_code is not None and 200 <= response.status_code < 300
        valid_ack = (
            isinstance(response.body, dict)
            and response.body.get("ack") is True
            and response.body.get("batch_id") == batch_id
        )
        if valid_http and valid_ack:
            self.set_state(batch_id, "acknowledged")
            return True
        # Explicit server/ACK rejection is retained as rejected; connection-like
        # failures return to pending. Both remain retryable and are never deleted.
        self.set_state(batch_id, "rejected" if response.status_code is not None else "pending")
        return False
