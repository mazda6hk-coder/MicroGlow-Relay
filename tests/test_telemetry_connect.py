"""CONNECT-001: local disclosure gate and immutable channel batch transport."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from telemetry import CONSENT_VERSION_V2, TelemetryRuntime, UploadResponse, HttpTelemetryUploadClient


class ConnectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="relay-connect-")
        self.seen = []
        self.response = UploadResponse(failure_kind="timeout")
        owner = self

        class Client:
            def upload(self, payload):
                owner.seen.append(json.loads(json.dumps(payload)))
                return owner.response

        self.runtime = TelemetryRuntime(Path(self.temp.name), "3.4", uploader=Client())

    def tearDown(self):
        self.temp.cleanup()

    def make_batch(self):
        for channel in ("official", "relay", "unknown"):
            self.assertTrue(self.runtime.record_request(
                provider="openai", model="synthetic-connect-model", status=200,
                elapsed_seconds=0.1, input_tokens=7, output_tokens=2, call_channel=channel))
        batch = self.runtime.checkpoint(timeout=1)
        self.assertIsNotNone(batch)
        return batch["payload"]

    def test_old_local_consent_never_silently_enables_upload(self):
        consent = self.runtime.consent
        consent.grant(2, CONSENT_VERSION_V2)
        payload = self.make_batch()
        self.assertTrue(self.runtime.enabled())
        self.assertFalse(consent.upload_is_granted())
        self.assertEqual(self.runtime.upload_pending(), 0)
        self.assertEqual(self.seen, [])
        self.assertEqual(self.runtime.batches.read(payload["batch_id"])["payload"], payload)

    def test_reconfirm_retry_rejection_wrong_ack_and_valid_ack_preserve_payload(self):
        consent = self.runtime.consent
        consent.grant(2, CONSENT_VERSION_V2)
        payload = self.make_batch()
        consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
        self.assertEqual(self.runtime.upload_pending(), 0)
        self.assertEqual(self.runtime.batches.read(payload["batch_id"])["state"], "pending")
        for response in (UploadResponse(status_code=422, body={}),
                         UploadResponse(status_code=202, body={"ack": True, "batch_id": "wrong"})):
            self.response = response
            self.assertEqual(self.runtime.upload_pending(), 0)
            self.assertEqual(self.runtime.batches.read(payload["batch_id"])["state"], "rejected")
        consent.withdraw()
        self.assertEqual(self.runtime.upload_pending(), 0)
        self.assertEqual(len(self.seen), 3)
        consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
        self.response = UploadResponse(status_code=202, body={"ack": True, "batch_id": payload["batch_id"]})
        self.assertEqual(self.runtime.upload_pending(), 1)
        self.assertTrue(all(item == payload for item in self.seen))
        self.assertEqual(self.runtime.batches.read(payload["batch_id"])["state"], "acknowledged")
        self.assertEqual(sum(row["api_call_count"] for row in payload["aggregated_rows"]), 3)
        self.assertEqual(sum(row["total_tokens"] for row in payload["aggregated_rows"]), 27)
        self.assertEqual({row["call_channel"] for row in payload["aggregated_rows"]}, {"official", "relay", "unknown"})
        raw = json.dumps(payload).lower()
        for private in ("https://", "api.openai.com", "prompt", "response", "authorization", "api_key"):
            self.assertNotIn(private, raw)

    def test_transport_sends_channel_without_rewriting_batch(self):
        self.runtime.consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
        payload = self.make_batch()
        captured = []

        class Response:
            status = 202
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return json.dumps({"ack": True, "batch_id": payload["batch_id"]}).encode()

        def opener(request, timeout):
            captured.append(json.loads(request.data))
            return Response()

        result = HttpTelemetryUploadClient("3.4", opener=opener).upload(payload)
        self.assertEqual(result.status_code, 202)
        self.assertEqual(captured, [payload])

    def test_upload_consent_read_failure_is_silent_and_preserves_batch(self):
        self.runtime.consent.grant(2, CONSENT_VERSION_V2, allow_upload=True)
        payload = self.make_batch()
        with patch.object(self.runtime.consent, "upload_is_granted", side_effect=OSError("synthetic failure")):
            self.assertEqual(self.runtime.upload_pending(), 0)
        self.assertEqual(self.seen, [])
        self.assertEqual(self.runtime.batches.read(payload["batch_id"])["payload"], payload)


if __name__ == "__main__":
    unittest.main()
