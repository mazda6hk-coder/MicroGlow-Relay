from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.main import create_admin_app, create_public_app
from app.repository import MemoryRepository, collapsed_rows
from app.schemas import TelemetryBatch


SECRET = "test-hmac-secret-that-is-longer-than-32-characters"
ADMIN_TOKEN = "test-admin-token-that-is-longer-than-32-characters"
ROOT = Path(__file__).resolve().parents[1]


def settings(**overrides) -> Settings:
    values = {
        "database_url": "postgresql://telemetry:test@localhost/telemetry",
        "installation_hmac_secret": SECRET,
        "admin_token": ADMIN_TOKEN,
        "max_body_bytes": 1_048_576,
        "max_rows": 500,
        "public_rate_limit_per_minute": 100,
        "admin_rate_limit_per_minute": 100,
    }
    values.update(overrides)
    return Settings(**values)


class Client:
    def __init__(self, app):
        self.app = app
        self.client = None
        self.lifespan = None

    async def __aenter__(self):
        self.lifespan = self.app.router.lifespan_context(self.app)
        await self.lifespan.__aenter__()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="https://testserver"
        )
        return self.client

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()
        await self.lifespan.__aexit__(exc_type, exc, tb)


@pytest.mark.asyncio
async def test_health_returns_status_only():
    app = create_public_app(settings(), MemoryRepository(SECRET))
    async with Client(app) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_accepts_batch_and_duplicate_is_not_counted_twice(valid_batch):
    repository = MemoryRepository(SECRET)
    app = create_public_app(settings(), repository)
    async with Client(app) as client:
        first = await client.post("/v1/telemetry/batches", json=valid_batch)
        duplicate = await client.post("/v1/telemetry/batches", json=valid_batch)

    assert first.status_code == 200
    assert first.json() == {
        "ack": True,
        "batch_id": valid_batch["batch_id"],
        "duplicate": False,
        "accepted_rows": 1,
    }
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["accepted_rows"] == 0
    assert len(repository.rows) == 1
    assert repository.rows[0]["api_call_count"] == 10


@pytest.mark.asyncio
async def test_reused_batch_id_with_different_payload_conflicts(valid_batch):
    repository = MemoryRepository(SECRET)
    app = create_public_app(settings(), repository)
    changed = deepcopy(valid_batch)
    changed["aggregated_rows"][0]["active_minutes"] = 21
    async with Client(app) as client:
        assert (await client.post("/v1/telemetry/batches", json=valid_batch)).status_code == 200
        response = await client.post("/v1/telemetry/batches", json=changed)
    assert response.status_code == 409
    assert response.json() == {"detail": "batch_id_conflict"}


@pytest.mark.asyncio
@pytest.mark.parametrize("consent", [False, None])
async def test_consent_must_be_explicitly_true(valid_batch, consent):
    payload = deepcopy(valid_batch)
    if consent is None:
        payload.pop("consent")
    else:
        payload["consent"] = consent
    app = create_public_app(settings(), MemoryRepository(SECRET))
    async with Client(app) as client:
        response = await client.post("/v1/telemetry/batches", json=payload)
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"


