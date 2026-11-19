# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
from pathlib import Path

import asyncpg
import pytest

from app.repository import BatchConflict, PostgresRepository, installation_hash
from app.geoip import COUNTRY_SOURCE_GAP, GEOIP_SOURCE
from app.schemas import TelemetryBatch


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


@pytest.mark.asyncio
async def test_postgres_migration_idempotency_and_period_summaries(valid_batch):
    connection = await asyncpg.connect(TEST_DATABASE_URL)
    try:
        for migration_path in sorted(Path("migrations").glob("*.sql")):
            await connection.execute(migration_path.read_text(encoding="utf-8"))
        await connection.execute("TRUNCATE usage_daily, telemetry_batches")
        columns = await connection.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name IN ('usage_daily', 'telemetry_batches')"
        )
        assert not {"ip_address", "client_ip", "source_ip", "remote_addr"} & {
            row["column_name"] for row in columns
        }
    finally:
        await connection.close()

    repository = await PostgresRepository.connect(TEST_DATABASE_URL, "i" * 32)
    try:
        batch = TelemetryBatch.model_validate(valid_batch)
        first = await repository.insert_batch(batch, "US", GEOIP_SOURCE)
        duplicate = await repository.insert_batch(batch, "US", GEOIP_SOURCE)
        assert first.duplicate is False
        assert duplicate.duplicate is True

        changed = batch.model_copy(deep=True)
        changed.aggregated_rows[0].active_minutes += 1
        with pytest.raises(BatchConflict):
            await repository.insert_batch(changed, "US", GEOIP_SOURCE)

        v2_payload = dict(valid_batch)
        v2_payload["batch_id"] = "batch_v2_0123456789abcdef"
        v2_payload["installation_id"] = "installation_v2_0123456789abcdef"
        v2_payload["schema_version"] = 2
        v2_payload["consent_version"] = "v2.2026-09"
        v2_payload["aggregated_rows"] = [dict(valid_batch["aggregated_rows"][0])]
        v2_payload["aggregated_rows"][0].update({
            "latency_buckets": {
                "lt_1s": 5, "from_1s_to_3s": 3, "from_3s_to_10s": 1, "gte_10s": 1,
            },
            "error_category_counts": {
                "authentication": 0, "rate_limit": 1, "timeout": 1,
                "unavailable": 0, "invalid_request": 0, "other": 0,
            },
            "fallback_count": 2,
        })
        await repository.insert_batch(TelemetryBatch.model_validate(v2_payload), "US", GEOIP_SOURCE)

        summary = await repository.usage_summary()
        assert summary["periods"]["daily"][0]["api_call_count"] == 20
        assert summary["periods"]["weekly"][0]["total_tokens"] == 3000
        assert summary["periods"]["monthly"][0]["active_installations"] == 2
        assert summary["active_installations"] == 2
        assert summary["latency_buckets"]["lt_1s"] == 5
        assert summary["error_categories"][1]["count"] == 1
        assert summary["usage_distribution"]["calls_p90"] is None
        assert summary["usage_distribution"]["sample_size"] == 2
        assert summary["timezone"] == "UTC"
        assert summary["activity"]["dau"] == 2
        assert summary["activity"]["wau"] == 2
        assert summary["activity"]["mau"] == 2
        assert summary["retention"]["day_7_rate"] is None
        assert summary["data_quality"]["last_successful_received_at"]
        assert summary["methodology"]["api_call_total"].startswith("includes successful and failed")
        assert summary["by_country"][0]["country_code"] == "US"
        assert summary["by_country"][0]["country_source"] == GEOIP_SOURCE

        gap_payload = dict(valid_batch)
        gap_payload["batch_id"] = "batch_gap_0123456789abcdef"
        gap_payload["installation_id"] = "installation_gap_0123456789abcdef"
        await repository.insert_batch(
            TelemetryBatch.model_validate(gap_payload), None, COUNTRY_SOURCE_GAP
        )

        connection = await asyncpg.connect(TEST_DATABASE_URL)
        try:
            gap_row = await connection.fetchrow(
                """
                SELECT country_code, country_source
                FROM usage_daily
                WHERE installation_hash = $1
                """,
                installation_hash("i" * 32, gap_payload["installation_id"]),
            )
            assert gap_row["country_code"] is None
            assert gap_row["country_source"] == COUNTRY_SOURCE_GAP

            with pytest.raises(asyncpg.CheckViolationError):
                await connection.execute(
                    "UPDATE usage_daily SET country_code = 'ZZ', country_source = 'GEOIP'"
                )
            with pytest.raises(asyncpg.CheckViolationError):
                await connection.execute(
                    "UPDATE usage_daily SET country_code = NULL, country_source = 'GEOIP'"
                )
            with pytest.raises(asyncpg.CheckViolationError):
                await connection.execute(
                    "UPDATE usage_daily SET country_code = 'US', country_source = 'COUNTRY-SOURCE-GAP'"
                )
            with pytest.raises(asyncpg.PostgresError):
                await connection.execute(
                    "UPDATE usage_daily SET country_code = 'COUNTRY-SOURCE-GAP'"
                )
        finally:
            await connection.close()
    finally:
        await repository.close()
