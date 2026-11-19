# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""请求侧模型留痕：日志行要能区分「Codex 说用哪个模型」和「实际打到哪个出口」。

背景是一次真实投诉：在 Codex 里给多个会话选了模型，任务跑起来发现不是最初选中的那个。
查证时卡在一个盲点上——日志的 `model` 字段是**出口模型名**（profile 里的 model），
而 Codex 请求体里发来的是**配置 id** 或原生 slug，两者根本不是一回事。
只有出口名，就分不清「Codex 发错」和「Relay 路由错」。

这里锁三件事：

* 请求 model 与解析出的配置一致时**不落字段**（否则每行都在复制 profile_id）；
* 不一致（默认入口 `microglow-relay`、原生 slug 透传）时**落字段**且不丢原文；
* 落盘再读回来还在，且小计照常记账（字段是加法，不能影响既有口径）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from records import ActivityLog  # noqa: E402

PROFILE = {"id": "model-abc123def456", "provider": "openai",
           "provider_name": "示例中转", "model": "glm-5.3"}


class RequestModelTraceTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="microglow-relay-trace-"))

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def _log(self) -> ActivityLog:
        return ActivityLog(self.directory, load=False)

    def _rows(self) -> list[dict]:
        path = self.directory / "microglow-relay-usage.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    # ------------------------------------------------------------ 落不落字段

    def test_same_model_as_profile_leaves_no_trace_field(self):
        log = self._log()
        log.add(profile=PROFILE, elapsed=0.5, status=200,
                input_tokens=10, output_tokens=5,
                request_model=PROFILE["id"])
        row = self._rows()[-1]
        self.assertNotIn("request_model", row)
        self.assertEqual(row["profile_id"], PROFILE["id"])
        self.assertEqual(row["model"], "glm-5.3")

    def test_router_model_is_recorded_because_it_means_following_the_default(self):
        log = self._log()
        log.add(profile=PROFILE, elapsed=0.5, status=200,
                input_tokens=10, output_tokens=5,
                request_model="microglow-relay")
        row = self._rows()[-1]
        self.assertEqual(row["request_model"], "microglow-relay")

    def test_native_slug_passthrough_keeps_the_original_request_name(self):
        profile = dict(PROFILE, model="gpt-6-astra")
        log = self._log()
        log.add(profile=profile, elapsed=0.5, status=200,
                input_tokens=10, output_tokens=5,
                request_model="gpt-6-astra")
        row = self._rows()[-1]
        self.assertEqual(row["request_model"], "gpt-6-astra")

    def test_missing_request_model_is_tolerated(self):
        """老版本写下的行没有这个字段；新增字段不能反过来要求它必须存在。"""
        log = self._log()
        log.add(profile=PROFILE, elapsed=0.5, status=200,
                input_tokens=10, output_tokens=5)
        self.assertNotIn("request_model", self._rows()[-1])

    # ------------------------------------------------------------ 持久化与口径

    def test_field_survives_reload_and_is_capped(self):
        log = self._log()
        long_name = "model-" + "x" * 300
        log.add(profile=PROFILE, elapsed=0.5, status=200,
                input_tokens=10, output_tokens=5, request_model=long_name)
        log.trips.flush()
        reloaded = ActivityLog(self.directory)
        row = reloaded.recent(1)[-1]
        self.assertEqual(row["request_model"], long_name[:120])

    def test_trip_counters_still_see_the_row(self):
        """加字段不能把记账打断：同一笔请求，小计与日总量都要照常 +1。"""
        log = self._log()
        log.add(profile=PROFILE, elapsed=0.5, status=200,
                input_tokens=7, output_tokens=3, request_model="microglow-relay")
        trip = log.trip_summary()["A"]
        today = log.today()
        self.assertEqual(trip["input_tokens"], today["input_tokens"])
        self.assertEqual(trip["output_tokens"], today["output_tokens"])
        self.assertEqual(trip["requests"], today["requests"])
        self.assertEqual(trip["input_tokens"], 7)
        self.assertEqual(trip["output_tokens"], 3)


class DetailPanelTests(unittest.TestCase):
    """详情面板要能同时给出「出口模型」和「Codex 请求的模型」。"""

    app = None

    @classmethod
    def setUpClass(cls):
        global QApplication, Gateway, Settings, Bridge, Shell, theme, set_language
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ["CODEX_HOME"] = str(Path(tempfile.gettempdir()) / "microglow-relay-trace-codex")
        from PySide6.QtWidgets import QApplication as _QApplication
        from server import Gateway as _Gateway
        from storage import Settings as _Settings
        from app import theme as _theme
        from app.bridge import Bridge as _Bridge
        from app.i18n import set_language as _set_language
        from app.window import Shell as _Shell
        QApplication, Gateway, Settings = _QApplication, _Gateway, _Settings
        Bridge, Shell, theme, set_language = _Bridge, _Shell, _theme, _set_language
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        set_language("zh-CN")
        self.temporary = tempfile.TemporaryDirectory(prefix="microglow-relay-trace-ui-")
        self.settings = Settings(Path(self.temporary.name))
        self.settings.data["language"] = "zh-CN"
        self.gateway = Gateway(self.settings)
        theme.apply_palette("microglow")
        self.app.setStyleSheet(theme.stylesheet())
        self.bridge = Bridge(self.settings, self.gateway)
        self.shell = Shell(self.bridge)
        self.shell.resize(1500, 950)
        self.page = self.shell.pages["dashboard"]

    def tearDown(self):
        self.shell.deleteLater()
        self.gateway.stop()
        for _ in range(6):
            self.app.processEvents()
        self.temporary.cleanup()

    def _row(self, **overrides):
        row = {"time": "03:20:00", "provider": "示例中转", "model": "glm-5.3",
               "status": 200, "ok": True, "elapsed": 1.25,
               "input_tokens": 100, "output_tokens": 20}
        row.update(overrides)
        return row

    def test_detail_panel_says_it_matches_when_request_equals_profile(self):
        self.page._set_detail(self._row())
        self.assertIn("一致", self.page.detail_values["request"].text())

    def test_detail_panel_shows_the_raw_request_model_when_it_differs(self):
        self.page._set_detail(self._row(request_model="microglow-relay"))
        self.assertEqual(self.page.detail_values["request"].text(), "microglow-relay")
        self.assertEqual(self.page.detail_values["model"].text(), "glm-5.3")


if __name__ == "__main__":
    unittest.main()
