"""Manual update checks are deterministic and never auto-install."""
from __future__ import annotations

import io
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.updates import GITHUB_REPOSITORY, check_for_update  # noqa: E402
from app.i18n import set_language  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from app.bridge import Bridge  # noqa: E402
from app.window import Shell  # noqa: E402
from server import Gateway  # noqa: E402
from storage import Settings  # noqa: E402


class UpdateTests(unittest.TestCase):
    def test_default_source_is_this_product_repository(self):
        self.assertEqual(GITHUB_REPOSITORY, "mazda6hk-coder/MicroGlow-Relay")
        with patch("app.updates.urlopen", return_value=io.BytesIO(b'{"tag_name":"v3.4"}')) as opener:
            result = check_for_update()
        self.assertEqual(opener.call_args.args[0].full_url,
                         "https://api.github.com/repos/mazda6hk-coder/MicroGlow-Relay/releases/latest")
        self.assertEqual(result.release_url, "https://github.com/mazda6hk-coder/MicroGlow-Relay/releases/latest")
        # 本用例只负责「默认源就是本产品仓库」与 URL 构造；版本比较由
        # test_version_comparison_follows_relay_decimal_scheme 单独覆盖。
        # 0.5 是本方案分支自己的版本号，与 3.x / 5.x / 6.x 发布线无关；但默认
        # 发布源仍指向旧线仓库（最新发布 v3.4），两位小数比较下 0.5 < 3.4，
        # 所以状态必然是 available 而不是 current。要消除这则提示须另改发布源。
        self.assertEqual(result.status, "available")

    def test_no_published_release_is_not_reported_as_current(self):
        error = HTTPError("https://api.github.com", 404, "Not Found", {}, None)
        with patch("app.updates.urlopen", side_effect=error):
            result = check_for_update()
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(result.latest_version)

    def test_permission_and_network_failures_remain_errors(self):
        for error in (HTTPError("https://api.github.com", 403, "Forbidden", {}, None), URLError("offline")):
            with self.subTest(error=type(error).__name__), patch("app.updates.urlopen", side_effect=error):
                with self.assertRaises(type(error)):
                    check_for_update()

    def test_unconfigured_source_never_opens_network(self):
        with patch("app.updates.urlopen") as opener:
            self.assertEqual(check_for_update(" ").status, "unconfigured")
            opener.assert_not_called()

    def test_version_comparison_follows_relay_decimal_scheme(self):
        for tag, expected in (("v3.33", "available"), ("v3.32", "current"),
                              ("v3.31", "current"), ("v3.4", "available")):
            with self.subTest(tag=tag):
                response = io.BytesIO(f'{{"tag_name": "{tag}"}}'.encode())
                with patch("app.updates.urlopen", return_value=response) as opener:
                    result = check_for_update("MicroGlow/Relay", "3.32")
                self.assertEqual(result.status, expected)
                self.assertEqual(result.release_url, "https://github.com/MicroGlow/Relay/releases/latest")
                self.assertEqual(opener.call_args.kwargs["timeout"], 8)

    def test_invalid_repository_and_release_are_rejected(self):
        with patch("app.updates.urlopen") as opener:
            with self.assertRaises(ValueError):
                check_for_update("owner/repo/extra")
            opener.assert_not_called()
        with patch("app.updates.urlopen", return_value=io.BytesIO(b'{"tag_name":"invalid"}')):
            with self.assertRaises(ValueError):
                check_for_update("owner/repo")


class UpdateUiTests(unittest.TestCase):
    def test_settings_button_explains_unconfigured_source_without_network(self):
        app = QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")
        app.setFont(QFont("Microsoft YaHei", 9))
        set_language("zh-CN")
        with tempfile.TemporaryDirectory() as temporary:
            settings = Settings(Path(temporary))
            gateway = Gateway(settings)
            bridge = Bridge(settings, gateway)
            shell = Shell(bridge)
            try:
                shell.navigate("settings")
                button = shell.pages["settings"].update_button
                with patch("app.updates.urlopen") as opener, patch.object(shell, "notify") as notify, \
                     patch("app.views.check_for_update", side_effect=lambda: check_for_update(" ")):
                    button.click()
                    deadline = time.monotonic() + 5
                    while not button.isEnabled() and time.monotonic() < deadline:
                        app.processEvents()
                        time.sleep(0.01)
                    app.processEvents()
                    self.assertTrue(button.isEnabled())
                    notify.assert_called_with("更新源尚未配置", "error")
                    opener.assert_not_called()
            finally:
                gateway.stop()
                shell.deleteLater()
                app.processEvents()

    def test_empty_release_source_displays_information_and_reenables_button(self):
        app = QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")
        app.setFont(QFont("Microsoft YaHei", 9))
        set_language("zh-CN")
        with tempfile.TemporaryDirectory() as temporary:
            settings = Settings(Path(temporary))
            gateway = Gateway(settings)
            bridge = Bridge(settings, gateway)
            shell = Shell(bridge)
            try:
                page = shell.pages["settings"]
                error = HTTPError("https://api.github.com", 404, "Not Found", {}, None)
                with patch("app.updates.urlopen", side_effect=error), patch.object(shell, "notify") as notify:
                    page.update_button.click()
                    deadline = time.monotonic() + 5
                    while not page.update_button.isEnabled() and time.monotonic() < deadline:
                        app.processEvents()
                        time.sleep(0.01)
                    app.processEvents()
                    self.assertTrue(page.update_button.isEnabled())
                    notify.assert_called_with("暂无可用的正式更新", "info")
            finally:
                gateway.stop()
                shell.deleteLater()
                app.processEvents()
