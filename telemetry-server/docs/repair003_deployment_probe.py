"""Authorized synthetic deployment probe for REPAIR-003 (no-OS aggregation).

Run via: docker-compose exec -T telemetry-api python -
Uses one unique synthetic identity, verifies new(no-OS)/legacy(OS) batches,
duplicate/conflict/consent paths, DB + admin consistency, then removes only its
own exact synthetic rows. Prints counters/statuses, never secrets or the raw
installation id, and never stores request bodies.
"""
import asyncio
from datetime import datetime, timezone
import http.client
import json
import os
import socket
import ssl
import urllib.error
import urllib.request
import uuid

import asyncpg
from app.repository import installation_hash


def make_row(client_version, with_os):
    row = dict(
        client_version=client_version,
        provider="synthetic",
        model="synthetic-repair003",
        active_minutes=0,
        api_call_count=5,
        success_count=4,
        error_count=1,
        input_tokens=30,
        output_tokens=10,
        total_tokens=40,
        aggregation_day=datetime.now(timezone.utc).date().isoformat(),
        latency_buckets=dict(lt_1s=5, from_1s_to_3s=0, from_3s_to_10s=0, gte_10s=0),
        error_category_counts=dict(authentication=0, rate_limit=0, timeout=0,
                                   unavailable=0, invalid_request=0, other=1),
        fallback_count=0,
    )
    if with_os:
        row["operating_system"] = "windows"
    return row


async def main():
    version = "repair003-probe-20261007"
    synthetic_installation = "installation_" + uuid.uuid4().hex
    digest = installation_hash(os.environ["INSTALLATION_HMAC_SECRET"], synthetic_installation)
    url = os.getenv("CHANNEL_PROBE_URL", "https://gateway:8443/v1/telemetry/batches")
    origin_host = os.environ.get("CHANNEL_ORIGIN_HOST", "metrics.microglow.com.cn")
    context = ssl.create_default_context()
    if url.startswith("https://gateway:"):
        # Local Caddy uses `tls internal`; verification is relaxed for this
        # in-network synthetic check only, never for the public endpoint.
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    have_os_id = "synthetic_repair003_os_" + uuid.uuid4().hex
    no_os_id = "synthetic_repair003_noos_" + uuid.uuid4().hex

    class LocalOriginConnection(http.client.HTTPSConnection):
        def __init__(self, host, **kwargs):
            super().__init__(host, **kwargs)
            if host == "gateway:8443":
                self.host = origin_host
                self._create_connection = lambda address, timeout, source_address=None: socket.create_connection(("gateway", 8443), timeout, source_address)

    class LocalOriginHandler(urllib.request.HTTPSHandler):
        def https_open(self, request):
            return self.do_open(LocalOriginConnection, request, context=self._context)

    handler = LocalOriginHandler(context=context) if url.startswith("https://gateway:") else urllib.request.HTTPSHandler(context=context)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), handler)

    def batch(batch_id, with_os):
        return dict(schema_version=2, batch_id=batch_id, installation_id=synthetic_installation,
                    consent_version=os.environ.get("CONSENT_VERSION_V2", "v2.2026-09"), consent=True,
                    client_version=version, aggregated_rows=[make_row(version, with_os)])

    def post(body):
        headers = {"Content-Type": "application/json"}
        if url.startswith("https://gateway:"):
            headers["Host"] = origin_host + ":8443"
        request = urllib.request.Request(url, json.dumps(body).encode(), headers)
        try:
            with opener.open(request, timeout=20) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, None

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM usage_daily WHERE installation_hash=$1)", digest)
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM telemetry_batches WHERE batch_id=$1)", have_os_id)
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM telemetry_batches WHERE batch_id=$1)", no_os_id)

        status, ack = post(batch(no_os_id, with_os=False))
        assert status == 200 and ack["ack"] is True and ack["duplicate"] is False and ack["accepted_rows"] == 1
        print("NEW_NO_OS_ACK=200 accepted_rows=1")

        status, ack = post(batch(have_os_id, with_os=True))
        assert status == 200 and ack["ack"] is True and ack["duplicate"] is False
        print("LEGACY_OS_ACK=200 accepted_rows=1")

        for name, body in (("NEW_NO_OS", batch(no_os_id, with_os=False)), ("LEGACY_OS", batch(have_os_id, with_os=True))):
            status, ack = post(body)
            assert status == 200 and ack["duplicate"] is True and ack["accepted_rows"] == 0
        print("REPEAT_ACK=200 duplicate=true")

        conflict = batch(no_os_id, with_os=False)
        conflict["aggregated_rows"][0]["operating_system"] = "windows"
        assert post(conflict)[0] == 409
        print("CONFLICT_SAME_ID_DIFF_CONTENT=409")

        declined = batch("synthetic_repair003_decline_" + uuid.uuid4().hex, with_os=False)
        declined["consent"] = False
        assert post(declined)[0] == 422
        print("CONSENT_FALSE=422")

        records = await conn.fetch(
            "SELECT operating_system, api_call_count, total_tokens FROM usage_daily WHERE installation_hash=$1 ORDER BY operating_system",
            digest,
        )
        assert len(records) == 2, records
        os_values = {r["operating_system"] for r in records}
        assert os_values == {"", "windows"}, os_values
        assert sum(r["api_call_count"] for r in records) == 10
        assert sum(r["total_tokens"] for r in records) == 80
        print("DB=2_rows os_in={blank,windows} calls=10 tokens=80")

        request = urllib.request.Request("http://telemetry-admin:8001/admin/usage/summary",
                                         headers={"Authorization": "Bearer " + os.environ["ADMIN_TOKEN"]})
        with opener.open(request, timeout=20) as response:
            summary = json.load(response)
        subset = [r for r in summary["by_relay_version_model"] if r["client_version"] == version]
        assert sum(r["api_call_count"] for r in subset) == 10, subset
        assert sum(r["total_tokens"] for r in subset) == 80, subset
        print("ADMIN=200 calls=10 tokens=80")

        # No other batches may reference this synthetic identity before cleanup.
        other = await conn.fetchval("SELECT COUNT(*) FROM telemetry_batches WHERE installation_hash=$1", digest)
        assert other == 2, other
    finally:
        async with conn.transaction():
            removed_rows = await conn.execute(
                "DELETE FROM usage_daily WHERE installation_hash=$1 AND provider='synthetic' AND model='synthetic-repair003' AND client_version=$2",
                digest, version,
            )
            removed_batches = await conn.execute(
                "DELETE FROM telemetry_batches WHERE batch_id IN ($1,$2) AND installation_hash=$3",
                have_os_id, no_os_id, digest,
            )
            assert removed_rows == "DELETE 2", removed_rows
            assert removed_batches == "DELETE 2", removed_batches
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM usage_daily WHERE installation_hash=$1)", digest)
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM telemetry_batches WHERE batch_id IN ($1,$2))", have_os_id, no_os_id)
        await conn.close()
        print("SYNTHETIC_CLEANUP=PASS exact_rows=2 exact_batches=2")


asyncio.run(main())
