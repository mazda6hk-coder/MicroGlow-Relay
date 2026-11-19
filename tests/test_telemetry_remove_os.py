# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""No system collection in new batches; sealed legacy retries stay immutable."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_telemetry import event
from telemetry import TelemetryConsent, TelemetryAggregator, TelemetryBatchStore, CONSENT_VERSION_V2, UploadResponse
from telemetry.store import TelemetryDatabase
from telemetry.runtime import TelemetryRuntime


class RemoveOsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="relay-remove-os-")
        self.path = Path(self.temp.name)
        self.consent = TelemetryConsent(self.path)
        self.db = TelemetryDatabase(self.path)
        self.aggregator = TelemetryAggregator(self.db, self.consent)
        self.batches = TelemetryBatchStore(self.db, self.consent)

    def tearDown(self):
        self.temp.cleanup()

    def test_no_os_field_or_os_partition_for_new_records(self):
        self.consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
        for os_name in ("windows", "linux"):
            self.assertTrue(self.aggregator.record_request(**event(operating_system=os_name)))
        with self.db.connect() as connection:
            rows = connection.execute("SELECT * FROM daily_aggregates").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["operating_system"], "")
        batch = self.batches.create_pending()["payload"]
        row = batch["aggregated_rows"][0]
        self.assertNotIn("operating_system", row)
        self.assertEqual(row["api_call_count"], 2)
        self.assertEqual(row["total_tokens"], 28)

    def test_legacy_sealed_batch_retries_without_rewriting(self):
        self.consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
        self.aggregator.record_request(**event())
        item = self.batches.create_pending()
        batch_id = item["payload"]["batch_id"]
        legacy = item["payload"]
        legacy["aggregated_rows"][0]["operating_system"] = "windows"
        encoded = json.dumps(legacy, ensure_ascii=False, sort_keys=True)
        with self.db.connect() as connection:
            connection.execute("UPDATE batches SET payload_json=? WHERE batch_id=?", (encoded, batch_id))
        self.assertFalse(self.batches.apply_upload_response(batch_id, UploadResponse(422, {})))
        self.assertEqual(self.batches.read(batch_id)["payload"], legacy)
        self.assertTrue(self.batches.apply_upload_response(batch_id, UploadResponse(200, {"ack": True, "batch_id": batch_id})))
        with self.db.connect() as connection:
            self.assertEqual(connection.execute("SELECT payload_json FROM batches WHERE batch_id=?", (batch_id,)).fetchone()[0], encoded)

    def test_runtime_does_not_read_platform_and_default_does_not_record(self):
        runtime = TelemetryRuntime(self.path, "3.4")
        with patch("platform.system", side_effect=AssertionError("must not collect OS")):
            self.assertFalse(runtime.record_request(provider="openai", model="test", status=200, elapsed_seconds=1))
            self.consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
            self.assertTrue(runtime.record_request(provider="openai", model="test", status=200, elapsed_seconds=1))
            batch = runtime.checkpoint(timeout=1)["payload"]
        self.assertNotIn("operating_system", batch["aggregated_rows"][0])
