from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import logging
from pathlib import Path

from fastapi import Request
import pytest

from app.geoip import (
    COUNTRY_SOURCE_GAP,
    GEOIP_SOURCE,
    CountryResolution,
    GeoIPCountryResolver,
)
from app.geoip_update import LICENSE_NAME, SOURCE_PAGE, update_database
from app.main import create_admin_app, create_public_app
from app.network import TrustedSourceAddress
from app.repository import MemoryRepository, collapsed_rows
from app.schemas import TelemetryBatch
from tests.test_api import ADMIN_TOKEN, Client, SECRET, settings


def request(peer: str | None, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/v1/telemetry/batches",
        "headers": headers or [],
        "client": (peer, 12345) if peer else None,
    })


def test_source_address_direct_and_trusted_proxy_chain():
    resolver = TrustedSourceAddress(("172.30.0.0/24",))
    assert resolver.resolve(request("8.8.8.8")) == "8.8.8.8"
    proxied = request("172.30.0.2", [(b"x-forwarded-for", b"8.8.8.8")])
    assert resolver.resolve(proxied) == "8.8.8.8"
    # The trusted proxy appends the actual source after any client-supplied value.
    appended = request("172.30.0.2", [(b"x-forwarded-for", b"1.1.1.1, 8.8.8.8")])
    assert resolver.resolve(appended) == "8.8.8.8"


def test_untrusted_or_invalid_forwarded_header_is_not_trusted():
    resolver = TrustedSourceAddress(("172.30.0.0/24",))
    forged = request("203.0.113.8", [(b"x-forwarded-for", b"8.8.8.8")])
    assert resolver.resolve(forged) == "203.0.113.8"
    invalid = request("172.30.0.2", [(b"x-forwarded-for", b"not-an-address")])
    assert resolver.resolve(invalid) is None
    assert resolver.resolve(request(None)) is None


def test_missing_database_and_lookup_exception_return_gap_without_ip_log(tmp_path, caplog):
    resolver = GeoIPCountryResolver(tmp_path / "missing.mmdb")
    assert resolver.lookup("8.8.8.8").country_source == COUNTRY_SOURCE_GAP

    class BrokenReader:
        def get(self, _address):
            raise RuntimeError("lookup failed for 8.8.8.8")

    resolver._ensure_reader = lambda: BrokenReader()  # type: ignore[method-assign]
    with caplog.at_level(logging.WARNING):
        result = resolver.lookup("8.8.8.8")
    assert result == CountryResolution(None, COUNTRY_SOURCE_GAP)
    assert "8.8.8.8" not in caplog.text


class FakeResponse:
    def __init__(self, payload: bytes, headers: dict[str, str] | None = None):
        self.stream = io.BytesIO(payload)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size: int) -> bytes:
        return self.stream.read(size)


def test_official_updater_downloads_validates_and_records_checksums(tmp_path):
    mmdb = b"synthetic-valid-country-mmdb"
    archive = gzip.compress(mmdb)
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)
    calls = []

    def opener(req, timeout):
        calls.append((req.full_url, timeout))
        return FakeResponse(archive, {
            "Last-Modified": "Tue, 01 Sep 2026 06:27:01 GMT",
            "ETag": '"official-etag"',
        })

    def validator(path: Path):
        assert path.read_bytes() == mmdb
        return {"database_type": "DBIP-Country-Lite", "build_epoch": 1788244021, "ip_version": 6}

    metadata = update_database(tmp_path, now=now, opener=opener, validator=validator)
    assert calls == [("https://download.db-ip.com/free/dbip-country-lite-2026-09.mmdb.gz", 60)]
    assert (tmp_path / "dbip-country-lite.mmdb").read_bytes() == mmdb
    assert metadata["source_page"] == SOURCE_PAGE
    assert metadata["license"] == LICENSE_NAME
    assert metadata["release_date"] == "2026-09-01"
    assert metadata["compressed_sha256"] == hashlib.sha256(archive).hexdigest()
    assert metadata["mmdb_sha256"] == hashlib.sha256(mmdb).hexdigest()
    recorded = json.loads((tmp_path / "dbip-country-lite.metadata.json").read_text("utf-8"))
    assert recorded["http_etag"] == '"official-etag"'


def test_failed_update_preserves_old_database(tmp_path):
    target = tmp_path / "dbip-country-lite.mmdb"
    target.write_bytes(b"known-good-old-mmdb")
    archive = gzip.compress(b"untrusted-new-mmdb")

    with pytest.raises(ValueError, match="checksum mismatch"):
        update_database(
            tmp_path,
            now=datetime(2026, 9, 22, tzinfo=timezone.utc),
            expected_compressed_sha256="0" * 64,
            opener=lambda *_args, **_kwargs: FakeResponse(archive),
            validator=lambda _path: {"database_type": "DBIP-Country-Lite"},
        )
    assert target.read_bytes() == b"known-good-old-mmdb"
    assert not list(tmp_path.glob("*.part"))


