from __future__ import annotations

from datetime import datetime, timezone
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from server import Gateway  # noqa: E402
from storage import Settings  # noqa: E402
from telemetry import (  # noqa: E402
    CONSENT_VERSION_V2, TelemetryAggregator, TelemetryBatchStore,
    TelemetryConsent, TelemetryRuntime, UploadResponse,
    classify_call_channel, load_official_hosts,
)
from telemetry.store import DAILY_AGGREGATES_DDL, TelemetryDatabase  # noqa: E402


class ChannelClassifierTests(unittest.TestCase):
    def test_official_hosts_from_shipped_manifest(self):
        hosts = load_official_hosts()
        self.assertIsNotNone(hosts)
        self.assertEqual(len(hosts), 8)
        for host in hosts:
            with self.subTest(host=host):
                self.assertEqual(classify_call_channel(f"https://{host}/v1/responses"), "official")

    def test_path_port_case_and_spoofing(self):
        self.assertEqual(classify_call_channel("HTTPS://API.OPENAI.COM:443/elsewhere"), "official")
        for url in (
            "https://api.openai.com.evil.example/v1/responses",
            "https://not-api.openai.com/v1/responses",
            "https://relay.example/api.openai.com/v1/responses",
            "https://例子.example/v1/responses",
            "http://127.0.0.1:11434/v1/chat/completions",
        ):
            with self.subTest(url=url):
                self.assertEqual(classify_call_channel(url), "relay")
        self.assertEqual(classify_call_channel("https://api.openai.com@relay.example/v1/responses"), "unknown")

    def test_invalid_url_or_unavailable_manifest_is_unknown(self):
        for url in (None, "", "api.openai.com", "https://", "https://api.openai.com:bad/x", "ftp://api.openai.com"):
            with self.subTest(url=url):
                self.assertEqual(classify_call_channel(url), "unknown")
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(load_official_hosts(Path(directory) / "missing.json"))
        self.assertEqual(classify_call_channel("https://relay.example/v1", hosts=frozenset()), "relay")
        with patch("telemetry.channel.load_official_hosts", return_value=None):
            self.assertEqual(classify_call_channel("https://relay.example/v1"), "unknown")


class ChannelAggregateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="microglow-channel-")
        self.directory = Path(self.temporary.name)
        self.consent = TelemetryConsent(self.directory)
        self.database = TelemetryDatabase(self.directory)
        self.aggregator = TelemetryAggregator(self.database, self.consent)
        self.batches = TelemetryBatchStore(self.database, self.consent)

    def tearDown(self):
        self.temporary.cleanup()

    def record(self, channel, **changes):
        value = dict(
            client_version="3.32", operating_system="windows", provider="deepseek",
            model="deepseek-flash", successful=True, input_tokens=10, output_tokens=2,
            active_minutes=1, occurred_at=datetime(2026, 10, 3, tzinfo=timezone.utc),
            call_channel=channel,
        )
        value.update(changes)
        return self.aggregator.record_request(**value)

    def test_same_model_separate_channels_without_new_counts_or_minutes(self):
        self.consent.grant(2, CONSENT_VERSION_V2)
        self.assertTrue(self.record("official"))
        self.assertTrue(self.record("relay", successful=False, input_tokens=5, output_tokens=0,
                                    active_minutes=0, error_category="timeout"))
        payload = self.batches.create_pending(2)["payload"]
        rows = payload["aggregated_rows"]
        self.assertEqual({row["call_channel"] for row in rows}, {"official", "relay"})
        self.assertEqual(sum(row["api_call_count"] for row in rows), 2)
        self.assertEqual(sum(row["success_count"] for row in rows), 1)
        self.assertEqual(sum(row["error_count"] for row in rows), 1)
        self.assertEqual(sum(row["input_tokens"] for row in rows), 15)
        self.assertEqual(sum(row["output_tokens"] for row in rows), 2)
        self.assertEqual(sum(row["active_minutes"] for row in rows), 1)
        serialized = json.dumps(payload)
        self.assertNotIn("api.deepseek.com", serialized)
        self.assertNotIn("relay.example", serialized)
        self.assertNotIn("base_url", serialized)
        self.assertNotIn("url", serialized.lower())

    def test_consent_failure_and_retry_preserve_new_batch_without_upload(self):
        calls = []

        class Client:
            def upload(self, payload):
                calls.append(payload)
                return UploadResponse(status_code=422, body={})

        runtime = TelemetryRuntime(self.directory, "3.32", uploader=Client())
        self.assertFalse(runtime.record_request(provider="deepseek", model="deepseek-flash", status=200,
                                                elapsed_seconds=1, call_channel="official"))
        self.assertEqual(runtime.flush(), 0)
        self.assertEqual(calls, [])
        self.consent.grant(2, CONSENT_VERSION_V2)
        self.record("official")
        batch = self.batches.create_pending(2)
        batch_id = batch["payload"]["batch_id"]
        self.assertEqual(runtime.flush(), 0)
        self.assertEqual(calls, [])
        self.assertEqual(self.batches.read(batch_id)["payload"], batch["payload"])
        self.assertEqual(self.batches.read(batch_id)["state"], "pending")

    def test_existing_legacy_batch_can_retry_unchanged(self):
        self.consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
        self.record("unknown")
        batch = self.batches.create_pending(2)
        legacy = json.loads(json.dumps(batch["payload"]))
        for row in legacy["aggregated_rows"]:
            del row["call_channel"]
        with self.database.connect() as connection:
            connection.execute("UPDATE batches SET payload_json=? WHERE batch_id=?",
                               (json.dumps(legacy), legacy["batch_id"]))
        captured = []

        class Client:
            def upload(self, payload):
                captured.append(payload)
                return UploadResponse(status_code=202, body={"ack": True, "batch_id": payload["batch_id"]})

        runtime = TelemetryRuntime(self.directory, "3.32", uploader=Client())
        self.assertEqual(runtime.upload_pending(), 1)
        self.assertEqual(captured, [legacy])
        self.assertEqual(self.batches.read(legacy["batch_id"])["state"], "acknowledged")

    def test_gateway_uses_actual_url_not_provider_or_model_name(self):
        seen = []

        class Runtime:
            def enabled(self):
                return True

            def record_request(self, **event):
                seen.append(event)

        gateway = object.__new__(Gateway)
        gateway.telemetry = Runtime()
        gateway.record_telemetry({"provider_name": "OpenAI", "model": "gpt-test",
                                  "base_url": "https://relay.example/v1/responses"},
                                 status=200, elapsed_seconds=1)
        self.assertEqual(seen[0]["call_channel"], "relay")


class LegacyMigrationTests(unittest.TestCase):
    def test_existing_aggregate_becomes_unknown_with_backup(self):
        with tempfile.TemporaryDirectory(prefix="microglow-channel-migration-") as directory:
            path = Path(directory) / "telemetry-v2.sqlite3"
            old_ddl = DAILY_AGGREGATES_DDL.replace(
                "call_channel TEXT NOT NULL DEFAULT 'unknown',", ""
            ).replace("aggregation_day, call_channel)", "aggregation_day)")
            with closing(sqlite3.connect(path)) as connection:
                with connection:
                    connection.execute(old_ddl.format(table="daily_aggregates"))
                    connection.execute(
                        "INSERT INTO daily_aggregates "
                        "(schema_version, client_version, operating_system, provider, model_type, model_value, "
                        "aggregation_day, active_minutes, api_call_count, success_count, input_tokens, output_tokens) "
                        "VALUES (2, '3.31', 'windows', 'openai', 'model', 'gpt-test', '2026-10-03', 2, 1, 1, 10, 2)"
                    )
                    connection.execute(
                        "CREATE TABLE batches (batch_id TEXT PRIMARY KEY, state TEXT NOT NULL, "
                        "payload_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
                    )
                    connection.execute(
                        "INSERT INTO batches VALUES (?, 'pending', ?, '2026-10-03', '2026-10-03')",
                        ("batch_legacy_1234567890", '{"batch_id":"batch_legacy_1234567890"}'),
                    )
            database = TelemetryDatabase(Path(directory))
            with database.connect() as connection:
                row = connection.execute("SELECT * FROM daily_aggregates").fetchone()
            self.assertEqual(row["call_channel"], "unknown")
            self.assertEqual(row["active_minutes"], 2)
            self.assertEqual(row["api_call_count"], 1)
            with database.connect() as connection:
                stored_batch = connection.execute("SELECT payload_json FROM batches").fetchone()[0]
            self.assertEqual(stored_batch, '{"batch_id":"batch_legacy_1234567890"}')
            self.assertTrue((Path(directory) / "telemetry-v2.pre-channel.sqlite3").is_file())


