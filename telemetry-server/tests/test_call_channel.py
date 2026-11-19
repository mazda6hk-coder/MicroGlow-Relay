from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import asyncpg
import pytest
from pydantic import ValidationError

from app.repository import MemoryRepository, PostgresRepository, BatchConflict, payload_hash, collapsed_rows
from app.schemas import TelemetryBatch
from test_api import settings, Client
from app.main import create_public_app


def channels_batch(payload):
    payload = deepcopy(payload)
    payload.update(schema_version=2, consent_version="v2.2026-09")
    base = payload["aggregated_rows"][0]
    base.update(latency_buckets=dict(lt_1s=10, from_1s_to_3s=0, from_3s_to_10s=0, gte_10s=0),
                error_category_counts=dict(authentication=0, rate_limit=0, timeout=0, unavailable=0, invalid_request=0, other=2), fallback_count=0)
    payload["aggregated_rows"] = [dict(base, call_channel=c, active_minutes=20 if i == 0 else 0)
                                  for i, c in enumerate(("official", "relay", "unknown"))]
    return payload


def test_legacy_hash_and_strict_contract(valid_batch):
    batch = TelemetryBatch.model_validate(valid_batch)
    old = batch.model_dump(mode="json")
    for row in old["aggregated_rows"]:
        row.pop("call_channel")
    expected = hashlib.sha256(json.dumps(old, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    assert payload_hash(batch) == expected
    assert collapsed_rows(batch)[0]["call_channel"] == "unknown"
    explicit = deepcopy(valid_batch)
    explicit["aggregated_rows"][0]["call_channel"] = "unknown"
    assert payload_hash(TelemetryBatch.model_validate(explicit)) != expected
    for value in ("Official", "custom", "", None, 1):
        bad = deepcopy(valid_batch)
        bad["aggregated_rows"][0]["call_channel"] = value
        with pytest.raises(ValidationError):
            TelemetryBatch.model_validate(bad)
    for field in ("ip_address", "url", "api_key", "unexpected"):
        bad = deepcopy(valid_batch)
        bad["aggregated_rows"][0][field] = "forbidden"
        with pytest.raises(ValidationError):
            TelemetryBatch.model_validate(bad)


@pytest.mark.asyncio
async def test_channel_ack_consent_and_totals(valid_batch):
    repository = MemoryRepository("test-secret")
    app = create_public_app(settings(), repository)
    payload = channels_batch(valid_batch)
    async with Client(app) as client:
        response = await client.post("/v1/telemetry/batches", json=payload)
        assert response.status_code == 200
        assert response.json()["ack"] is True
        assert (await client.post("/v1/telemetry/batches", json=payload)).json()["duplicate"] is True
        changed = deepcopy(payload)
        changed["aggregated_rows"][0]["call_channel"] = "relay"
        assert (await client.post("/v1/telemetry/batches", json=changed)).status_code == 409
        for consent in (False, None):
            bad = deepcopy(payload)
            if consent is None:
                bad.pop("consent")
            else:
                bad["consent"] = consent
            assert (await client.post("/v1/telemetry/batches", json=bad)).status_code == 422
    summary = await repository.usage_summary()
    grouped = summary["by_relay_version_model_channel"]
    assert {r["call_channel"] for r in grouped} == {"official", "relay", "unknown"}
    assert sum(r["api_call_count"] for r in grouped) == 30
    assert sum(r["total_tokens"] for r in grouped) == 4500
    assert sum(r["active_minutes"] for r in grouped) == 20
    assert summary["active_installations"] == 1
    assert sum(r["api_call_count"] for r in summary["by_relay_version_model"]) == 30


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="isolated PostgreSQL required")
async def test_channel_postgres(valid_batch):
    url = os.environ["TEST_DATABASE_URL"]
    connection = await asyncpg.connect(url)
    try:
        for path in sorted(Path("migrations").glob("*.sql")):
            if path.name < "005":
                await connection.execute(path.read_text(encoding="utf-8"))
        await connection.execute("TRUNCATE usage_daily, telemetry_batches")
    finally:
        await connection.close()
    repo = await PostgresRepository.connect(url, "test-secret")
    try:
        # Insert legacy data using pre-channel SQL and old canonical hash.
        legacy = TelemetryBatch.model_validate(valid_batch)
        conn = await asyncpg.connect(url)
        try:
            await conn.execute("INSERT INTO usage_daily (day,country_code,country_source,operating_system,provider,model,model_type,client_version,installation_hash,active_minutes,api_call_count,success_count,error_count,input_tokens,output_tokens,total_tokens) VALUES (CURRENT_DATE,NULL,'COUNTRY-SOURCE-GAP','windows','legacy','legacy','model','legacy',$1,20,10,8,2,1000,500,1500)", "a" * 64)
            migration = Path("migrations/005_call_channel.sql").read_text(encoding="utf-8")
            await conn.execute(migration)
            await conn.execute(migration)
            assert await conn.fetchval("SELECT call_channel FROM usage_daily WHERE provider='legacy'") == "unknown"
            await conn.execute("TRUNCATE usage_daily, telemetry_batches")
        finally:
            await conn.close()
        assert not (await repo.insert_batch(legacy)).duplicate
        assert (await repo.insert_batch(legacy)).duplicate
        payload = channels_batch(valid_batch)
        payload["batch_id"] = "channel_synthetic_002"
        batch = TelemetryBatch.model_validate(payload)
        assert not (await repo.insert_batch(batch)).duplicate
        assert (await repo.insert_batch(batch)).duplicate
        payload["aggregated_rows"][0]["call_channel"] = "unknown"
        with pytest.raises(BatchConflict):
            await repo.insert_batch(TelemetryBatch.model_validate(payload))
        summary = await repo.usage_summary()
        grouped = summary["by_relay_version_model_channel"]
        assert sum(r["api_call_count"] for r in grouped) == 40
        assert sum(r["total_tokens"] for r in grouped) == 6000
        assert sum(r["active_minutes"] for r in grouped) == 40
        assert {r["call_channel"] for r in grouped} == {"official", "relay", "unknown"}
        conn = await asyncpg.connect(url)
        try:
            for bad in ("invalid", "Official"):
                with pytest.raises(asyncpg.CheckViolationError):
                    await conn.execute("UPDATE usage_daily SET call_channel=$1", bad)
            with pytest.raises(asyncpg.NotNullViolationError):
                await conn.execute("UPDATE usage_daily SET call_channel=NULL")
            for path in sorted(Path("migrations").glob("*.sql")):
                await conn.execute(path.read_text(encoding="utf-8"))
            assert await conn.fetchval("SELECT SUM(api_call_count) FROM usage_daily") == 40
            columns = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='usage_daily'")
            assert not {"installation_id", "ip_address", "url", "client_ip"} & {r["column_name"] for r in columns}
        finally:
            await conn.close()
        future = await repo.usage_summary(from_day=batch.aggregated_rows[0].aggregation_day.replace(year=2099))
        assert future["by_relay_version_model_channel"] == []
    finally:
        await repo.close()
