# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Release documents are offline, accessible and contain no test credentials."""
from pathlib import Path
from unittest.mock import patch
from test_ui3 import UiTestCase

from storage import VERSION
from PySide6.QtWidgets import QTextBrowser, QPushButton

ROOT = Path(__file__).resolve().parents[1]


class AboutReleaseTests(UiTestCase):
    def test_documents_open_without_external_application(self):
        page = self.shell.pages["settings"]
        for filename in ("USER-GUIDE.md", "USER-AGREEMENT.md", "PRIVACY-POLICY.md", "THIRD-PARTY-NOTICES.md"):
            page.open_document(filename, filename)
            self._process()
            browser = page.document_dialog.findChild(QTextBrowser)
            self.assertTrue(browser.toPlainText().strip())
            self.assertTrue(page.document_dialog.isVisible())
            page.document_dialog.close()

    def test_about_has_real_actions_and_team(self):
        page = self.shell.pages["settings"]
        buttons = page.about_card.findChildren(QPushButton)
        for caption in ("问题反馈", "隐私政策", "用户协议", "第三方许可"):
            matching = [b for b in buttons if b.text() == caption]
            self.assertEqual(len(matching), 1)
            self.assertTrue(matching[0].isEnabled())
        from PySide6.QtWidgets import QLabel
        text = " ".join(w.text() for w in page.about_card.findChildren(QLabel))
        # 关于卡改版后品牌行由 BrandMark + 富文本拼成，旧的“ChatGPT · Codex”
        # 副标题不再随卡展示；产品名与团队署名仍需可见。
        self.assertIn("Relay", text)
        self.assertIn("郑州微光智能科技中心", text)
        with patch("PySide6.QtGui.QDesktopServices.openUrl") as open_url:
            page.open_feedback()
            self.assertEqual(open_url.call_args.args[0].toString(), "mailto:support@microglow.com.cn")

    def test_agreement_date_and_packaging(self):
        agreement = (ROOT / "docs/USER-AGREEMENT.md").read_text(encoding="utf-8")
        self.assertIn("2026年10月7日", agreement)
        for number in range(1, 17):
            self.assertIn(f"## {number}. ", agreement)
        spec = (ROOT / f"MicroGlow-Relay-{VERSION}.spec").read_text(encoding="utf-8")
        for name in ("USER-AGREEMENT.md", "PRIVACY-POLICY.md", "THIRD-PARTY-NOTICES.md"):
            self.assertIn(name, spec)
        installer = (ROOT / "installer/MicroGlowRelay.iss").read_text(encoding="utf-8")
        self.assertIn("LicenseFile=", installer)
        # 2026-11-17 起按业主要求改标准路径 C:\Program Files，安装需要管理员权限。
        self.assertIn("PrivilegesRequired=admin", installer)
        self.assertIn(r"DefaultDirName={autopf}\MicroGlow Relay", installer)