class StaticGeoIP:
    def __init__(self, country_code: str | None, country_source: str):
        self.result = CountryResolution(country_code, country_source)
        self.seen: list[str | None] = []

    def lookup(self, source_address: str | None) -> CountryResolution:
        self.seen.append(source_address)
        return self.result


@pytest.mark.asyncio
async def test_server_country_overrides_forged_client_country(valid_batch):
    repository = MemoryRepository(SECRET)
    geoip = StaticGeoIP("US", GEOIP_SOURCE)
    payload = deepcopy(valid_batch)
    payload["aggregated_rows"][0]["country_code"] = "CN"
    app = create_public_app(settings(), repository, geoip)  # type: ignore[arg-type]
    async with Client(app) as client:
        response = await client.post("/v1/telemetry/batches", json=payload)
    assert response.status_code == 200
    assert geoip.seen == ["127.0.0.1"]
    assert repository.rows[0]["country_code"] == "US"
    assert repository.rows[0]["country_source"] == GEOIP_SOURCE
    assert "127.0.0.1" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "resolution",
    [CountryResolution("US", GEOIP_SOURCE), CountryResolution(None, COUNTRY_SOURCE_GAP)],
)
async def test_schema_v2_accepts_no_client_country_and_uses_server_resolution(valid_batch, resolution):
    repository = MemoryRepository(SECRET)
    geoip = StaticGeoIP(resolution.country_code, resolution.country_source)
    payload = deepcopy(valid_batch)
    payload["schema_version"] = 2
    payload["consent_version"] = "v2.2026-09"
    row = payload["aggregated_rows"][0]
    row.pop("country_code")
    row.update({
        "latency_buckets": {"lt_1s": 10, "from_1s_to_3s": 0, "from_3s_to_10s": 0, "gte_10s": 0},
        "error_category_counts": {"authentication": 0, "rate_limit": 0, "timeout": 0,
                                  "unavailable": 0, "invalid_request": 0, "other": 2},
        "fallback_count": 0,
    })
    app = create_public_app(settings(), repository, geoip)  # type: ignore[arg-type]
    async with Client(app) as client:
        response = await client.post("/v1/telemetry/batches", json=payload)
    assert response.status_code == 200
    assert response.json()["ack"] is True
    assert repository.rows[0]["country_code"] == resolution.country_code
    assert repository.rows[0]["country_source"] == resolution.country_source


@pytest.mark.asyncio
async def test_gap_is_null_and_admin_response_contains_no_full_ip(valid_batch):
    repository = MemoryRepository(SECRET)
    geoip = StaticGeoIP(None, COUNTRY_SOURCE_GAP)
    public = create_public_app(settings(), repository, geoip)  # type: ignore[arg-type]
    admin = create_admin_app(settings(), repository)
    async with Client(public) as client:
        accepted = await client.post("/v1/telemetry/batches", json=valid_batch)
    async with Client(admin) as client:
        summary = await client.get(
            "/admin/usage/summary",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert accepted.status_code == 200
    country = summary.json()["by_country"][0]
    assert country["country_code"] is None
    assert country["country_source"] == COUNTRY_SOURCE_GAP
    assert "127.0.0.1" not in summary.text


def test_no_ip_storage_columns_and_no_wildcard_proxy_trust():
    root = Path(__file__).resolve().parents[1]
    migrations = "\n".join(path.read_text("utf-8") for path in sorted((root / "migrations").glob("*.sql")))
    compose = (root / "docker-compose.yml").read_text("utf-8")
    dockerfile = (root / "Dockerfile").read_text("utf-8")
    for forbidden in ("ip_address", "client_ip", "source_ip", "remote_addr"):
        assert forbidden not in migrations.lower()
    assert "--forwarded-allow-ips" not in compose
    assert "--forwarded-allow-ips" not in dockerfile
    assert "--no-access-log" in compose


def test_repository_accepts_only_iso_geoip_or_null_gap(valid_batch):
    batch = TelemetryBatch.model_validate(valid_batch)
    assert collapsed_rows(batch, "US", GEOIP_SOURCE)[0]["country_code"] == "US"
    assert collapsed_rows(batch, None, COUNTRY_SOURCE_GAP)[0]["country_code"] is None
    with pytest.raises(ValueError, match="country provenance"):
        collapsed_rows(batch, "ZZ", GEOIP_SOURCE)
    with pytest.raises(ValueError, match="country provenance"):
        collapsed_rows(batch, "US", COUNTRY_SOURCE_GAP)
