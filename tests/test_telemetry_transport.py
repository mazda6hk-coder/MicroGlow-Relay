# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""生产入口硬编码、HTTP 传输与运行时接线（全离线）。"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from urllib import error


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from telemetry import (  # noqa: E402
    CONSENT_VERSION_V2,
    TELEMETRY_ENDPOINT_URL,
    TELEMETRY_HOST,
    TELEMETRY_PATH,
    HttpTelemetryUploadClient,
    TelemetryAggregator,
    TelemetryBatchStore,
    TelemetryConsent,
    TelemetryRuntime,
    client_version,
    model_dimension,
    provider_key,
)
from telemetry.store import TelemetryDatabase  # noqa: E402


def event(**changes):
    """与 test_telemetry.event 等价的最小事件夹具（本地内联，避免跨模块导入）。"""
    value = {
        "client_version": "3.2",
        "operating_system": "windows",
        "provider": "openai",
        "model": "gpt-test",
        "successful": True,
        "input_tokens": 10,
        "output_tokens": 4,
        "elapsed_seconds": 0.5,
        "error_category": None,
        "fallback": False,
        "occurred_at": datetime(2026, 9, 22, 0, 30, tzinfo=timezone.utc),
    }
    value.update(changes)
    return value


class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = json.dumps(body).encode("utf-8")

    def read(self, size=-1):
        return self._body

    def close(self):
        # ``urllib.error.HTTPError`` wraps ``fp`` in a temporary file on 3.13,
        # which closes the wrapper on GC; a real response is always closable.
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class EndpointTests(unittest.TestCase):
    def test_production_endpoint_is_hardcoded_once(self):
        self.assertEqual(TELEMETRY_HOST, "metrics.microglow.com.cn")
        self.assertEqual(TELEMETRY_PATH, "/v1/telemetry/batches")
        self.assertEqual(TELEMETRY_ENDPOINT_URL, "https://metrics.microglow.com.cn/v1/telemetry/batches")


class TransportTests(unittest.TestCase):
    def test_successful_upload_sends_allow_listed_payload_only(self):
        captured = {}

        def opener(http_request, timeout):
            captured["url"] = http_request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(http_request.header_items())
            captured["payload"] = json.loads(http_request.data.decode("utf-8"))
            return _FakeResponse(202, {"ack": True, "batch_id": "batch_fixture"})

        client = HttpTelemetryUploadClient("3.2", opener=opener)
        response = client.upload({"schema_version": 2, "batch_id": "batch_fixture"})

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.body, {"ack": True, "batch_id": "batch_fixture"})
        self.assertIsNone(response.failure_kind)
        self.assertEqual(captured["url"], TELEMETRY_ENDPOINT_URL)
        self.assertEqual(captured["payload"], {"schema_version": 2, "batch_id": "batch_fixture"})
        self.assertIn("MicroGlow-Relay/3.2", captured["headers"].get("User-agent", ""))

    def test_http_error_keeps_status_and_body_without_raising(self):
        def opener(http_request, timeout):
            raise error.HTTPError(
                TELEMETRY_ENDPOINT_URL, 422, "unprocessable", {},
                _FakeResponse(422, {"error": "invalid_request"}),
            )

        response = HttpTelemetryUploadClient(opener=opener).upload({"batch_id": "batch_x"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.body, {"error": "invalid_request"})
        self.assertIsNone(response.failure_kind)

    def test_timeout_and_connection_failures_are_classified_silently(self):
        def timeout_opener(http_request, timeout):
            raise error.URLError(socket.timeout("timed out"))

        def offline_opener(http_request, timeout):
            raise error.URLError(OSError("no route to host"))

        def broken_opener(http_request, timeout):
            raise RuntimeError("boom")

        self.assertEqual(HttpTelemetryUploadClient(opener=timeout_opener).upload({}).failure_kind, "timeout")
        self.assertEqual(HttpTelemetryUploadClient(opener=offline_opener).upload({}).failure_kind, "network_unavailable")
        self.assertEqual(HttpTelemetryUploadClient(opener=broken_opener).upload({}).failure_kind, "connection_failed")

    def test_non_json_success_body_is_not_treated_as_ack(self):
        class _Raw:
            status = 200

            def read(self, size=-1):
                return b"<html>not json</html>"

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        response = HttpTelemetryUploadClient(opener=lambda request, timeout: _Raw()).upload({})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.body)


    def test_unsupported_fields_are_not_sent_or_rewritten_under_existing_batch_id(self):
        captured = {}
        payload = {
            "schema_version": 2,
            "batch_id": "batch_fixture",
            "aggregated_rows": [{"provider": "zhipu", "api_call_count": 1}],
        }

        def opener(http_request, timeout):
            captured["payload"] = json.loads(http_request.data.decode("utf-8"))
            return _FakeResponse(202, {"ack": True, "batch_id": "batch_fixture"})

        HttpTelemetryUploadClient("3.2", opener=opener).upload(payload)
        self.assertNotIn("country_code", captured["payload"]["aggregated_rows"][0])
        self.assertNotIn("country_code", payload["aggregated_rows"][0])

        for field, value in (("country_code", "DE"),):
            payload["aggregated_rows"][0][field] = value
            captured.clear()
            response = HttpTelemetryUploadClient("3.2", opener=opener).upload(payload)
            self.assertEqual(response.failure_kind, "schema_not_supported")
            self.assertEqual(captured, {})
            self.assertEqual(payload["aggregated_rows"][0][field], value)
            del payload["aggregated_rows"][0][field]


