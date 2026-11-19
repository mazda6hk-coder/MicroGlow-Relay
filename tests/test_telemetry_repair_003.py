"""Production Pascal writer output -> settings state -> normal exit upload gate."""
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest

from telemetry import UploadResponse
from telemetry.consent import TelemetryConsent
from storage import Settings
from server import Gateway
from app.bridge import Bridge

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "work/consent-repair-003-probe"


class RepairConsentTests(unittest.TestCase):
    def test_actual_pascal_allow_deny_consumed_by_client_and_exit(self):
        if not (PROBE / "allow/telemetry-consent.json").exists():
            self.skipTest("Run the isolated Inno Pascal persistence probe first")
        for name, allowed in (("allow", True), ("deny", False)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                directory = Path(folder)
                shutil.copy2(PROBE / name / "telemetry-consent.json", directory)
                gateway = Gateway(Settings(directory))
                runtime = gateway.telemetry
                seen = []

                class Uploader:
                    def upload(self, payload):
                        seen.append(payload)
                        return UploadResponse(status_code=200, body={"ack": True, "batch_id": payload["batch_id"]})

                runtime.uploader = Uploader()
                bridge = SimpleNamespace(telemetry_consent=TelemetryConsent(directory))
                self.assertEqual(Bridge.telemetry_enabled(bridge), allowed)
                self.assertEqual(Bridge.telemetry_upload_enabled(bridge), allowed)
                self.assertEqual(runtime.enabled(), allowed)
                self.assertEqual(runtime.record_request(provider="custom", model="synthetic-repair-003", status=200,
                                                       elapsed_seconds=0.2, input_tokens=7, output_tokens=2,
                                                       call_channel="relay"), allowed)
                # Recording/starting never uploads; only normal application shutdown does.
                self.assertEqual(seen, [])
                gateway.shutdown()
                self.assertEqual(len(seen), int(allowed))
                if allowed:
                    row = seen[0]["aggregated_rows"][0]
                    self.assertNotIn("operating_system", row)
                    self.assertEqual(row["total_tokens"], 9)
                    self.assertEqual(runtime.batches.read(seen[0]["batch_id"])["state"], "acknowledged")

    def test_pascal_overwrite_backs_up_old_choice(self):
        directory = PROBE / "change"
        if not directory.exists():
            self.skipTest("Run the isolated Pascal persistence probe first")
        consent = TelemetryConsent(directory)
        self.assertTrue(consent.upload_is_granted())
        backups = list(directory.glob("telemetry-consent.json.before-installer-*.bak"))
        self.assertTrue(backups)
        self.assertTrue(any('"consent":false' in p.read_text() for p in backups))


if __name__ == "__main__":
    unittest.main()
