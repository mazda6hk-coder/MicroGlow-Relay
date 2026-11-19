"""Explicitly authorized synthetic deployment probe; never run as a scheduler.

Run through telemetry-api stdin. Uses only a fresh synthetic identity, cleans
only its exact hash/batch, and prints counters/statuses rather than secrets.
"""
import asyncio
from datetime import datetime, timezone
import json
import os
import ssl
import socket
import http.client
import uuid
import urllib.request
import urllib.error

import asyncpg
from app.repository import installation_hash


async def main():
    marker = "channel_probe_" + uuid.uuid4().hex
    synthetic_installation = "installation_" + uuid.uuid4().hex
    digest = installation_hash(os.environ["INSTALLATION_HMAC_SECRET"], synthetic_installation)
    url = os.getenv("CHANNEL_PROBE_URL", "https://gateway:8443/v1/telemetry/batches")
    origin_host = os.environ.get("CHANNEL_ORIGIN_HOST", "metrics.microglow.com.cn")
    context = ssl.create_default_context()
    if url.startswith("https://gateway:"):
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # local Caddy's internal certificate only
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
    row = dict(client_version="channel-probe-20261007", operating_system="other", provider="synthetic",
               model="synthetic-channel", api_call_count=10, success_count=8, error_count=2,
               input_tokens=1000, output_tokens=500, total_tokens=1500,
               aggregation_day=datetime.now(timezone.utc).date().isoformat(),
               latency_buckets=dict(lt_1s=10, from_1s_to_3s=0, from_3s_to_10s=0, gte_10s=0),
               error_category_counts=dict(authentication=0, rate_limit=0, timeout=0, unavailable=0, invalid_request=0, other=2), fallback_count=0)
    payload = dict(schema_version=2, batch_id=marker, installation_id=synthetic_installation,
                   consent_version=os.environ.get("CONSENT_VERSION_V2", "v2.2026-09"), consent=True,
                   client_version=row["client_version"], aggregated_rows=[dict(row, call_channel=c, active_minutes=20 if i == 0 else 0)
                   for i, c in enumerate(("official", "relay", "unknown"))])
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM usage_daily WHERE installation_hash=$1)", digest)
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM telemetry_batches WHERE batch_id=$1)", marker)
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
        status, ack = post(payload)
        assert status == 200 and ack["ack"] is True and ack["duplicate"] is False and ack["accepted_rows"] == 3
        print("HTTP_ACK=200 accepted_rows=3")
        status, ack = post(payload)
        assert status == 200 and ack["duplicate"] is True
        print("HTTP_RETRY=200 duplicate=true")
        changed = json.loads(json.dumps(payload))
        changed["aggregated_rows"][0]["call_channel"] = "relay"
        assert post(changed)[0] == 409
        print("HTTP_CONFLICT=409")
        records = await conn.fetch("SELECT call_channel,api_call_count,total_tokens,active_minutes FROM usage_daily WHERE installation_hash=$1", digest)
        assert {r["call_channel"] for r in records} == {"official", "relay", "unknown"}
        assert sum(r["api_call_count"] for r in records) == 30
        assert sum(r["total_tokens"] for r in records) == 4500
        assert sum(r["active_minutes"] for r in records) == 20
        print("DB=3_channels calls=30 tokens=4500 minutes=20")
        request = urllib.request.Request("http://telemetry-admin:8001/admin/usage/summary", headers={"Authorization": "Bearer " + os.environ["ADMIN_TOKEN"]})
        with opener.open(request, timeout=20) as response:
            summary = json.load(response)
        subset = [r for r in summary["by_relay_version_model_channel"] if r["client_version"] == row["client_version"]]
        assert {r["call_channel"] for r in subset} == {"official", "relay", "unknown"}
        assert sum(r["api_call_count"] for r in subset) == 30
        print("ADMIN=200 channel_summary=PASS")
    finally:
        async with conn.transaction():
            await conn.execute("DELETE FROM usage_daily WHERE installation_hash=$1 AND client_version=$2 AND provider='synthetic' AND model='synthetic-channel'", digest, row["client_version"])
            await conn.execute("DELETE FROM telemetry_batches WHERE batch_id=$1 AND installation_hash=$2", marker, digest)
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM usage_daily WHERE installation_hash=$1)", digest)
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM telemetry_batches WHERE batch_id=$1)", marker)
        await conn.close()
        print("SYNTHETIC_CLEANUP=PASS")


asyncio.run(main())