@pytest.mark.asyncio
@pytest.mark.parametrize("forbidden", [
    {"api_key": "secret"},
    {"authorization": "Bearer secret"},
    {"ip_address": "203.0.113.42"},
    {"prompt": "private"},
    {"response": "private"},
    {"email": "person@example.test"},
])
async def test_unlisted_or_sensitive_fields_are_rejected_without_echo(valid_batch, forbidden):
    payload = deepcopy(valid_batch)
    payload["aggregated_rows"][0].update(forbidden)
    app = create_public_app(settings(), MemoryRepository(SECRET))
    async with Client(app) as client:
        response = await client.post("/v1/telemetry/batches", json=payload)
    assert response.status_code == 422
    serialized = response.text
    assert "secret" not in serialized
    assert "private" not in serialized
    assert "person@example.test" not in serialized


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("country_code", "USA"),
    ("active_minutes", -1),
    ("api_call_count", 11),
    ("total_tokens", 1499),
])
async def test_invalid_ranges_and_inconsistent_totals_are_rejected(valid_batch, field, value):
    payload = deepcopy(valid_batch)
    payload["aggregated_rows"][0][field] = value
    app = create_public_app(settings(), MemoryRepository(SECRET))
    async with Client(app) as client:
        response = await client.post("/v1/telemetry/batches", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_client_calendar_day_may_be_one_day_ahead_of_server(valid_batch):
    payload = deepcopy(valid_batch)
    payload["aggregated_rows"][0]["aggregation_day"] = (
        datetime.now(timezone.utc).date() + timedelta(days=1)
    ).isoformat()
    app = create_public_app(settings(), MemoryRepository(SECRET))
    async with Client(app) as client:
        response = await client.post("/v1/telemetry/batches", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_configured_row_limit_is_enforced(valid_batch):
    payload = deepcopy(valid_batch)
    second = deepcopy(payload["aggregated_rows"][0])
    second["provider"] = "anthropic"
    payload["aggregated_rows"].append(second)
    app = create_public_app(settings(max_rows=1), MemoryRepository(SECRET))
    async with Client(app) as client:
        response = await client.post("/v1/telemetry/batches", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_request_body_limit_is_enforced(valid_batch):
    app = create_public_app(settings(max_body_bytes=64), MemoryRepository(SECRET))
    async with Client(app) as client:
        response = await client.post("/v1/telemetry/batches", json=valid_batch)
    assert response.status_code == 413
    assert response.json() == {"error": "request_too_large"}


@pytest.mark.asyncio
async def test_admin_summary_requires_independent_token(valid_batch):
    repository = MemoryRepository(SECRET)
    public = create_public_app(settings(), repository)
    admin = create_admin_app(settings(), repository)
    async with Client(public) as client:
        await client.post("/v1/telemetry/batches", json=valid_batch)
    async with Client(admin) as client:
        missing = await client.get("/admin/usage/summary")
        installation = await client.get(
            "/admin/usage/summary",
            headers={"Authorization": f"Bearer {valid_batch['installation_id']}"},
        )
        allowed = await client.get(
            "/admin/usage/summary",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert missing.status_code == 401
    assert installation.status_code == 401
    assert allowed.status_code == 200
    summary = allowed.json()
    assert summary["by_country"][0]["country_code"] is None
    assert summary["by_country"][0]["country_source"] == "COUNTRY-SOURCE-GAP"
    assert summary["outcomes"]["success"] == 8
    assert summary["outcomes"]["error"] == 2
    assert summary["outcomes"]["total"] == 10
    assert summary["outcomes"]["success_rate"] == 0.8
    assert summary["outcomes"]["total_tokens"] == 1500


@pytest.mark.asyncio
async def test_schema_v2_accepts_only_consented_quality_aggregates(valid_batch):
    payload = deepcopy(valid_batch)
    payload["schema_version"] = 2
    payload["consent_version"] = "v2.2026-09"
    payload["aggregated_rows"][0].update({
        "latency_buckets": {
            "lt_1s": 5, "from_1s_to_3s": 3, "from_3s_to_10s": 1, "gte_10s": 1,
        },
        "error_category_counts": {
            "authentication": 0, "rate_limit": 1, "timeout": 1,
            "unavailable": 0, "invalid_request": 0, "other": 0,
        },
        "fallback_count": 2,
    })
    repository = MemoryRepository(SECRET)
    public = create_public_app(settings(), repository)
    admin = create_admin_app(settings(), repository)
    async with Client(public) as client:
        accepted = await client.post("/v1/telemetry/batches", json=payload)
    async with Client(admin) as client:
        summary = await client.get(
            "/admin/usage/summary", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
        )
    assert accepted.status_code == 200
    assert summary.json()["latency_buckets"]["lt_1s"] == 5
    assert summary.json()["error_categories"][1] == {"category": "rate_limit", "count": 1}
    assert summary.json()["outcomes"]["fallback_count"] == 2


@pytest.mark.asyncio
async def test_v1_rejects_quality_fields_and_v2_requires_new_consent(valid_batch):
    payload = deepcopy(valid_batch)
    payload["aggregated_rows"][0]["fallback_count"] = 1
    app = create_public_app(settings(), MemoryRepository(SECRET))
    async with Client(app) as client:
        old_schema = await client.post("/v1/telemetry/batches", json=payload)
        payload["schema_version"] = 2
        old_consent = await client.post("/v1/telemetry/batches", json=payload)
    assert old_schema.status_code == 422
    assert old_consent.status_code == 422


@pytest.mark.asyncio
async def test_consent_versions_are_exact_allowlisted_and_rejection_writes_nothing(valid_batch):
    repository = MemoryRepository(SECRET)
    app = create_public_app(settings(), repository)
    disguised_v1 = deepcopy(valid_batch)
    disguised_v1["consent_version"] = "2026-09-new"
    disguised_v2 = deepcopy(valid_batch)
    disguised_v2["schema_version"] = 2
    disguised_v2["consent_version"] = "v2.legacy"
    disguised_v2["aggregated_rows"][0].update({
        "latency_buckets": {"lt_1s": 10, "from_1s_to_3s": 0, "from_3s_to_10s": 0, "gte_10s": 0},
        "error_category_counts": {
            "authentication": 0, "rate_limit": 0, "timeout": 0,
            "unavailable": 0, "invalid_request": 0, "other": 2,
        },
        "fallback_count": 0,
    })
    async with Client(app) as client:
        first = await client.post("/v1/telemetry/batches", json=disguised_v1)
        second = await client.post("/v1/telemetry/batches", json=disguised_v2)
    assert first.status_code == 422
    assert second.status_code == 422
    assert first.json()["detail"] == "consent_version_not_accepted"
    assert repository.rows == []
    assert repository.batches == {}


@pytest.mark.asyncio
async def test_admin_date_filter_and_invalid_range(valid_batch):
    repository = MemoryRepository(SECRET)
    public = create_public_app(settings(), repository)
    admin = create_admin_app(settings(), repository)
    older = deepcopy(valid_batch)
    older["batch_id"] = "batch_older_0123456789"
    older["aggregated_rows"][0]["aggregation_day"] = (date.today() - timedelta(days=10)).isoformat()
    async with Client(public) as client:
        await client.post("/v1/telemetry/batches", json=valid_batch)
        await client.post("/v1/telemetry/batches", json=older)
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    async with Client(admin) as client:
        filtered = await client.get(
            f"/admin/usage/summary?from_day={date.today().isoformat()}&to_day={date.today().isoformat()}",
            headers=headers,
        )
        invalid = await client.get(
            f"/admin/usage/summary?from_day={date.today().isoformat()}&to_day={(date.today() - timedelta(days=1)).isoformat()}",
            headers=headers,
        )
    assert filtered.status_code == 200
    assert filtered.json()["outcomes"]["total"] == 10
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_relay_version_model_ranking_merges_providers_and_respects_dates(valid_batch):
    repository = MemoryRepository(SECRET)
    base = collapsed_rows(TelemetryBatch.model_validate(valid_batch))[0]
    today = datetime.now(timezone.utc).date()
    for version, provider, calls, day in (
        ("3.32", "custom", 10, today),
        ("3.32", "ai", 20, today),
        ("3.31", "custom", 30, today),
        ("3.32", "custom", 100, today - timedelta(days=1)),
    ):
        repository.rows.append({
            **base, "client_version": version, "provider": provider,
            "model": "shared-model", "model_type": "model", "day": day,
            "installation_hash": "ranking-test", "api_call_count": calls,
            "success_count": calls, "error_count": 0,
            "input_tokens": calls * 6, "output_tokens": calls * 4,
            "total_tokens": calls * 10,
        })
    summary = await repository.usage_summary(from_day=today, to_day=today)
    ranking = summary["by_relay_version_model"]
    assert len(ranking) == 2
    assert {item["client_version"] for item in ranking} == {"3.31", "3.32"}
    for item in ranking:
        assert item["api_call_count"] == 30
        assert item["total_tokens"] == 300
        assert item["call_share"] == 0.5
        assert item["token_share"] == 0.5
    assert sum(item["api_call_count"] for item in ranking) == summary["outcomes"]["total"]
    trends = summary["relay_version_model_trends"]
    assert len(trends) == 2
    assert {item["client_version"] for item in trends} == {"3.31", "3.32"}
    assert all(item["api_call_count"] == 30 and item["total_tokens"] == 300 for item in trends)
    assert all(item["period"] == today.replace(day=1).isoformat() for item in trends)


@pytest.mark.asyncio
async def test_retention_growth_and_usage_percentiles_are_derived_from_daily_rows(valid_batch):
    repository = MemoryRepository(SECRET)
    first = deepcopy(valid_batch)
    first["batch_id"] = "batch_retention_first_0001"
    first["installation_id"] = "installation_retention_first_0001"
    first_row = first["aggregated_rows"][0]
    first_row["aggregation_day"] = (date.today() - timedelta(days=40)).isoformat()
    day_7 = deepcopy(first_row)
    day_7["aggregation_day"] = (date.today() - timedelta(days=33)).isoformat()
    day_30 = deepcopy(first_row)
    day_30["aggregation_day"] = (date.today() - timedelta(days=10)).isoformat()
    first["aggregated_rows"] = [first_row, day_7, day_30]

    second = deepcopy(valid_batch)
    second["batch_id"] = "batch_retention_second_0002"
    second["installation_id"] = "installation_retention_second_0002"
    second["aggregated_rows"][0]["aggregation_day"] = (date.today() - timedelta(days=40)).isoformat()

    await repository.insert_batch(TelemetryBatch.model_validate(first))
    await repository.insert_batch(TelemetryBatch.model_validate(second))
    summary = await repository.usage_summary()

    assert summary["retention"]["eligible_7"] == 2
    assert summary["retention"]["retained_7"] == 1
    assert summary["retention"]["day_7_rate"] == 0.5
    assert summary["retention"]["eligible_30"] == 2
    assert summary["retention"]["retained_30"] == 1
    assert summary["usage_distribution"]["calls_p50"] == 20
    assert summary["usage_distribution"]["calls_p90"] is None
    assert summary["usage_distribution"]["sample_size"] == 2
    assert summary["periods"]["daily"][0]["new_installations"] == 2


@pytest.mark.asyncio
async def test_rolling_active_installations_use_utc_as_of_day(valid_batch):
    repository = MemoryRepository(SECRET)
    base = collapsed_rows(TelemetryBatch.model_validate(valid_batch))[0]
    as_of = datetime.now(timezone.utc).date()
    for index, offset in enumerate((0, 6, 7, 29, 30)):
        repository.rows.append({
            **base,
            "day": as_of - timedelta(days=offset),
            "installation_hash": f"installation-hash-{index}",
        })
    summary = await repository.usage_summary(to_day=as_of)
    assert summary["timezone"] == "UTC"
    assert summary["activity"]["as_of_day"] == as_of.isoformat()
    assert summary["activity"]["dau"] == 1
    assert summary["activity"]["wau"] == 2
    assert summary["activity"]["mau"] == 4


@pytest.mark.asyncio
async def test_retention_is_exact_day_and_unavailable_is_null(valid_batch):
    base = collapsed_rows(TelemetryBatch.model_validate(valid_batch))[0]
    today_utc = datetime.now(timezone.utc).date()
    insufficient = MemoryRepository(SECRET)
    insufficient.rows.append({**base, "day": today_utc, "installation_hash": "new-install"})
    insufficient_summary = await insufficient.usage_summary()
    assert insufficient_summary["retention"]["day_7_rate"] is None
    assert insufficient_summary["retention"]["day_30_rate"] is None

    exact = MemoryRepository(SECRET)
    exact.rows.extend([
        {**base, "day": today_utc - timedelta(days=10), "installation_hash": "day-eight-only"},
        {**base, "day": today_utc - timedelta(days=2), "installation_hash": "day-eight-only"},
    ])
    exact_summary = await exact.usage_summary()
    assert exact_summary["retention"]["eligible_7"] == 1
    assert exact_summary["retention"]["retained_7"] == 0
    assert exact_summary["retention"]["day_7_rate"] == 0.0


@pytest.mark.asyncio
async def test_installation_averages_and_percentile_sample_thresholds(valid_batch):
    repository = MemoryRepository(SECRET)
    base = collapsed_rows(TelemetryBatch.model_validate(valid_batch))[0]
    for index in range(10):
        calls = index + 1
        repository.rows.append({
            **base,
            "installation_hash": f"distribution-{index}",
            "api_call_count": calls,
            "success_count": calls,
            "error_count": 0,
            "input_tokens": calls * 10,
            "output_tokens": calls * 5,
            "total_tokens": calls * 15,
            "active_minutes": calls * 2,
        })
    summary = await repository.usage_summary()
    distribution = summary["usage_distribution"]
    assert distribution["sample_size"] == 10
    assert distribution["avg_calls"] == 5.5
    assert distribution["avg_tokens"] == 82.5
    assert distribution["avg_active_minutes"] == 11
    assert distribution["calls_p50"] == 5.5
    assert distribution["calls_p90"] is not None
    assert distribution["calls_p99"] is None


@pytest.mark.asyncio
async def test_admin_dashboard_is_safe_shell_and_data_api_remains_protected():
    admin = create_admin_app(settings(), MemoryRepository(SECRET))
    async with Client(admin) as client:
        page = await client.get("/admin/")
        logo = await client.get("/admin/assets/microglow-logo.png")
        protected = await client.get("/admin/usage/summary")

    assert page.status_code == 200
    assert "MicroGlow Relay 匿名遥测决策中心" in page.text
    assert "MicroGlow 公司 Logo" in page.text
    assert "隐私优先的数据分析" in page.text
    assert "用户使用概览" in page.text
    assert ".span-12 { grid-column: span 12; }" in page.text
    assert "日活跃安装" in page.text
    assert "7 日活跃安装" in page.text
    assert "30 日活跃安装" in page.text
    assert "<span>DAU</span>" not in page.text
    assert "<span>WAU</span>" not in page.text
    assert "<span>MAU</span>" not in page.text
    assert "Privacy-first analytics" not in page.text
    assert logo.status_code == 200
    assert logo.headers["content-type"] == "image/png"
    assert len(logo.content) > 100_000
    assert "ADMIN_TOKEN" in page.text
    assert "活跃客户端" not in page.text
    assert "活跃安装" in page.text
    assert "包含成功和失败请求" in page.text
    assert "样本不足" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in page.headers["content-security-policy"]
    assert page.headers["x-frame-options"] == "DENY"
    assert protected.status_code == 401


def test_admin_dashboard_does_not_persist_token_in_browser_storage():
    dashboard = (ROOT / "app" / "admin.html").read_text(encoding="utf-8")
    script = dashboard.split("<script>", 1)[1].split("</script>", 1)[0]
    assert "localStorage" not in script
    assert "sessionStorage" not in script
    assert "document.cookie" not in script
    assert 'window.location.protocol === "file:"' in script
    assert "请勿直接双击 admin.html" in dashboard
    assert 'data-range-days="1"' in dashboard
    assert 'data-range-days="7"' in dashboard
    assert 'data-range-days="30"' in dashboard
    assert 'data-range-days="90"' in dashboard
    assert 'data-range-days="365"' in dashboard
    assert "setUTCDate" in dashboard
    assert "latestDataDay" in dashboard
    assert "applyQuickRange" in dashboard
    # Quick ranges must recompute their anchor instead of latching onto the
    # previous end-date input value, otherwise they freeze on the first day set.
    assert '$("toDay").value ||' not in script
    assert "数据截止" in script
    for export_metadata in (
        "generated_at", "timezone", "schema_and_consent", "api_call_total",
        "retention_day_7", "retention_day_30",
    ):
        assert export_metadata in script
    assert "state.data.filters.from_day" in script
    assert "window.print()" in script


@pytest.mark.asyncio
async def test_rate_limit_uses_sanitized_client_bucket(valid_batch):
    app = create_public_app(
        settings(public_rate_limit_per_minute=1), MemoryRepository(SECRET)
    )
    async with Client(app) as client:
        first = await client.post("/v1/telemetry/batches", json=valid_batch)
        second = await client.post("/v1/telemetry/batches", json=valid_batch)
    assert first.status_code == 200
    assert second.status_code == 429


def test_public_and_admin_routes_are_separate():
    repository = MemoryRepository(SECRET)
    public_paths = {route.path for route in create_public_app(settings(), repository).routes}
    admin_paths = {route.path for route in create_admin_app(settings(), repository).routes}
    assert "/admin/usage/summary" not in public_paths
    assert "/v1/telemetry/batches" not in admin_paths
