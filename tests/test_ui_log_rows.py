# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""实时日志的行高：单行紧凑、长报错不截断。

业主反馈日志面板行距过大（实测每行 52px，一屏仅 8.9 行），本用例固化收窄后的口径。
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CODEX_HOME"] = str(Path(tempfile.gettempdir()) / "microglow-relay-ui-codex")

from PySide6.QtWidgets import QApplication  # noqa: E402

from server import Gateway  # noqa: E402
from storage import Settings  # noqa: E402

from app import theme  # noqa: E402
from app.bridge import Bridge  # noqa: E402
from app import final_views  # noqa: E402
from app.i18n import set_language  # noqa: E402
from app.window import Shell  # noqa: E402

SHORT_EVENT = {
    "time": "22:55:45",
    "level": "success",
    "message": "",
    "request_result": {"ok": True, "elapsed": 3.3, "tokens": 234668, "model": "demo-model"},
}
LONG_EVENT = {
    "time": "22:59:10",
    "level": "error",
    "message": "请求参数或协议与供应商不兼容：The `reasoning_text` in the thinking mode "
               "must be passed back to the API. (request_id: a84c983e-2bd9-40c6-8580-ded889a0f169)",
}


class LogRowTests(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        set_language("zh-CN")
        self.temporary = tempfile.TemporaryDirectory(prefix="microglow-relay-logrows-")
        self.settings = Settings(Path(self.temporary.name))
        self.settings.data["language"] = "zh-CN"
        self.gateway = Gateway(self.settings)
        theme.apply_palette("microglow")
        self.app.setStyleSheet(theme.stylesheet())
        self.bridge = Bridge(self.settings, self.gateway)
        self.shell = Shell(self.bridge)
        self.shell.resize(1500, 950)
        self.shell.show()
        self.shell.navigate("logs")
        self.page = self.shell.pages["logs"]
        self._process()

    def tearDown(self):
        self.shell.deleteLater()
        self.gateway.stop()
        self._process()
        self.temporary.cleanup()

    def _process(self):
        for _ in range(8):
            self.app.processEvents()

    def _render(self, events, width=1200):
        self.bridge.events.clear()
        for event in events:
            self.bridge.events.append(event)
        self.page._render_all()
        self._process()
        widget = self.page.list_widget
        widget.resize(width, 400)
        self.page._fit_rows()
        return widget

    def test_single_line_rows_are_dense(self):
        widget = self._render([SHORT_EVENT] * 8)
        hints = [widget.item(index).sizeHint().height() for index in range(widget.count())]
        for hint in hints:
            self.assertEqual(hint, final_views.LOG_ROW_HEIGHT, "单行日志应压到固定的一行高度")
            self.assertLessEqual(hint, 32, "单行高度应明显低于回归前的 52px")
        self.assertEqual(widget.spacing(), 0)

    def test_request_row_names_the_routed_model(self):
        """0.5 允许一条会话内切模型，实时日志必须写明模型名。"""
        widget = self._render([SHORT_EVENT])
        self.assertIn("demo-model", widget.item(0).text())
        # 没有模型名时不能留下悬空分隔符。
        anonymous = dict(SHORT_EVENT, request_result={"ok": True, "elapsed": 1.0,
                                                       "tokens": 10, "model": ""})
        widget = self._render([anonymous])
        self.assertNotIn("··", widget.item(0).text())
        self.assertIn("1.0", widget.item(0).text())

    def test_long_message_is_not_clipped(self):
        # 宽度必须按宿主字体实测来定：既让短行放得下，又让长报错必然放不下。
        # 写死 1200px 会随字体变宽/变窄而失效 —— offscreen 字体下长报错恰好一行放得下，
        # 断言就落空了（这正是一次真实失败的原因），所以这里不能写死。
        probe = self._render([SHORT_EVENT])
        width = probe.fontMetrics().horizontalAdvance(probe.item(0).text()) + 40
        widget = self._render([SHORT_EVENT, LONG_EVENT], width=width)
        # 列表最新在上：第二个事件（长报错）应排在第 0 行。
        self.assertEqual(widget.item(0).data(final_views.LOG_MESSAGE_ROLE), LONG_EVENT["message"])
        self.assertGreater(widget.item(0).sizeHint().height(), final_views.LOG_ROW_HEIGHT,
                           "长报错必须换成多行高度，不能被截断")
        self.assertEqual(widget.item(1).sizeHint().height(), final_views.LOG_ROW_HEIGHT)

    def test_append_is_incremental(self):
        """新事件只插入一行，既有行不重建（这一条是卡顿回归的护栏）。"""
        self.bridge.events.clear()
        self.bridge.events.extend([dict(SHORT_EVENT, time=f"22:0{index}:00") for index in range(5)])
        self.page._render_all()
        self._process()
        widget = self.page.list_widget
        before = widget.count()
        self.assertEqual(before, 5)
        anchor = widget.item(before - 1).data(final_views.LOG_EVENT_ROLE)
        fresh = dict(SHORT_EVENT, time="23:00:00")
        self.bridge.events.append(fresh)
        self.page._append([fresh])
        self._process()
        self.assertEqual(widget.count(), before + 1)
        self.assertEqual(widget.item(0).data(final_views.LOG_TIME_ROLE), "23:00:00")
        self.assertEqual(widget.item(widget.count() - 1).data(final_views.LOG_EVENT_ROLE), anchor,
                         "旧行必须原地保留，不能被 clear() 重建")


if __name__ == "__main__":
    unittest.main()