class ShutdownTests(unittest.TestCase):
    def test_service_stop_does_not_upload_and_repeated_exit_uploads_once(self):
        with tempfile.TemporaryDirectory(prefix="microglow-exit-once-") as directory:
            gateway = Gateway(Settings(Path(directory)))
            runtime = Mock()
            gateway.telemetry = runtime
            gateway.start(0)
            gateway.stop()
            runtime.flush.assert_not_called()
            gateway.shutdown()
            gateway.shutdown()
            gateway.stop()
            runtime.flush.assert_called_once_with()

    def test_failed_legacy_batch_waits_for_next_exit_without_changing_id(self):
        with tempfile.TemporaryDirectory(prefix="microglow-exit-retry-") as directory:
            settings = Settings(Path(directory))
            gateway = Gateway(settings)
            gateway.telemetry.consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
            payload = {"schema_version": 2, "batch_id": "batch_exit_only_fixture",
                       "aggregated_rows": [{"provider": "openai"}]}
            with gateway.telemetry.database.connect() as connection:
                connection.execute("INSERT INTO batches VALUES (?, 'pending', ?, 'now', 'now')",
                                   (payload["batch_id"], json.dumps(payload)))
            uploaded = []
            class Client:
                def upload(self, value):
                    uploaded.append(value)
                    return UploadResponse(failure_kind="timeout")
            gateway.telemetry.uploader = Client()
            gateway.stop()
            self.assertEqual(uploaded, [])
            gateway.shutdown()
            gateway.shutdown()
            self.assertEqual(uploaded, [payload])
            self.assertEqual(gateway.telemetry.batches.read(payload["batch_id"])["state"], "pending")
            next_run = Gateway(settings)
            class AckClient:
                def upload(self, value):
                    uploaded.append(value)
                    return UploadResponse(status_code=202, body={"ack": True, "batch_id": value["batch_id"]})
            next_run.telemetry.uploader = AckClient()
            self.assertEqual(uploaded, [payload])
            next_run.shutdown()
            self.assertEqual(uploaded, [payload, payload])
            self.assertEqual(next_run.telemetry.batches.read(payload["batch_id"])["state"], "acknowledged")

    def test_unconsented_exit_and_telemetry_error_do_not_upload_or_break_exit(self):
        with tempfile.TemporaryDirectory(prefix="microglow-exit-consent-") as directory:
            gateway = Gateway(Settings(Path(directory)))
            client = Mock()
            gateway.telemetry.uploader = client
            gateway.shutdown()
            client.upload.assert_not_called()
            another = Gateway(Settings(Path(directory) / "another"))
            another.telemetry = Mock(flush=Mock(side_effect=OSError("synthetic failure")))
            another.shutdown()
            another.shutdown()
            another.telemetry.flush.assert_called_once_with()

    def test_held_channel_batch_does_not_block_gateway_shutdown(self):
        with tempfile.TemporaryDirectory(prefix="microglow-channel-shutdown-") as directory:
            settings = Settings(Path(directory))
            gateway = Gateway(settings)
            gateway.telemetry.set_consent(True)
            uploads = []

            class Client:
                def upload(self, payload):
                    uploads.append(payload)
                    return UploadResponse(status_code=422, body={})

            gateway.telemetry.uploader = Client()
            gateway.start(0)
            try:
                gateway.record_telemetry(
                    {"provider_name": "OpenAI", "model": "gpt-test",
                     "base_url": "https://api.openai.com/v1/responses"},
                    status=200, elapsed_seconds=0.1,
                )
            finally:
                gateway.shutdown()
            self.assertFalse(gateway.running)
            self.assertEqual(uploads, [])
            pending = gateway.telemetry.batches.list_retryable()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["payload"]["aggregated_rows"][0]["call_channel"], "official")


if __name__ == "__main__":
    unittest.main()
