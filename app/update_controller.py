"""Background check/download. Never starts an installer until an explicit click."""
from pathlib import Path
import time
import subprocess

from PySide6.QtCore import QObject, QTimer

from .i18n import tr, trf
from .updates import check_downloadable_update, download_update


class UpdateController(QObject):
    def __init__(self, shell, automatic=True):
        super().__init__(shell)
        self.shell = shell
        self.busy = False
        self.ready = None
        self.result = None
        self.manual = False
        self.timer = QTimer(self)
        self.timer.setInterval(24 * 60 * 60 * 1000)
        self.timer.timeout.connect(self.check)
        if automatic:
            self.timer.start()
            QTimer.singleShot(5000, self.check)

    def button(self):
        return self.shell.pages["settings"].update_button

    def check(self, manual=False):
        if self.busy:
            return
        if not manual:
            if not self.shell.bridge.auto_update_enabled():
                return
            if str(self.shell.bridge.last_update_check())[:10] == time.strftime("%Y-%m-%d"):
                return
        self.manual = manual
        if self.ready:
            if manual:
                self.install()
            return
        self.busy = True
        self.shell.bridge.mark_update_checked()
        self.button().setEnabled(False)
        self.shell.bridge.run(check_downloadable_update, self.checked, self.failed)

    def checked(self, result):
        self.result = result
        self.shell.pages["settings"].set_version_state(
            result.status, getattr(result, "latest_version", ""))
        if result.status == "available":
            self.button().setText(tr("正在下载更新"))
            self.shell.bridge.run(
                lambda: download_update(result, Path(self.shell.bridge.settings.directory) / "updates"),
                self.downloaded, self.failed)
            return
        self.busy = False
        self.button().setEnabled(True)
        if self.manual:
            self.shell.notify(tr("已是最新版本") if result.status == "current" else tr("暂无可用的正式更新"), "info")

    def downloaded(self, path):
        self.ready = path
        self.busy = False
        self.button().setText(tr("安装更新"))
        self.button().setEnabled(True)
        self.shell.notify(trf("版本 {0} 已下载，请在设置中点击安装更新。", self.result.latest_version), "success", 8000)

    def failed(self, error):
        self.busy = False
        self.button().setText(tr("检查更新"))
        self.button().setEnabled(True)
        if self.manual or (self.result and self.result.status == "available"):
            self.shell.notify(tr("检查或下载更新失败，请稍后重试"), "error")

    def install(self):
        if not self.ready or self.shell.bridge.compatibility_busy:
            return
        if not self.shell.ask(tr("安装更新"), tr("安装器将由你手动操作。是否现在打开？请在安装前正常退出 Relay。")):
            return
        # Reverify the cached file immediately before execution.
        self.busy = True
        self.button().setEnabled(False)
        self.shell.bridge.run(
            lambda: download_update(self.result, self.ready.parent),
            self.launch, self.failed)

    def launch(self, path):
        try:
            subprocess.Popen([str(path)], close_fds=True)
        except OSError as error:
            self.failed(error)
            return
        self.busy = False
        self.button().setEnabled(True)
