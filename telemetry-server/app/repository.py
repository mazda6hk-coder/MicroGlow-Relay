from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import hmac
import json
from typing import Any, Protocol

import asyncpg

from .geoip import COUNTRY_SOURCE_GAP, GEOIP_SOURCE
from .schemas import ISO_ALPHA2, TelemetryBatch


class BatchConflict(Exception):
    pass


@dataclass(frozen=True, slots=True)
class InsertResult:
    duplicate: bool
    accepted_rows: int


class Repository(Protocol):
    async def health(self) -> None: ...
    async def insert_batch(
        self,
        batch: TelemetryBatch,
        country_code: str | None = None,
        country_source: str = COUNTRY_SOURCE_GAP,
    ) -> InsertResult: ...
    async def usage_summary(self, from_day: date | None = None, to_day: date | None = None) -> dict[str, Any]: ...
    async def close(self) -> None: ...


def installation_hash(secret: str, installation_id: str) -> str:
    return hmac.new(secret.encode("utf-8"), installation_id.encode("utf-8"), hashlib.sha256).hexdigest()


def payload_hash(batch: TelemetryBatch) -> str:
    payload = batch.model_dump(mode="json")
    # Preserve pre-channel hashes for immutable pending legacy batches.
    for row, original in zip(payload["aggregated_rows"], batch.aggregated_rows):
        if "call_channel" not in original.model_fields_set:
            row.pop("call_channel", None)
        if "operating_system" not in original.model_fields_set:
            row.pop("operating_system", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def collapsed_rows(
    batch: TelemetryBatch,
    country_code: str | None = None,
    country_source: str = COUNTRY_SOURCE_GAP,
) -> list[dict[str, Any]]:
    if not (
        (country_source == GEOIP_SOURCE and country_code in ISO_ALPHA2)
        or (country_source == COUNTRY_SOURCE_GAP and country_code is None)
    ):
        raise ValueError("invalid server country provenance")
    buckets: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in batch.aggregated_rows:
        key = (
            row.aggregation_day, country_code, country_source, row.operating_system,
            row.provider, row.normalized_model, row.model_type, row.client_version, row.call_channel,
        )
        target = buckets.setdefault(key, {
            "day": row.aggregation_day,
            "country_code": country_code,
            "country_source": country_source,
            # Existing NOT NULL column/index uses an empty legacy slot, not an inferred OS.
            "operating_system": row.operating_system or "",
            "provider": row.provider,
            "model": row.normalized_model,
            "model_type": row.model_type,
            "client_version": row.client_version,
            "call_channel": row.call_channel,
            "active_minutes": 0,
            "api_call_count": 0,
            "success_count": 0,
            "error_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "latency_lt_1s": 0,
            "latency_1s_3s": 0,
            "latency_3s_10s": 0,
            "latency_gte_10s": 0,
            "error_authentication": 0,
            "error_rate_limit": 0,
            "error_timeout": 0,
            "error_unavailable": 0,
            "error_invalid_request": 0,
            "error_other": 0,
            "fallback_count": 0,
        })
        for field in (
            "active_minutes", "api_call_count", "success_count", "error_count",
            "input_tokens", "output_tokens", "total_tokens",
        ):
            target[field] += getattr(row, field)
        if row.latency_buckets is not None:
            target["latency_lt_1s"] += row.latency_buckets.lt_1s
            target["latency_1s_3s"] += row.latency_buckets.from_1s_to_3s
            target["latency_3s_10s"] += row.latency_buckets.from_3s_to_10s
            target["latency_gte_10s"] += row.latency_buckets.gte_10s
        if row.error_category_counts is not None:
            target["error_authentication"] += row.error_category_counts.authentication
            target["error_rate_limit"] += row.error_category_counts.rate_limit
            target["error_timeout"] += row.error_category_counts.timeout
            target["error_unavailable"] += row.error_category_counts.unavailable
            target["error_invalid_request"] += row.error_category_counts.invalid_request
            target["error_other"] += row.error_category_counts.other
        target["fallback_count"] += int(row.fallback_count or 0)
    return list(buckets.values())


class PostgresRepository:
    def __init__(self, pool: asyncpg.Pool, hmac_secret: str):
        self.pool = pool
        self.hmac_secret = hmac_secret

    @classmethod
    async def connect(cls, database_url: str, hmac_secret: str) -> "PostgresRepository":
        url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        async def initialize(connection: asyncpg.Connection) -> None:
            await connection.execute("SET TIME ZONE 'UTC'")

        pool = await asyncpg.create_pool(
            url, min_size=1, max_size=10, command_timeout=30, init=initialize,
        )
        return cls(pool, hmac_secret)

    async def close(self) -> None:
        await self.pool.close()

    async def health(self) -> None:
        async with self.pool.acquire() as connection:
            await connection.fetchval("SELECT 1")

    async def insert_batch(
        self,
        batch: TelemetryBatch,
        country_code: str | None = None,
        country_source: str = COUNTRY_SOURCE_GAP,
    ) -> InsertResult:
        digest = payload_hash(batch)
        install_digest = installation_hash(self.hmac_secret, batch.installation_id)
        rows = collapsed_rows(batch, country_code, country_source)
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                inserted = await connection.fetchval(
                    """
                    INSERT INTO telemetry_batches
                        (batch_id, installation_hash, schema_version, consent_version, row_count,
                         payload_hash, aggregation_day_min, aggregation_day_max)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (batch_id) DO NOTHING
                    RETURNING batch_id
                    """,
                    batch.batch_id, install_digest, batch.schema_version,
                    batch.consent_version, len(batch.aggregated_rows), digest,
                    min(row.aggregation_day for row in batch.aggregated_rows),
                    max(row.aggregation_day for row in batch.aggregated_rows),
                )
                if inserted is None:
                    existing = await connection.fetchval(
                        "SELECT payload_hash FROM telemetry_batches WHERE batch_id = $1",
                        batch.batch_id,
                    )
                    if existing != digest:
                        raise BatchConflict("batch_id already exists with another payload")
                    return InsertResult(duplicate=True, accepted_rows=0)

                for row in rows:
                    await connection.execute(
                        """
                        INSERT INTO usage_daily (
                            day, country_code, country_source, operating_system, provider, model, model_type,
                            client_version, installation_hash, active_minutes, api_call_count,
                            success_count, error_count, input_tokens, output_tokens, total_tokens,
                            latency_lt_1s, latency_1s_3s, latency_3s_10s, latency_gte_10s,
                            error_authentication, error_rate_limit, error_timeout,
                            error_unavailable, error_invalid_request, error_other, fallback_count, call_channel
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                            $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28
                        )
                        ON CONFLICT (
                            day, country_code, country_source, operating_system, provider, model, model_type,
                            client_version, installation_hash, call_channel
                        ) DO UPDATE SET
                            active_minutes = usage_daily.active_minutes + EXCLUDED.active_minutes,
                            api_call_count = usage_daily.api_call_count + EXCLUDED.api_call_count,
                            success_count = usage_daily.success_count + EXCLUDED.success_count,
                            error_count = usage_daily.error_count + EXCLUDED.error_count,
                            input_tokens = usage_daily.input_tokens + EXCLUDED.input_tokens,
                            output_tokens = usage_daily.output_tokens + EXCLUDED.output_tokens,
                            total_tokens = usage_daily.total_tokens + EXCLUDED.total_tokens,
                            latency_lt_1s = usage_daily.latency_lt_1s + EXCLUDED.latency_lt_1s,
                            latency_1s_3s = usage_daily.latency_1s_3s + EXCLUDED.latency_1s_3s,
                            latency_3s_10s = usage_daily.latency_3s_10s + EXCLUDED.latency_3s_10s,
                            latency_gte_10s = usage_daily.latency_gte_10s + EXCLUDED.latency_gte_10s,
                            error_authentication = usage_daily.error_authentication + EXCLUDED.error_authentication,
                            error_rate_limit = usage_daily.error_rate_limit + EXCLUDED.error_rate_limit,
                            error_timeout = usage_daily.error_timeout + EXCLUDED.error_timeout,
                            error_unavailable = usage_daily.error_unavailable + EXCLUDED.error_unavailable,
                            error_invalid_request = usage_daily.error_invalid_request + EXCLUDED.error_invalid_request,
                            error_other = usage_daily.error_other + EXCLUDED.error_other,
                            fallback_count = usage_daily.fallback_count + EXCLUDED.fallback_count
                        """,
                        row["day"], row["country_code"], row["country_source"],
                        row["operating_system"], row["provider"], row["model"], row["model_type"],
                        row["client_version"], install_digest, row["active_minutes"],
                        row["api_call_count"], row["success_count"], row["error_count"],
                        row["input_tokens"], row["output_tokens"], row["total_tokens"],
                        row["latency_lt_1s"], row["latency_1s_3s"],
                        row["latency_3s_10s"], row["latency_gte_10s"],
                        row["error_authentication"], row["error_rate_limit"],
                        row["error_timeout"], row["error_unavailable"],
                        row["error_invalid_request"], row["error_other"],
                        row["fallback_count"], row["call_channel"],
                    )
        return InsertResult(duplicate=False, accepted_rows=len(batch.aggregated_rows))

    async def usage_summary(
        self, from_day: date | None = None, to_day: date | None = None,
    ) -> dict[str, Any]:
        filtered = "WHERE ($1::date IS NULL OR day >= $1) AND ($2::date IS NULL OR day <= $2)"
        async with self.pool.acquire() as connection:
            channels = await connection.fetch(f"""
                SELECT client_version, model, model_type, call_channel,
                       SUM(api_call_count)::bigint AS api_call_count,
                       SUM(success_count)::bigint AS success_count,
                       SUM(error_count)::bigint AS error_count,
                       SUM(input_tokens)::bigint AS input_tokens,
                       SUM(output_tokens)::bigint AS output_tokens,
                       SUM(total_tokens)::bigint AS total_tokens,
                       SUM(active_minutes)::bigint AS active_minutes,
                       COUNT(DISTINCT installation_hash)::bigint AS active_installations
                FROM usage_daily {filtered}
                GROUP BY client_version, model, model_type, call_channel
                ORDER BY SUM(api_call_count) DESC, client_version, model, call_channel
            """, from_day, to_day)
            countries = await connection.fetch(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered})
                SELECT country_code, country_source, SUM(api_call_count)::bigint AS api_call_count,
                       SUM(total_tokens)::bigint AS total_tokens,
                       COUNT(DISTINCT installation_hash)::bigint AS active_installations,
                       COALESCE(SUM(api_call_count)::double precision /
                           NULLIF(SUM(SUM(api_call_count)) OVER (), 0), 0) AS call_share
                FROM filtered GROUP BY country_code, country_source
                ORDER BY api_call_count DESC, country_code NULLS LAST
            """, from_day, to_day)
            model_groups = {}
            for dimension in ("provider", "client_version"):
                model_groups[dimension] = await connection.fetch(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered})
                SELECT {dimension}, model, model_type,
                       SUM(api_call_count)::bigint AS api_call_count,
                       SUM(total_tokens)::bigint AS total_tokens,
                       COUNT(DISTINCT installation_hash)::bigint AS active_installations,
                       COALESCE(SUM(api_call_count)::double precision /
                           NULLIF(SUM(SUM(api_call_count)) OVER (), 0), 0) AS call_share,
                       COALESCE(SUM(total_tokens)::double precision /
                           NULLIF(SUM(SUM(total_tokens)) OVER (), 0), 0) AS token_share,
                       COALESCE(SUM(success_count)::double precision /
                           NULLIF(SUM(api_call_count), 0), 0) AS success_rate
                FROM filtered GROUP BY {dimension}, model, model_type
                ORDER BY api_call_count DESC, {dimension}, model, model_type
                """, from_day, to_day)
            models = model_groups["provider"]
            version_models = model_groups["client_version"]
            periods: dict[str, list[dict[str, Any]]] = {}
            expressions = {
                "daily": ("day", "first_day"),
                "weekly": ("date_trunc('week', day)::date", "date_trunc('week', first_day)::date"),
                "monthly": ("date_trunc('month', day)::date", "date_trunc('month', first_day)::date"),
            }
            for name, (expression, first_expression) in expressions.items():
                records = await connection.fetch(f"""
                    WITH first_seen AS (
                        SELECT installation_hash, MIN(day) AS first_day
                        FROM usage_daily GROUP BY installation_hash
                    ), filtered AS (SELECT * FROM usage_daily {filtered})
                    SELECT {expression} AS period,
                           SUM(api_call_count)::bigint AS api_call_count,
                           SUM(total_tokens)::bigint AS total_tokens,
                           COUNT(DISTINCT filtered.installation_hash)::bigint AS active_installations,
                           COUNT(DISTINCT filtered.installation_hash)
                               FILTER (WHERE {first_expression} = {expression})::bigint AS new_installations
                    FROM filtered JOIN first_seen USING (installation_hash)
                    GROUP BY period ORDER BY period
                """, from_day, to_day)
                period_rows = [_json_record(record) for record in records]
                for row in period_rows:
                    row["returning_installations"] = row["active_installations"] - row["new_installations"]
                periods[name] = period_rows
            duration = await connection.fetch(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered}), totals AS (
                    SELECT installation_hash, SUM(active_minutes)::bigint AS minutes
                    FROM filtered GROUP BY installation_hash
                )
                SELECT CASE
                    WHEN minutes = 0 THEN '0'
                    WHEN minutes <= 30 THEN '1-30'
                    WHEN minutes <= 120 THEN '31-120'
                    WHEN minutes <= 600 THEN '121-600'
                    ELSE '601+'
                END AS range, COUNT(*)::bigint AS active_installations
                FROM totals GROUP BY range ORDER BY MIN(minutes)
            """, from_day, to_day)
            outcomes = await connection.fetchrow(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered})
                SELECT COALESCE(SUM(success_count), 0)::bigint AS success,
                       COALESCE(SUM(error_count), 0)::bigint AS error,
                       COALESCE(SUM(api_call_count), 0)::bigint AS total,
                       COALESCE(SUM(input_tokens), 0)::bigint AS input_tokens,
                       COALESCE(SUM(output_tokens), 0)::bigint AS output_tokens,
                       COALESCE(SUM(total_tokens), 0)::bigint AS total_tokens,
                       COALESCE(SUM(fallback_count), 0)::bigint AS fallback_count
                FROM filtered
            """, from_day, to_day)
            activity = await connection.fetchrow(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered}), bounds AS (
                    SELECT COALESCE($2::date, MAX(day)) AS end_day FROM filtered
                )
                SELECT
                    end_day AS as_of_day,
                    COUNT(DISTINCT installation_hash) FILTER (WHERE day = end_day)::bigint AS dau,
                    COUNT(DISTINCT installation_hash) FILTER (WHERE day >= end_day - 6)::bigint AS wau,
                    COUNT(DISTINCT installation_hash) FILTER (WHERE day >= end_day - 29)::bigint AS mau,
                    COALESCE(SUM(api_call_count) FILTER (WHERE day >= end_day - 6), 0)::bigint AS current_week_calls,
                    COALESCE(SUM(api_call_count) FILTER (WHERE day BETWEEN end_day - 13 AND end_day - 7), 0)::bigint AS previous_week_calls,
                    COALESCE(SUM(total_tokens) FILTER (WHERE day >= end_day - 6), 0)::bigint AS current_week_tokens,
                    COALESCE(SUM(total_tokens) FILTER (WHERE day BETWEEN end_day - 13 AND end_day - 7), 0)::bigint AS previous_week_tokens
                FROM filtered CROSS JOIN bounds GROUP BY end_day
            """, from_day, to_day)
            range_installations = await connection.fetchrow(f"""
                WITH first_seen AS (
                    SELECT installation_hash, MIN(day) AS first_day
                    FROM usage_daily GROUP BY installation_hash
                ), filtered AS (SELECT * FROM usage_daily {filtered}), active AS (
                    SELECT DISTINCT installation_hash FROM filtered
                ), bounds AS (
                    SELECT MIN(day) AS start_day, COALESCE($2::date, MAX(day)) AS end_day
                    FROM filtered
                )
                SELECT COUNT(*) FILTER (
                           WHERE first_day BETWEEN start_day AND end_day
                       )::bigint AS new_installations,
                       COUNT(*) FILTER (
                           WHERE first_day < start_day
                       )::bigint AS returning_installations
                FROM active JOIN first_seen USING (installation_hash) CROSS JOIN bounds
            """, from_day, to_day)
            distributions = await connection.fetchrow(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered}), per_installation AS (
                    SELECT installation_hash, SUM(api_call_count)::bigint AS calls,
                           SUM(total_tokens)::bigint AS tokens,
                           SUM(active_minutes)::bigint AS active_minutes
                    FROM filtered GROUP BY installation_hash
                )
                SELECT COUNT(*)::bigint AS installations,
                       COALESCE(AVG(calls), 0)::double precision AS avg_calls,
                       COALESCE(AVG(tokens), 0)::double precision AS avg_tokens,
                       COALESCE(AVG(active_minutes), 0)::double precision AS avg_active_minutes,
                       COALESCE(percentile_cont(0.5) WITHIN GROUP (ORDER BY calls), 0)::double precision AS calls_p50,
                       COALESCE(percentile_cont(0.9) WITHIN GROUP (ORDER BY calls), 0)::double precision AS calls_p90,
                       COALESCE(percentile_cont(0.99) WITHIN GROUP (ORDER BY calls), 0)::double precision AS calls_p99,
                       COALESCE(percentile_cont(0.5) WITHIN GROUP (ORDER BY tokens), 0)::double precision AS tokens_p50,
                       COALESCE(percentile_cont(0.9) WITHIN GROUP (ORDER BY tokens), 0)::double precision AS tokens_p90,
                       COALESCE(percentile_cont(0.99) WITHIN GROUP (ORDER BY tokens), 0)::double precision AS tokens_p99
                FROM per_installation
            """, from_day, to_day)
            retention = await connection.fetchrow("""
                WITH first_seen AS (
                    SELECT installation_hash, MIN(day) AS first_day
                    FROM usage_daily GROUP BY installation_hash
                ), bounds AS (
                    SELECT COALESCE($2::date, MAX(day)) AS end_day FROM usage_daily
                    WHERE ($1::date IS NULL OR day >= $1) AND ($2::date IS NULL OR day <= $2)
                ), cohorts AS (
                    SELECT * FROM first_seen CROSS JOIN bounds
                    WHERE ($1::date IS NULL OR first_day >= $1)
                      AND ($2::date IS NULL OR first_day <= $2)
                )
                SELECT
                    COUNT(*) FILTER (WHERE first_day <= end_day - 7)::bigint AS eligible_7,
                    COUNT(*) FILTER (WHERE first_day <= end_day - 7 AND EXISTS (
                        SELECT 1 FROM usage_daily activity
                        WHERE activity.installation_hash = cohorts.installation_hash
                          AND activity.day = first_day + 7
                    ))::bigint AS retained_7,
                    COUNT(*) FILTER (WHERE first_day <= end_day - 30)::bigint AS eligible_30,
                    COUNT(*) FILTER (WHERE first_day <= end_day - 30 AND EXISTS (
                        SELECT 1 FROM usage_daily activity
                        WHERE activity.installation_hash = cohorts.installation_hash
                          AND activity.day = first_day + 30
                    ))::bigint AS retained_30
                FROM cohorts
            """, from_day, to_day)
            versions = await connection.fetch(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered})
                SELECT client_version, COUNT(DISTINCT installation_hash)::bigint AS active_installations,
                       SUM(api_call_count)::bigint AS api_call_count,
                       SUM(total_tokens)::bigint AS total_tokens
                FROM filtered GROUP BY client_version ORDER BY active_installations DESC, client_version
            """, from_day, to_day)
            trend_groups = {}
            for dimension in ("provider", "client_version"):
                trend_groups[dimension] = await connection.fetch(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered})
                SELECT date_trunc('month', day)::date AS period, {dimension}, model, model_type,
                       SUM(api_call_count)::bigint AS api_call_count,
                       SUM(total_tokens)::bigint AS total_tokens
                FROM filtered GROUP BY period, {dimension}, model, model_type
                ORDER BY period, api_call_count DESC, {dimension}, model, model_type
                """, from_day, to_day)
            provider_trends = trend_groups["provider"]
            version_model_trends = trend_groups["client_version"]
            quality = await connection.fetchrow(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered})
                SELECT COALESCE(SUM(latency_lt_1s), 0)::bigint AS lt_1s,
                       COALESCE(SUM(latency_1s_3s), 0)::bigint AS from_1s_to_3s,
                       COALESCE(SUM(latency_3s_10s), 0)::bigint AS from_3s_to_10s,
                       COALESCE(SUM(latency_gte_10s), 0)::bigint AS gte_10s,
                       COALESCE(SUM(error_authentication), 0)::bigint AS authentication,
                       COALESCE(SUM(error_rate_limit), 0)::bigint AS rate_limit,
                       COALESCE(SUM(error_timeout), 0)::bigint AS timeout,
                       COALESCE(SUM(error_unavailable), 0)::bigint AS unavailable,
                       COALESCE(SUM(error_invalid_request), 0)::bigint AS invalid_request,
                       COALESCE(SUM(error_other), 0)::bigint AS other
                FROM filtered
            """, from_day, to_day)
            data_quality = await connection.fetchrow(f"""
                WITH filtered AS (SELECT * FROM usage_daily {filtered})
                SELECT MIN(day) AS first_day, MAX(day) AS latest_day,
                       COUNT(*)::bigint AS aggregate_rows,
                       COUNT(DISTINCT installation_hash)::bigint AS active_installations,
                       COUNT(DISTINCT client_version)::bigint AS client_versions,
                       CASE WHEN MAX(day) IS NULL THEN NULL ELSE GREATEST(CURRENT_DATE - MAX(day), 0) END AS freshness_days,
                       (SELECT MAX(received_at) FROM telemetry_batches
                        WHERE ($1::date IS NULL OR aggregation_day_max IS NULL OR aggregation_day_max >= $1)
                          AND ($2::date IS NULL OR aggregation_day_min IS NULL OR aggregation_day_min <= $2)) AS last_successful_received_at
                FROM filtered
            """, from_day, to_day)
            schema_coverage = await connection.fetch("""
                SELECT schema_version, consent_version, COUNT(*)::bigint AS batches,
                       SUM(row_count)::bigint AS rows
                FROM telemetry_batches
                WHERE ($1::date IS NULL OR aggregation_day_max IS NULL OR aggregation_day_max >= $1)
                  AND ($2::date IS NULL OR aggregation_day_min IS NULL OR aggregation_day_min <= $2)
                GROUP BY schema_version, consent_version
                ORDER BY schema_version, consent_version
            """, from_day, to_day)

        outcome = _json_record(outcomes)
        outcome["success_rate"] = (outcome["success"] / outcome["total"]) if outcome["total"] else 0.0
        activity_data = _json_record(activity or {})
        activity_data["week_call_growth"] = _growth(
            activity_data.get("current_week_calls", 0), activity_data.get("previous_week_calls", 0)
        )
        activity_data["week_token_growth"] = _growth(
            activity_data.get("current_week_tokens", 0), activity_data.get("previous_week_tokens", 0)
        )
        activity_data.update(_json_record(range_installations or {}))
        retention_data = _json_record(retention or {})
        retention_data["day_7_rate"] = _retention_rate(
            retention_data.get("retained_7", 0), retention_data.get("eligible_7", 0)
        )
        retention_data["day_30_rate"] = _retention_rate(
            retention_data.get("retained_30", 0), retention_data.get("eligible_30", 0)
        )
        quality_data = _json_record(quality)
        distribution_data = _json_record(distributions)
        distribution_data["sample_size"] = distribution_data.pop("installations", 0)
        for prefix in ("calls", "tokens"):
            for percentile, minimum in ((50, 2), (90, 10), (99, 100)):
                if distribution_data["sample_size"] < minimum:
                    distribution_data[f"{prefix}_p{percentile}"] = None
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "timezone": "UTC",
            "filters": {"from_day": from_day.isoformat() if from_day else None,
                        "to_day": to_day.isoformat() if to_day else None},
            "by_country": [_json_record(record) for record in countries],
            "by_provider_model": [_json_record(record) for record in models],
            "by_relay_version_model": [_json_record(record) for record in version_models],
            "by_relay_version_model_channel": [_json_record(record) for record in channels],
            "provider_model_trends": [_json_record(record) for record in provider_trends],
            "relay_version_model_trends": [_json_record(record) for record in version_model_trends],
            "periods": periods,
            "active_installations": int(distribution_data["sample_size"]),
            "activity": activity_data,
            "retention": retention_data,
            "usage_distribution": distribution_data,
            "active_minutes_ranges": [_json_record(record) for record in duration],
            "client_versions": [_json_record(record) for record in versions],
            "outcomes": outcome,
            "latency_buckets": {key: quality_data[key] for key in (
                "lt_1s", "from_1s_to_3s", "from_3s_to_10s", "gte_10s"
            )},
            "error_categories": [
                {"category": key, "count": quality_data[key]}
                for key in ("authentication", "rate_limit", "timeout", "unavailable", "invalid_request", "other")
            ],
            "data_quality": _json_record(data_quality),
            "schema_coverage": [_json_record(record) for record in schema_coverage],
            "methodology": _methodology(),
        }


def _json_record(record: Any) -> dict[str, Any]:
    result = dict(record)
    for key, value in tuple(result.items()):
        if isinstance(value, date):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
    return result


def _rate(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _retention_rate(numerator: int | float, denominator: int | float) -> float | None:
    return _rate(numerator, denominator) if denominator else None


def _growth(current: int | float, previous: int | float) -> float | None:
    if not previous:
        return None if current else 0.0
    return (float(current) - float(previous)) / float(previous)


def _methodology() -> dict[str, Any]:
    return {
        "timezone": "UTC",
        "active_unit": "active_installation",
        "dau": "distinct active installations on the UTC as-of calendar day",
        "wau": "distinct active installations in the rolling 7 UTC days ending on as-of day",
        "mau": "distinct active installations in the rolling 30 UTC days ending on as-of day",
        "new_installation": "first observed UTC day is inside the selected range",
        "returning_installation": "first observed before the selected range and active again inside it",
        "retention_day_7": "active on the exact 7th UTC day after first activity",
        "retention_day_30": "active on the exact 30th UTC day after first activity",
        "api_call_total": "includes successful and failed calls; success_count + error_count",
        "token_total": "input_tokens + output_tokens",
        "percentile_min_samples": {"p50": 2, "p90": 10, "p99": 100},
    }


class MemoryRepository:
    """Test repository implementing the same idempotency and summaries."""

    def __init__(self, hmac_secret: str):
        self.hmac_secret = hmac_secret
        self.batches: dict[str, str] = {}
        self.batch_metadata: list[dict[str, Any]] = []
        self.rows: list[dict[str, Any]] = []

    async def close(self) -> None:
        return None

    async def health(self) -> None:
        return None

    async def insert_batch(
        self,
        batch: TelemetryBatch,
        country_code: str | None = None,
        country_source: str = COUNTRY_SOURCE_GAP,
    ) -> InsertResult:
        digest = payload_hash(batch)
        if batch.batch_id in self.batches:
            if self.batches[batch.batch_id] != digest:
                raise BatchConflict
            return InsertResult(True, 0)
        self.batches[batch.batch_id] = digest
        self.batch_metadata.append({
            "schema_version": batch.schema_version,
            "consent_version": batch.consent_version,
            "rows": len(batch.aggregated_rows),
            "received_at": datetime.now(timezone.utc),
            "aggregation_day_min": min(row.aggregation_day for row in batch.aggregated_rows),
            "aggregation_day_max": max(row.aggregation_day for row in batch.aggregated_rows),
        })
        install_digest = installation_hash(self.hmac_secret, batch.installation_id)
        for row in collapsed_rows(batch, country_code, country_source):
            self.rows.append({**row, "installation_hash": install_digest})
        return InsertResult(False, len(batch.aggregated_rows))

    async def usage_summary(
        self, from_day: date | None = None, to_day: date | None = None,
    ) -> dict[str, Any]:
        rows = [
            row for row in self.rows
            if (from_day is None or row["day"] >= from_day)
            and (to_day is None or row["day"] <= to_day)
        ]
        first_seen: dict[str, date] = {}
        for row in self.rows:
            client = row["installation_hash"]
            first_seen[client] = min(first_seen.get(client, row["day"]), row["day"])

        def aggregate(source: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
            result: dict[tuple[Any, ...], dict[str, Any]] = {}
            for row in source:
                group = tuple(row[key] for key in keys)
                item = result.setdefault(group, {key: row[key] for key in keys} | {
                    "api_call_count": 0, "total_tokens": 0, "success_count": 0,
                    "error_count": 0, "input_tokens": 0, "output_tokens": 0, "active_minutes": 0,
                    "_clients": set(),
                })
                item["api_call_count"] += row["api_call_count"]
                item["total_tokens"] += row["total_tokens"]
                item["success_count"] += row["success_count"]
                for field in ("error_count", "input_tokens", "output_tokens", "active_minutes"):
                    item[field] += row[field]
                item["_clients"].add(row["installation_hash"])
            output = []
            for item in result.values():
                clients = item.pop("_clients")
                item["active_installations"] = len(clients)
                output.append(item)
            return output

        clients = {row["installation_hash"] for row in rows}
        total_calls = sum(row["api_call_count"] for row in rows)
        total_tokens = sum(row["total_tokens"] for row in rows)
        success = sum(row["success_count"] for row in rows)
        error = sum(row["error_count"] for row in rows)

        countries = aggregate(rows, ("country_code", "country_source"))
        for item in countries:
            item["call_share"] = _rate(item["api_call_count"], total_calls)
            item.pop("success_count")
        countries.sort(key=lambda item: (-item["api_call_count"], item["country_code"] or ""))

        model_groups = {}
        for dimension in ("provider", "client_version"):
            grouped_models = aggregate(rows, (dimension, "model", "model_type"))
            for item in grouped_models:
                item["call_share"] = _rate(item["api_call_count"], total_calls)
                item["token_share"] = _rate(item["total_tokens"], total_tokens)
                item["success_rate"] = _rate(item.pop("success_count"), item["api_call_count"])
            grouped_models.sort(key=lambda item: (-item["api_call_count"], item[dimension], item["model"], item["model_type"]))
            model_groups[dimension] = grouped_models
        models = model_groups["provider"]
        version_models = model_groups["client_version"]

        def period_start(day_value: date, name: str) -> date:
            if name == "weekly":
                return day_value - timedelta(days=day_value.weekday())
            if name == "monthly":
                return day_value.replace(day=1)
            return day_value

        periods: dict[str, list[dict[str, Any]]] = {}
        for name in ("daily", "weekly", "monthly"):
            period_rows = [{**row, "period": period_start(row["day"], name)} for row in rows]
            grouped = aggregate(period_rows, ("period",))
            for item in grouped:
                period_value = item["period"]
                item["new_installations"] = len({
                    row["installation_hash"] for row in period_rows
                    if row["period"] == period_value
                    and period_start(first_seen[row["installation_hash"]], name) == period_value
                })
                item["returning_installations"] = item["active_installations"] - item["new_installations"]
                item["period"] = period_value.isoformat()
                item.pop("success_count")
            periods[name] = sorted(grouped, key=lambda item: item["period"])

        per_installation: dict[str, dict[str, int]] = defaultdict(
            lambda: {"calls": 0, "tokens": 0, "active_minutes": 0}
        )
        for row in rows:
            item = per_installation[row["installation_hash"]]
            item["calls"] += row["api_call_count"]
            item["tokens"] += row["total_tokens"]
            item["active_minutes"] += row["active_minutes"]

        def percentile(values: list[int], quantile: float) -> float:
            if not values:
                return 0.0
            ordered = sorted(values)
            position = (len(ordered) - 1) * quantile
            lower = int(position)
            upper = min(lower + 1, len(ordered) - 1)
            fraction = position - lower
            return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction

        calls = [item["calls"] for item in per_installation.values()]
        tokens = [item["tokens"] for item in per_installation.values()]
        minutes = [item["active_minutes"] for item in per_installation.values()]
        distributions = {
            "installations": len(per_installation),
            "avg_calls": sum(calls) / len(calls) if calls else 0.0,
            "avg_tokens": sum(tokens) / len(tokens) if tokens else 0.0,
            "avg_active_minutes": sum(minutes) / len(minutes) if minutes else 0.0,
            **{f"calls_p{int(q * 100)}": percentile(calls, q) for q in (0.5, 0.9, 0.99)},
            **{f"tokens_p{int(q * 100)}": percentile(tokens, q) for q in (0.5, 0.9, 0.99)},
        }
        ranges = [
            ("0", lambda value: value == 0),
            ("1-30", lambda value: 1 <= value <= 30),
            ("31-120", lambda value: 31 <= value <= 120),
            ("121-600", lambda value: 121 <= value <= 600),
            ("601+", lambda value: value >= 601),
        ]
        duration = [
            {"range": label, "active_installations": sum(1 for value in minutes if predicate(value))}
            for label, predicate in ranges if any(predicate(value) for value in minutes)
        ]

        latest_data_day = max((row["day"] for row in rows), default=None)
        end_day = to_day or latest_data_day
        def calls_between(start: date, end: date, field: str = "api_call_count") -> int:
            return sum(row[field] for row in rows if start <= row["day"] <= end)
        if end_day:
            dau = len({row["installation_hash"] for row in rows if row["day"] == end_day})
            wau = len({row["installation_hash"] for row in rows if row["day"] >= end_day - timedelta(days=6)})
            mau = len({row["installation_hash"] for row in rows if row["day"] >= end_day - timedelta(days=29)})
            current_week_calls = calls_between(end_day - timedelta(days=6), end_day)
            previous_week_calls = calls_between(end_day - timedelta(days=13), end_day - timedelta(days=7))
            current_week_tokens = calls_between(end_day - timedelta(days=6), end_day, "total_tokens")
            previous_week_tokens = calls_between(end_day - timedelta(days=13), end_day - timedelta(days=7), "total_tokens")
        else:
            dau = wau = mau = current_week_calls = previous_week_calls = 0
            current_week_tokens = previous_week_tokens = 0
        activity = {
            "as_of_day": end_day.isoformat() if end_day else None,
            "dau": dau, "wau": wau, "mau": mau,
            "current_week_calls": current_week_calls,
            "previous_week_calls": previous_week_calls,
            "current_week_tokens": current_week_tokens,
            "previous_week_tokens": previous_week_tokens,
            "week_call_growth": _growth(current_week_calls, previous_week_calls),
            "week_token_growth": _growth(current_week_tokens, previous_week_tokens),
        }
        range_start = from_day or min((row["day"] for row in rows), default=None)
        if range_start and end_day:
            activity["new_installations"] = len({
                client for client in clients if range_start <= first_seen[client] <= end_day
            })
            activity["returning_installations"] = len({
                client for client in clients if first_seen[client] < range_start
            })
        else:
            activity["new_installations"] = 0
            activity["returning_installations"] = 0

        cohort_clients = [
            (client, first_day) for client, first_day in first_seen.items()
            if (from_day is None or first_day >= from_day) and (to_day is None or first_day <= to_day)
        ]
        activity_days = defaultdict(set)
        for row in self.rows:
            activity_days[row["installation_hash"]].add(row["day"])
        def retention_at(offset: int) -> tuple[int, int]:
            if end_day is None:
                return 0, 0
            eligible = [(client, first) for client, first in cohort_clients if first <= end_day - timedelta(days=offset)]
            retained = sum(
                1 for client, first in eligible
                if first + timedelta(days=offset) in activity_days[client]
            )
            return len(eligible), retained
        eligible_7, retained_7 = retention_at(7)
        eligible_30, retained_30 = retention_at(30)
        retention = {
            "eligible_7": eligible_7, "retained_7": retained_7,
            "eligible_30": eligible_30, "retained_30": retained_30,
            "day_7_rate": _retention_rate(retained_7, eligible_7),
            "day_30_rate": _retention_rate(retained_30, eligible_30),
        }

        version_rows = aggregate(rows, ("client_version",))
        for item in version_rows:
            item.pop("success_count")
        version_rows.sort(key=lambda item: (-item["active_installations"], item["client_version"]))
        trend_source = [{**row, "period": row["day"].replace(day=1)} for row in rows]
        trend_groups = {}
        for dimension in ("provider", "client_version"):
            grouped_trends = aggregate(trend_source, ("period", dimension, "model", "model_type"))
            for item in grouped_trends:
                item["period"] = item["period"].isoformat()
                item.pop("success_count")
            grouped_trends.sort(key=lambda item: (item["period"], -item["api_call_count"], item[dimension], item["model"], item["model_type"]))
            trend_groups[dimension] = grouped_trends
        provider_trends = trend_groups["provider"]
        version_model_trends = trend_groups["client_version"]

        quality_keys = (
            "latency_lt_1s", "latency_1s_3s", "latency_3s_10s", "latency_gte_10s",
            "error_authentication", "error_rate_limit", "error_timeout",
            "error_unavailable", "error_invalid_request", "error_other", "fallback_count",
        )
        quality = {key: sum(row[key] for row in rows) for key in quality_keys}
        schema_groups: dict[tuple[int, str], dict[str, Any]] = {}
        filtered_batch_metadata = [
            item for item in self.batch_metadata
            if (from_day is None or item["aggregation_day_max"] >= from_day)
            and (to_day is None or item["aggregation_day_min"] <= to_day)
        ]
        for item in filtered_batch_metadata:
            key = (item["schema_version"], item["consent_version"])
            target = schema_groups.setdefault(key, {
                "schema_version": key[0], "consent_version": key[1], "batches": 0, "rows": 0,
            })
            target["batches"] += 1
            target["rows"] += item["rows"]

        distribution_data = dict(distributions)
        sample_size = int(distribution_data.pop("installations", 0))
        distribution_data["sample_size"] = sample_size
        for prefix in ("calls", "tokens"):
            for percentile, minimum in ((50, 2), (90, 10), (99, 100)):
                if sample_size < minimum:
                    distribution_data[f"{prefix}_p{percentile}"] = None

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "timezone": "UTC",
            "filters": {"from_day": from_day.isoformat() if from_day else None,
                        "to_day": to_day.isoformat() if to_day else None},
            "by_country": countries,
            "by_provider_model": models,
            "by_relay_version_model": version_models,
            "by_relay_version_model_channel": aggregate(rows, ("client_version", "model", "model_type", "call_channel")),
            "provider_model_trends": sorted(provider_trends, key=lambda item: (item["period"], -item["api_call_count"])),
            "relay_version_model_trends": version_model_trends,
            "periods": periods,
            "active_installations": len(clients),
            "activity": activity,
            "retention": retention,
            "usage_distribution": distribution_data,
            "active_minutes_ranges": duration,
            "client_versions": version_rows,
            "outcomes": {
                "success": success, "error": error, "total": total_calls,
                "input_tokens": sum(row["input_tokens"] for row in rows),
                "output_tokens": sum(row["output_tokens"] for row in rows),
                "total_tokens": total_tokens, "fallback_count": quality["fallback_count"],
                "success_rate": _rate(success, total_calls),
            },
            "latency_buckets": {
                "lt_1s": quality["latency_lt_1s"], "from_1s_to_3s": quality["latency_1s_3s"],
                "from_3s_to_10s": quality["latency_3s_10s"], "gte_10s": quality["latency_gte_10s"],
            },
            "error_categories": [
                {"category": name, "count": quality[f"error_{name}"]}
                for name in ("authentication", "rate_limit", "timeout", "unavailable", "invalid_request", "other")
            ],
            "data_quality": {
                "first_day": min((row["day"] for row in rows), default=None).isoformat() if rows else None,
                "latest_day": latest_data_day.isoformat() if latest_data_day else None,
                "aggregate_rows": len(rows), "active_installations": len(clients),
                "client_versions": len({row["client_version"] for row in rows}),
                "freshness_days": max(
                    0, (datetime.now(timezone.utc).date() - latest_data_day).days
                ) if latest_data_day else None,
                "last_successful_received_at": max(
                    (item["received_at"] for item in filtered_batch_metadata), default=None
                ).isoformat(timespec="seconds") if filtered_batch_metadata else None,
            },
            "schema_coverage": list(schema_groups.values()),
            "methodology": _methodology(),
        }
