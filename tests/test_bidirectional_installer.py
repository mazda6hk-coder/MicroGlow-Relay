"""Installer consent contract and runtime consumption, using isolated data only."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from telemetry.consent import TelemetryConsent

ROOT = Path(__file__).resolve().parents[1]

class InstallerConsentTests(unittest.TestCase):
    def test_no_preselection_single_choice_and_silent_never_grants(self):
        source = (ROOT / "installer/MicroGlowRelay.iss").read_text(encoding="utf-8")
        self.assertIn("CreateInputOptionPage(wpLicense", source)
        self.assertIn("StatisticsPage.Values[0] := False", source)
        self.assertIn("StatisticsPage.Values[1] := False", source)
        self.assertIn("ConsentChoice := -1", source)
        self.assertIn("ConsentChoice := StatisticsPage.SelectedValueIndex", source)
        self.assertIn("WizardForm.NextButton.Enabled := StatisticsPage.SelectedValueIndex >= 0", source)
        self.assertNotIn("StatisticsConfirmed", source)
        self.assertNotIn("MsgBox", source)
        self.assertIn("同意加入（推荐）", source)
        self.assertIn("请给我们一点光，让 Relay 越来越好用", source)
        self.assertNotIn("Fields:", source)
        self.assertNotIn("TNewMemo", source)
        self.assertIn("PrivacyButton.OnClick := @ViewPrivacyPolicy", source)
        self.assertIn("ExtractTemporaryFile('PRIVACY-POLICY.md')", source)
        self.assertIn("SaveStatisticsConsent(ConsentPath, (not WizardSilent) and (ConsentChoice = 0))", source)
        self.assertIn("WizardSilent and FileExists(ConsentPath) then Exit", source)
        helper = (ROOT / "installer/TelemetryConsent.iss").read_text(encoding="utf-8")
        self.assertIn(".before-installer-", helper)
        self.assertIn("SetupIconFile=..\\assets\\app.ico", source)

    def test_installer_payload_yes_and_no_match_runtime(self):
        source = (ROOT / "installer/TelemetryConsent.iss").read_text(encoding="utf-8")
        expression = re.search(r"Payload := (.*);", source).group(1)
        for choice in (False, True):
            replacements = {"ConsentValue": "true" if choice else "false",
                            "Disclosure": '"channel-exit-upload-2026-10"' if choice else "null"}
            parts = expression.split(" + ")
            payload = "".join(part[1:-1] if part.startswith("'") else replacements[part]
                              for part in parts)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                (path / "telemetry-consent.json").write_text(payload, encoding="utf-8")
                consent = TelemetryConsent(path)
                self.assertEqual(consent.is_granted(), choice)
                self.assertEqual(consent.upload_is_granted(), choice)
                self.assertNotIn("os", json.loads(payload))
