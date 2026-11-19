from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from telemetry import (  # noqa: E402
    CONSENT_VERSION_V1,
    CONSENT_VERSION_V2,
    TelemetryAggregator,
    TelemetryBatchStore,
    TelemetryConsent,
    TelemetryRuntime,
    UploadResponse,
)
from telemetry.store import TelemetryDatabase, utc_day  # noqa: E402
from server import Gateway  # noqa: E402
from storage import Settings  # noqa: E402


def event(**changes):
    value = {
        "client_version": "3.0.0",
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


class TelemetryCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="microglow-telemetry-")
        self.directory = Path(self.temporary.name)
        self.consent = TelemetryConsent(self.directory)
        self.database = TelemetryDatabase(self.directory)
        self.aggregator = TelemetryAggregator(self.database, self.consent)
        self.batches = TelemetryBatchStore(self.database, self.consent)

    def tearDown(self):
        self.temporary.cleanup()

    def grant_v2(self):
        self.consent.grant(2, CONSENT_VERSION_V2)

    def make_batch(self):
        self.grant_v2()
        self.assertTrue(self.aggregator.record_request(**event()))
        batch = self.batches.create_pending(2)
        self.assertIsNotNone(batch)
        return batch


class ConsentTests(TelemetryCase):
    def test_default_is_denied_and_identity_is_stable(self):
        self.assertFalse(self.consent.is_granted(2))
        first = self.consent.installation_id()
        second = TelemetryConsent(self.directory).installation_id()
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("installation_"))

    def test_exact_v1_v2_versions_only(self):
        with self.assertRaises(ValueError):
            self.consent.grant(2, "v2")
        with self.assertRaises(ValueError):
            self.consent.grant(1, CONSENT_VERSION_V2)
        self.consent.grant(1, CONSENT_VERSION_V1)
        self.assertTrue(self.consent.is_granted(1))
        self.assertFalse(self.consent.is_granted(2))
        self.consent.grant(2, CONSENT_VERSION_V2)
        self.assertTrue(self.consent.is_granted(2))

    def test_collection_requires_opt_in_and_stops_after_withdrawal(self):
        self.assertFalse(self.aggregator.record_request(**event()))
        self.grant_v2()
        self.assertTrue(self.aggregator.record_request(**event()))
        batch = self.batches.create_pending(2)
        self.assertEqual(len(self.batches.list_retryable()), 1)
        self.consent.withdraw()
        self.assertFalse(self.aggregator.record_request(**event()))
        self.assertEqual(self.batches.list_retryable(), [])
        self.assertIsNotNone(self.batches.read(batch["payload"]["batch_id"]))


class AggregationTests(TelemetryCase):
    def test_v2_totals_buckets_errors_fallback_and_utc(self):
        self.grant_v2()
        self.aggregator.record_request(**event())
        self.aggregator.record_request(**event(
            successful=False,
            input_tokens=3,
            output_tokens=1,
            elapsed_seconds=4.0,
            error_category="timeout",
            fallback=True,
        ))
        batch = self.batches.create_pending(2)["payload"]
        row = batch["aggregated_rows"][0]
        self.assertEqual(row["success_count"] + row["error_count"], row["api_call_count"])
        self.assertEqual(row["input_tokens"] + row["output_tokens"], row["total_tokens"])
        self.assertEqual(sum(row["latency_buckets"].values()), row["api_call_count"])
        self.assertEqual(sum(row["error_category_counts"].values()), row["error_count"])
        self.assertLessEqual(row["fallback_count"], row["api_call_count"])
        self.assertEqual(row["aggregation_day"], "2026-09-22")
        self.assertNotIn("country_code", row)

    def test_model_and_model_family_are_mutually_exclusive(self):
        self.grant_v2()
        with self.assertRaises(ValueError):
            self.aggregator.record_request(**event(model="one", model_family="family"))
        with self.assertRaises(ValueError):
            self.aggregator.record_request(**event(model=None, model_family=None))
        self.assertTrue(self.aggregator.record_request(**event(model=None, model_family="gpt")))
        row = self.batches.create_pending(2)["payload"]["aggregated_rows"][0]
        self.assertIn("model_family", row)
        self.assertNotIn("model", row)

    def test_utc_day_converts_aware_time_and_rejects_naive_time(self):
        instant = datetime(2026, 9, 22, 0, 30, tzinfo=timezone(timedelta(hours=8)))
        self.assertEqual(utc_day(instant), "2026-09-21")
        with self.assertRaises(ValueError):
            utc_day(datetime(2026, 9, 22, 0, 30))

    def test_v1_payload_has_no_v2_quality_fields(self):
        self.consent.grant(1, CONSENT_VERSION_V1)
        self.assertTrue(self.aggregator.record_request(**event(schema_version=1)))
        payload = self.batches.create_pending(1)["payload"]
        row = payload["aggregated_rows"][0]
        self.assertEqual(payload["schema_version"], 1)
        self.assertNotIn("latency_buckets", row)
        self.assertNotIn("error_category_counts", row)
        self.assertNotIn("fallback_count", row)


