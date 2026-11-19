# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Update source failover, integrity checks, and user-only execution boundary."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen as real_urlopen
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from app import updates

DATA = b"synthetic installer; never executable"
URL = "https://github.com/mazda6hk-coder/MicroGlow-Relay/releases/download/v5.1/setup.exe"
MIRROR = "https://www.microglow.com.cn/updates/relay/5.1/setup.exe"


def manifest(**changes):
    result = dict(schema=1, product="MicroGlow-Relay", platform="windows-x64", version="5.1",
                  size=len(DATA), sha256=hashlib.sha256(DATA).hexdigest(), download_urls=[URL, MIRROR])
    return result | changes


class AutoUpdateTests(unittest.TestCase):
    def test_real_http_stream_and_integrity_in_isolated_fixture(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", str(len(DATA)))
                self.end_headers()
                self.wfile.write(DATA)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            def open_fixture(request, timeout):
                return real_urlopen(f"http://127.0.0.1:{server.server_port}/installer", timeout=timeout)
            with tempfile.TemporaryDirectory() as folder, patch.object(updates, "urlopen", side_effect=open_fixture):
                path = updates.download_update(updates._manifest(manifest(), "5.0"), Path(folder))
                self.assertEqual(path.read_bytes(), DATA)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_github_primary(self):
        release = dict(tag_name="v5.1", assets=[dict(name="update.json", browser_download_url=URL.replace("setup.exe", "update.json"))])
        with patch.object(updates, "_json", side_effect=[release, manifest()]) as read:
            result = updates.check_downloadable_update("5.0")
        self.assertEqual(result.status, "available")
        self.assertEqual(read.call_count, 2)

    def test_github_failure_uses_official(self):
        with patch.object(updates, "_json", side_effect=[OSError("offline"), manifest()]) as read:
            result = updates.check_downloadable_update("5.0")
        self.assertEqual(result.latest_version, "5.1")
        self.assertEqual(read.call_args.args[0], updates.WEBSITE_MANIFEST)

    def test_unpublished_not_current(self):
        with patch.object(updates, "_json", side_effect=[OSError(), manifest(available=False)]):
            self.assertEqual(updates.check_downloadable_update("5.0").status, "unavailable")

    def test_current_does_not_download(self):
        self.assertEqual(updates._manifest(manifest(version="5.0"), "5.0").status, "current")

    def test_manifest_rejects_wrong_platform_digest_url(self):
        for changes in (dict(platform="linux"), dict(sha256=""), dict(size=0), dict(download_urls=["http://bad/setup.exe"]), dict(download_urls=["https://evil.example/x.exe"])):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                updates._manifest(manifest(**changes), "5.0")

    def test_download_failure_mirror_success_and_cached_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            result = updates._manifest(manifest(), "5.0")
            with patch.object(updates, "urlopen", side_effect=[OSError(), io.BytesIO(DATA)]) as request:
                path = updates.download_update(result, Path(folder))
            self.assertEqual(request.call_args.args[0].full_url, MIRROR)
            self.assertEqual(path.read_bytes(), DATA)
            with patch.object(updates, "urlopen") as request:
                self.assertEqual(updates.download_update(result, Path(folder)), path)
                request.assert_not_called()

    def test_integrity_mismatch_never_creates_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(updates, "urlopen", side_effect=lambda *a, **k: io.BytesIO(b"wrong")):
                with self.assertRaises(RuntimeError):
                    updates.download_update(updates._manifest(manifest(), "5.0"), Path(folder))
            self.assertFalse(list(Path(folder).iterdir()))

    def test_background_controller_never_executes_installer(self):
        from PySide6.QtWidgets import QApplication, QWidget, QPushButton
        from app.update_controller import UpdateController
        app = QApplication.instance() or QApplication([])
        shell = QWidget()
        shell.pages = {"settings": Mock(update_button=QPushButton())}
        shell.bridge = Mock()
        shell.bridge.compatibility_busy = False
        shell.notify = Mock()
        shell.ask = Mock(return_value=False)
        controller = UpdateController(shell, automatic=False)
        result = updates._manifest(manifest(), "5.0")
        with patch("app.update_controller.subprocess.Popen") as execute:
            controller.checked(result)
            controller.downloaded(Path("synthetic.exe"))
            execute.assert_not_called()
            controller.install()
            execute.assert_not_called()
        shell.deleteLater()

    def test_only_confirmed_install_launches(self):
        from PySide6.QtWidgets import QApplication, QWidget, QPushButton
        from app.update_controller import UpdateController
        app = QApplication.instance() or QApplication([])
        shell = QWidget()
        shell.pages = {"settings": Mock(update_button=QPushButton())}
        shell.bridge = Mock()
        shell.bridge.compatibility_busy = False
        shell.ask = Mock(return_value=True)
        shell.notify = Mock()
        controller = UpdateController(shell, automatic=False)
        controller.result = updates._manifest(manifest(), "5.0")
        controller.ready = Path("synthetic.exe")
        with patch("app.update_controller.subprocess.Popen") as execute:
            controller.install()
            execute.assert_not_called()
            self.assertTrue(controller.busy)
            # Worker completion after successful re-verification is the only launch point.
            shell.bridge.run.call_args.args[1](controller.ready)
            execute.assert_called_once_with(["synthetic.exe"], close_fds=True)
        shell.deleteLater()

    def test_startup_timer_triggers_background_check(self):
        from PySide6.QtWidgets import QApplication, QWidget, QPushButton
        from app.update_controller import UpdateController
        app = QApplication.instance() or QApplication([])
        shell = QWidget()
        shell.pages = {"settings": Mock(update_button=QPushButton())}
        shell.bridge = Mock()
        controller = UpdateController(shell, automatic=True)
        self.assertTrue(controller.timer.isActive())
        self.assertEqual(controller.timer.interval(), 86400000)
        deadline = time.monotonic() + 7
        while not shell.bridge.run.called and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.02)
        self.assertTrue(shell.bridge.run.called)
        self.assertFalse(shell.pages["settings"].update_button.isEnabled())
        controller.timer.stop()
        shell.deleteLater()

    def test_new_labels_have_all_translations(self):
        from app.i18n import LANGUAGE_CHOICES, set_language, tr
        for code, _ in LANGUAGE_CHOICES:
            set_language(code)
            if code != "zh-CN":
                self.assertNotEqual(tr("安装更新"), "安装更新")
        set_language("en")


if __name__ == "__main__":
    unittest.main()