class WiringTests(unittest.TestCase):
    def test_provider_keys_are_allow_listed(self):
        expected = {
            "OpenAI": "openai",
            "DeepSeek": "deepseek",
            "Anthropic": "anthropic",
            "智谱 AI": "zhipu",
            "Moonshot AI": "moonshot",
            "硅基流动": "siliconflow",
            "Ollama（本机）": "ollama",
            "自定义 / 中转服务": "custom",
            "": "custom",
        }
        for name, token in expected.items():
            self.assertEqual(provider_key(name), token, name)

    def test_model_dimension_keeps_exactly_one_side(self):
        self.assertEqual(model_dimension("gpt-5", "OpenAI"), ("gpt-5", None))
        self.assertEqual(model_dimension("", "智谱 AI"), (None, "zhipu"))
        self.assertEqual(model_dimension(None, None), (None, "custom"))

    def test_client_version_falls_back_to_safe_token(self):
        self.assertEqual(client_version("3.2"), "3.2")
        self.assertEqual(client_version(""), "0.0.0")
        self.assertEqual(client_version("3.2 (内部)"), "0.0.0")


class UploadRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="microglow-telemetry-upload-")
        self.directory = Path(self.temporary.name)
        self.consent = TelemetryConsent(self.directory)
        self.database = TelemetryDatabase(self.directory)
        self.aggregator = TelemetryAggregator(self.database, self.consent)
        self.batches = TelemetryBatchStore(self.database, self.consent)

    def tearDown(self):
        self.temporary.cleanup()

    def _make_batch(self):
        self.consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
        self.assertTrue(self.aggregator.record_request(**event()))
        return self.batches.create_pending(2)

    def test_new_channel_batch_uploads_after_explicit_confirmation(self):
        batch = self._make_batch()
        seen = []

        class _Client:
            def upload(self, payload):
                seen.append(payload["batch_id"])
                from telemetry import UploadResponse
                return UploadResponse(status_code=202, body={"ack": True, "batch_id": payload["batch_id"]})

        runtime = TelemetryRuntime(self.directory, "3.2", uploader=_Client())
        self.assertEqual(runtime.upload_pending(), 1)
        self.assertEqual(seen, [batch["payload"]["batch_id"]])
        self.assertEqual(self.batches.read(batch["payload"]["batch_id"])["state"], "acknowledged")

    def test_failed_upload_keeps_batch_retryable(self):
        batch = self._make_batch()
        batch_id = batch["payload"]["batch_id"]

        class _Client:
            def upload(self, payload):
                from telemetry import UploadResponse
                return UploadResponse(failure_kind="timeout")

        runtime = TelemetryRuntime(self.directory, "3.2", uploader=_Client())
        self.assertEqual(runtime.upload_pending(), 0)
        self.assertEqual(self.batches.read(batch_id)["state"], "pending")
        self.assertEqual(len(self.batches.list_retryable()), 1)

    def test_crashing_uploader_never_raises_or_loses_the_batch(self):
        batch = self._make_batch()
        batch_id = batch["payload"]["batch_id"]

        class _Client:
            def upload(self, payload):
                raise RuntimeError("transport exploded")

        runtime = TelemetryRuntime(self.directory, "3.2", uploader=_Client())
        self.assertEqual(runtime.upload_pending(), 0)
        self.assertEqual(self.batches.read(batch_id)["state"], "pending")

    def test_upload_is_skipped_without_consent(self):
        batch = self._make_batch()
        self.consent.withdraw()

        called = []

        class _Client:
            def upload(self, payload):
                called.append(payload)
                from telemetry import UploadResponse
                return UploadResponse(status_code=202, body={"ack": True, "batch_id": payload["batch_id"]})

        runtime = TelemetryRuntime(self.directory, "3.2", uploader=_Client())
        self.assertEqual(runtime.upload_pending(), 0)
        self.assertEqual(called, [])
        self.assertEqual(self.batches.read(batch["payload"]["batch_id"])["state"], "pending")