class BatchTests(TelemetryCase):
    def test_batch_is_saved_read_and_restored_after_restart(self):
        batch = self.make_batch()
        batch_id = batch["payload"]["batch_id"]
        self.batches.set_state(batch_id, "uploading")
        restarted = TelemetryBatchStore(TelemetryDatabase(self.directory), TelemetryConsent(self.directory))
        restored = restarted.read(batch_id)
        self.assertEqual(restored["state"], "pending")
        self.assertEqual(restored["payload"], batch["payload"])

    def test_batch_ids_are_unique(self):
        first = self.make_batch()["payload"]["batch_id"]
        self.aggregator.record_request(**event(model="another"))
        second = self.batches.create_pending(2)["payload"]["batch_id"]
        self.assertNotEqual(first, second)

    def test_payload_has_only_aggregate_allowlist_and_no_ip(self):
        payload = self.make_batch()["payload"]
        self.assertEqual(set(payload), {
            "schema_version", "batch_id", "installation_id", "consent_version",
            "consent", "client_version", "aggregated_rows",
        })
        forbidden = {
            "prompt", "response", "api_key", "authorization", "file", "code",
            "ip", "ip_address", "raw_error", "error_message", "request_body",
            "response_body", "request_records", "country_code",
        }
        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key.lower()
                    yield from keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from keys(child)
        self.assertTrue(forbidden.isdisjoint(set(keys(payload))))

    def test_every_failure_mode_preserves_retryable_batch_silently(self):
        cases = [
            UploadResponse(failure_kind="network_unavailable"),
            UploadResponse(failure_kind="connection_failed"),
            UploadResponse(failure_kind="timeout"),
            UploadResponse(status_code=503, body={}),
            UploadResponse(status_code=200, body={}),
            UploadResponse(status_code=200, body={"ack": False}),
            UploadResponse(status_code=200, body={"ack": True}),
            UploadResponse(status_code=200, body={"ack": True, "batch_id": "batch_wrong"}),
        ]
        for response in cases:
            batch = self.make_batch()
            batch_id = batch["payload"]["batch_id"]
            self.batches.set_state(batch_id, "uploading")
            self.assertFalse(self.batches.apply_upload_response(batch_id, response))
            stored = self.batches.read(batch_id)
            self.assertIn(stored["state"], {"pending", "rejected"})
            self.assertEqual(stored["payload"], batch["payload"])

    def test_only_matching_success_ack_can_acknowledge(self):
        batch = self.make_batch()
        batch_id = batch["payload"]["batch_id"]
        accepted = UploadResponse(status_code=202, body={"ack": True, "batch_id": batch_id})
        self.assertTrue(self.batches.apply_upload_response(batch_id, accepted))
        self.assertEqual(self.batches.read(batch_id)["state"], "acknowledged")


class IsolationTests(unittest.TestCase):
    def test_storage_failure_falls_back_without_raising(self):
        with tempfile.TemporaryDirectory() as directory:
            blocked = Path(directory) / "not-a-directory"
            blocked.write_text("occupied", encoding="utf-8")
            runtime = TelemetryRuntime.create_isolated(blocked, "3.0.0")
            self.assertFalse(runtime.enabled())
            self.assertFalse(runtime.record_request(
                provider="openai", model="gpt-test", status=200, elapsed_seconds=0.1
            ))
            self.assertIsNone(runtime.checkpoint())

    def test_denied_or_failed_telemetry_does_not_block_router_start(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consent = TelemetryConsent(root / "telemetry")
            self.assertFalse(consent.is_granted(2))
            blocked = root / "blocked"
            blocked.write_text("occupied", encoding="utf-8")
            self.assertFalse(TelemetryRuntime.create_isolated(blocked, "3.0.0").enabled())

            gateway = Gateway(Settings(root / "router"))
            try:
                gateway.start(0)
                self.assertTrue(gateway.running)
            finally:
                gateway.stop()


if __name__ == "__main__":
    unittest.main()
