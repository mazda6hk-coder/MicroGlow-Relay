"""Final-design acceptance: canvas events, durable accounting and real payloads."""
import csv
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from datetime import date
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from storage import Settings
from server import Gateway
from app import theme
from app.bridge import Bridge
from app.dialogs import ProfileDialog
from app.i18n import set_language
from app.window import Shell


class FinalUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        base = Path("R:/WorkBuddyTmp/UI-FINAL-IMPLEMENT"); base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="test-", dir=base)
        self.directory = Path(self.temp.name)
        self.environment = patch.dict(os.environ, CODEX_HOME=str(self.directory / "codex"), CLAUDE_CONFIG_DIR=str(self.directory / "claude"))
        self.environment.start()
        set_language("zh-CN"); theme.apply_palette("winter-day"); self.app.setStyleSheet(theme.stylesheet())
        self.settings = Settings(self.directory)
        self.settings.data.update(language="zh-CN", day_night="day", motion="static")
        self.profile = self.settings.upsert(dict(provider="自定义 / 中转服务", provider_name="Fixture",
            model="fixture-model", protocol="chat", base_url="https://fixture.invalid/v1"), "fixture-key")
        self.gateway = Gateway(self.settings, with_telemetry=False)
        self.bridge = Bridge(self.settings, self.gateway)
        self.errors = []; self.excepthook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: self.errors.append(str(value))
        self.shell = Shell(self.bridge); self.shell.resize(1340, 900); self.shell.show(); self.process()

    def process(self):
        for _ in range(4): self.app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def tearDown(self):
        self.shell.hide(); self.shell.deleteLater(); self.process()
        self.gateway.close(); self.environment.stop(); self.temp.cleanup()
        sys.excepthook = self.excepthook
        self.assertEqual(self.errors, [])

    def feed(self, incoming=1000, outgoing=100, **fields):
        self.gateway.activity.add(profile=self.profile, status=200, elapsed=2.5,
            input_tokens=incoming, output_tokens=outgoing, **fields)

    def test_canvas_scaling_centering_and_native_navigation_events(self):
        for width, height in ((1005,675), (1296,880), (1340,900), (1600,900), (1600,1200)):
            self.shell.resize(width, height); self.process()
            scale = min(width/1296, height/880)
            self.assertAlmostEqual(self.shell.canvas_view.transform().m11(), scale, places=6)
            self.assertEqual(self.shell.canvas.size().toTuple(), (1340,900))
            self.assertFalse(self.shell.canvas_view.horizontalScrollBar().isVisible())
            self.assertFalse(self.shell.canvas_view.verticalScrollBar().isVisible())
            target = self.shell.canvas_view.mapFromScene(QPointF(390,36))
            QTest.mouseClick(self.shell.canvas_view.viewport(), Qt.LeftButton, pos=target); self.process()
            self.assertIs(self.shell.stack.currentWidget(), self.shell.pages["models"])

    def test_trip_rename_enter_escape_limit_and_stable_card(self):
        page = self.shell.pages["dashboard"]; title = page.trip_slots["A"]["name"]
        size = page.trip_card.size()
        title.start_edit(); title.editor.setText("一二三四五六七八九十十一十二")
        self.assertEqual(len(title.editor.text()), 12)
        QTest.keyClick(title.editor, Qt.Key_Return); self.process()
        self.assertEqual(len(self.bridge.trip_stats()["A"]["name"]), 12)
        before = self.bridge.trip_stats()["A"]["name"]
        title.start_edit(); title.editor.setText("取消"); QTest.keyClick(title.editor, Qt.Key_Escape)
        self.assertEqual(self.bridge.trip_stats()["A"]["name"], before)
        self.assertEqual(page.trip_card.size(), size)
        title.start_edit(); title.editor.clear(); QTest.keyClick(title.editor, Qt.Key_Return)
        self.assertEqual(self.bridge.trip_stats()["A"]["name"], "")

    def test_reset_undo_preserves_name_scope_new_calls_and_card_dimensions(self):
        self.feed(client="responses", cached_tokens=200, cache_creation_input_tokens=50, mitigated="timeout")
        self.bridge.rename_trip("A", "本地区间"); self.bridge.set_trip_scope("A", "responses")
        page = self.shell.pages["dashboard"]; page.refresh(); before = self.bridge.trip_stats()["A"]
        size = page.trip_card.size(); page._reset_trip("A")
        slot = page.trip_slots["A"]
        self.assertFalse(slot["undo"].isHidden()); self.assertTrue(slot["info"].isHidden())
        self.assertEqual(self.bridge.trip_stats()["A"]["tokens"], 0)
        self.assertEqual(self.bridge.trip_stats()["A"]["name"], "")
        self.feed(20, 2, client="responses")
        page._undo_trip("A"); after = self.bridge.trip_stats()["A"]
        for key in ("name", "scope", "started_at", "reset_at"): self.assertEqual(after[key], before[key])
        self.assertEqual(after["tokens"], before["tokens"] + 22)
        self.assertEqual(len(self.bridge.trip_ledger_entries()), 0)
        self.assertEqual(page.trip_card.size(), size)

    def test_zero_reset_does_not_create_history_and_notice_expires(self):
        page = self.shell.pages["dashboard"]; page._reset_trip("A")
        self.assertEqual(self.bridge.trip_ledger_entries(), [])
        slot = page.trip_slots["A"]; slot["deadline"] = time.monotonic() - 1; page._undo_tick("A")
        self.assertTrue(slot["undo"].isHidden()); self.assertFalse(slot["info"].isHidden())

    def test_drums_roll_then_settle_after_one_second(self):
        from app.odometer import Odometer
        meter = Odometer()
        self.addCleanup(meter.deleteLater)
        with patch("app.odometer.motion_allowed", return_value=True):
            meter.set_value(123, animate=True)
            QTest.qWait(250)
            self.assertTrue(any(0 < cell.progress < 1 for cell in meter._cells))
            QTest.qWait(850)
            self.assertTrue(all(not cell._timer.isActive() for cell in meter._cells))
            self.assertEqual("".join(cell.char for cell in meter._cells), "000000000123")

    def test_scope_protocol_and_count_tokens_endpoint_exclusion(self):
        self.feed(100, 10, client="responses"); self.feed(200, 20, client="anthropic")
        self.bridge.set_trip_scope("A", "anthropic")
        self.assertEqual(self.bridge.trip_stats()["A"]["tokens"], 220)
        self.gateway.activity.trips._fold(dict(path="/v1/messages/count_tokens", timestamp=time.time(), input_tokens=999))
        self.assertEqual(self.bridge.trip_stats()["A"]["tokens"], 220)
        self.bridge.set_trip_scope("A", "all")
        self.assertEqual(self.bridge.trip_stats()["A"]["tokens"], 330)

    def test_history_restore_archives_current_excludes_gap_and_removes_source(self):
        self.feed(cached_tokens=400, cache_creation_input_tokens=80, mitigated="rate_limit")
        self.bridge.rename_trip("A", "原区间"); before = self.bridge.trip_stats()["A"]
        self.bridge.reset_trip("A"); entry = self.bridge.trip_ledger_entries()[0]
        self.feed(10, 1)
        self.assertTrue(self.bridge.restore_trip_ledger_entry(entry["id"]))
        self.assertNotIn(entry["id"], [e["id"] for e in self.bridge.trip_ledger_entries()])
        self.assertEqual(self.bridge.trip_ledger_entries()[0]["input_tokens"], 10)
        self.assertEqual(self.bridge.trip_stats()["A"]["tokens"], before["tokens"])
        self.feed(20,2)
        self.assertEqual(self.bridge.trip_stats()["A"]["tokens"], before["tokens"] + 22)
        self.gateway.activity.trips.flush()
        from trips import TripStore
        reopened = TripStore(self.directory, log_name=self.gateway.activity.path.name)
        reopened.sync(self.gateway.activity._log_files())
        self.assertEqual(reopened.summary()["A"]["tokens"], before["tokens"] + 22)
        self.assertEqual(reopened.summary()["A"]["name"], "原区间")

    def test_ledger_cache_models_mitigation_and_bom_csv_persist(self):
        self.feed(cached_tokens=400, cache_creation_input_tokens=80, mitigated="rate_limit")
        self.bridge.reset_trip("A"); entry = self.bridge.trip_ledger_entries()[0]
        self.assertEqual((entry["cached_input_tokens"], entry["cache_creation_tokens"], entry["mitigated"]), (400,80,1))
        self.assertEqual(entry["models"]["fixture-model"]["tokens"], 1100)
        path = self.directory / "行程.csv"; self.bridge.export_trip_ledger_csv(path)
        self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
        rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
        self.assertEqual(rows[1][0], ""); self.assertEqual(rows[1][6:10], ["600","100","400","80"])
        from trip_ledger import TripLedger
        self.assertEqual(TripLedger(self.directory).entries()[0]["models"], entry["models"])

    def test_restored_trip_duration_does_not_include_the_archived_gap(self):
        self.feed(); self.bridge.reset_trip("A")
        entry = self.bridge.trip_ledger_entries()[0]
        later = time.time() + 3600
        with patch("trips.time.time", return_value=later):
            self.bridge.restore_trip_ledger_entry(entry["id"])
            self.assertAlmostEqual(self.bridge.trip_stats()["A"]["elapsed"], entry["elapsed"], places=3)

    def test_hourly_channel_and_dashboard_totals_share_index_after_restart(self):
        self.feed(channel_index=0, mitigated="timeout"); self.feed(200,20,channel_index=1)
        summary = self.gateway.activity.range_summary(date.today(),date.today())
        details = self.gateway.activity.daily_details(date.today())
        self.assertEqual(sum(h["tokens"] for h in details["hours"]), summary["tokens"])
        self.assertEqual(sum(h["requests"] for h in details["hours"]), summary["requests"])
        from records import ActivityLog
        other = ActivityLog(self.directory)
        self.assertEqual(other.range_summary(date.today(), date.today())["mitigated"], 1)
        self.assertEqual(other.daily_details(date.today())["channels"][(self.profile["id"],1)]["requests"], 1)

    def test_odo_retains_daily_aggregates_after_raw_log_retention(self):
        self.feed(); before = self.bridge.odo_stats()
        self.gateway.activity.path.unlink()
        self.assertEqual(self.bridge.odo_stats()["tokens"], before["tokens"])

    def test_model_grouping_selection_sort_weight_key_and_cooldown(self):
        self.bridge.update_channels(self.profile["id"], [dict(label="甲",base_url="https://a.invalid/v1",weight=3),dict(label="乙",base_url="https://b.invalid/v1",weight=1)], ["key-a","key-b"])
        other = self.bridge.save_profile(dict(self.profile, id="", provider_name="第二渠道"), "key-c")
        self.bridge.update_channels(other["id"], [dict(label="丙",base_url="https://c.invalid/v1",weight=1)], ["key-c"])
        page = self.shell.pages["models"]; page.rebuild()
        self.assertIn("1 个模型组 · 3 个渠道", page.summary.text())
        self.assertEqual(page.selected_model, self.profile["model"])
        c = dict(profile_id=self.profile["id"], index=0)
        page._change_channel(c, weight=4)
        stored = self.bridge.profile(self.profile["id"], include_key=True)
        self.assertEqual(stored["channels"][0]["api_key"], "key-a")
        self.assertEqual(stored["channels"][0]["weight"], 4)
        self.gateway.channel_router.mark_failure(0,self.profile["id"])
        health = self.bridge.channel_health()
        self.assertFalse(health[self.profile["id"]][0]["healthy"])
        self.assertTrue(all(e["healthy"] for e in health.get(other["id"], [])))

    def test_profile_editor_roundtrip_does_not_erase_channel_keys(self):
        self.bridge.update_channels(self.profile["id"], [dict(label="甲",base_url="https://a.invalid/v1",weight=3),dict(label="乙",base_url="https://b.invalid/v1",weight=1)], ["key-a","key-b"])
        original = self.bridge.profile(self.profile["id"],include_key=True)
        dialog = ProfileDialog(self.bridge, original, original["api_key"], self.shell)
        dialog._remove_channel_row(dialog.channel_rows[0]); dialog.save()
        self.assertEqual(self.bridge.profile(self.profile["id"],include_key=True)["channels"][0]["api_key"], "key-b")
        dialog.deleteLater()

    def test_page_dialogs_are_parented_to_the_top_level_window(self):
        """画布页面内弹窗必须挂到顶层 Shell。

        页面被嵌进 QGraphicsScene 的 QGraphicsProxyWidget 里；把 QMessageBox/QDialog
        的 parent 设成页面本身，模态打开期间整个场景会停止重绘——实测主窗口画面从
        81.5% 掉到 2.6%，界面看似僵尸（数据仍在收发）。见 CRASH-CHECK-20261116 后续。
        """
        for name in ("views.py", "final_views.py"):
            text = (ROOT / "app" / name).read_text(encoding="utf-8")
            for pattern in ("QDialog(self)", "QMessageBox.Ok, self)", "getSaveFileName(self,"):
                self.assertNotIn(pattern, text, f"{name} 里存在以页面为父窗口的对话框：{pattern}")

    def test_background_events_do_not_rebuild_model_page_while_dialog_is_open(self):
        """后台日志不得在编辑窗口打开期间整页重建，否则销毁发起鼠标事件的按钮。

        回归自 CRASH-CHECK-20261116：Qt 在事件返回后访问已删除的控件，实测崩溃。
        """
        from shiboken6 import isValid
        from PySide6.QtWidgets import QDialog
        for index in range(3):
            self.settings.upsert(dict(self.profile, id="", model=f"guard-model-{index}"), "synthetic-key")
        self.shell.navigate("models"); page = self.shell.pages["models"]
        page.rebuild(); self.process()
        trigger = page.channel_controls[0]["edit"]
        modal = QDialog(self.shell); modal.setModal(True); modal.show(); self.process()
        try:
            self.assertIs(QApplication.activeModalWidget(), modal)
            for _ in range(20):
                self.gateway.log("success", "background event while editing")
            # 事件经轮询定时器（150ms）投递到页面，必须让事件循环真实走一轮。
            QTest.qWait(500); self.process()
            self.assertTrue(isValid(trigger), "编辑期间原按钮不得被重建销毁")
            self.assertTrue(page._refresh_pending, "应登记待刷新而不是立即重建")
        finally:
            modal.reject(); self.process()
        page._refresh_health(); self.process()
        self.assertFalse(page._refresh_pending, "关窗后应补上这次刷新")
        self.assertTrue(isValid(page.channel_controls[0]["edit"]))

    def test_themes_keep_trip_undo_and_logs_tab_and_all_layouts_fit(self):
        self.feed(); self.shell.pages["dashboard"]._reset_trip("A")
        deadline, reading, entry = self.bridge._trip_undo["A"]
        self.bridge._trip_undo["A"] = (time.monotonic() + 3600, reading, entry)
        for key in theme.THEME_ORDER:
            self.shell.apply_theme(key); self.process()
            self.assertFalse(self.shell.pages["dashboard"].trip_slots["A"]["undo"].isHidden())
            for page in ("dashboard","models","logs","settings"):
                self.shell.navigate(page); self.process()
                self.assertEqual(self.shell.pages[page].size().toTuple(),(1340,828))
        self.shell.pages["logs"].show_tab("trips"); self.shell.apply_theme("winter-day"); self.process()
        self.assertEqual(self.shell.pages["logs"].tabs.value(), "trips")

    def test_day_night_button_sets_manual_preference_and_appearance_updates(self):
        self.bridge.set_day_night_mode("system")
        self.shell.side_bar.day_night_button.click(); self.process()
        mode = self.bridge.day_night_mode()
        self.assertIn(mode,("day","night"))
        self.assertEqual(self.shell.pages["settings"].day_night_switch.value(),mode)
        self.assertEqual(theme.current.day_night,mode)

    def test_automatic_updates_respect_switch_and_once_per_day(self):
        from app.update_controller import UpdateController
        controller = UpdateController(self.shell, automatic=False)
        with patch.object(self.bridge, "run") as run:
            self.bridge.set_auto_update(False); controller.check(); run.assert_not_called()
            self.bridge.set_auto_update(True); self.bridge.mark_update_checked()
            controller.check(); run.assert_not_called()
            self.settings.data["last_update_check"] = ""
            controller.check(); self.assertEqual(run.call_count, 1)
            controller.busy = False; controller.check(); self.assertEqual(run.call_count, 1)
            controller.check(manual=True); self.assertEqual(run.call_count, 2)

    def test_local_only_legacy_consent_never_claims_upload_permission(self):
        from telemetry import CONSENT_VERSION_V2
        self.bridge.telemetry_consent.grant(2, CONSENT_VERSION_V2, allow_upload=False)
        page = self.shell.pages["settings"]; page.refresh()
        self.assertEqual(page.telemetry_state.text(), "仅本地统计")
        self.assertIsNone(self.bridge.telemetry_preview_payload())

    def test_license_entry_opens_existing_software_license_section_offline(self):
        from PySide6.QtWidgets import QPushButton, QTextBrowser
        page = self.shell.pages["settings"]
        entry = next(w for w in page.about_card.findChildren(QPushButton) if w.text() == "许可证")
        entry.click(); self.process()
        text = page.document_dialog.findChild(QTextBrowser).toPlainText()
        self.assertIn("3. 软件许可", text)
        self.assertNotIn("4. ", text)
        page.document_dialog.close()

    def test_disabled_single_channel_blocks_upstream_and_default_model_merges_owners(self):
        import httpx
        from test_router import MockSupplier
        first, second = MockSupplier(), MockSupplier()
        try:
            self.bridge.update_channels(self.profile["id"], [dict(label="甲",base_url=first.url,weight=1,enabled=False)], ["key-a"])
            self.gateway.start(0)
            self.shell.pages["dashboard"].refresh()
            self.assertIn(str(self.gateway.port), self.shell.pages["dashboard"].hero.sub_label.text())
            self.assertTrue(self.shell.pages["dashboard"].hero.sub_label.isHidden())
            url = f"http://127.0.0.1:{self.gateway.port}/v1/responses"
            headers = {"Authorization": "Bearer " + self.settings.local_token()}
            with httpx.Client(trust_env=False) as client:
                response = client.post(url, headers=headers, json=dict(model="microglow-relay",input="fixture",stream=False), timeout=5)
                self.assertEqual(response.status_code,503); self.assertEqual(first.requests,[])
                peer = self.bridge.save_profile(dict(self.profile,id="",base_url=second.url), "key-b")
                response = client.post(url, headers=headers, json=dict(model="microglow-relay",input="fixture",stream=False), timeout=5)
                self.assertEqual(response.status_code,200)
                self.assertEqual(len(second.requests),1); self.assertEqual(first.requests,[])
        finally:
            self.gateway.stop(); first.close(); second.close()

    def test_clear_and_delete_require_confirmation(self):
        self.bridge.events.append(dict(time="12:00:00",level="success",message="事件"))
        page = self.shell.pages["logs"]
        with patch.object(self.shell,"ask",return_value=False) as ask:
            page.clear_logs(); self.assertTrue(ask.called); self.assertEqual(len(self.bridge.events),1)
        self.feed(); self.bridge.reset_trip("A")
        page.show_tab("trips"); page._selected_trip = self.bridge.trip_ledger_entries()[0]["id"]; page._refresh_trips()
        with patch.object(self.shell,"ask",return_value=False): page._delete_record()
        self.assertEqual(len(self.bridge.trip_ledger_entries()),1)

    def test_arrowless_dates_open_native_calendar_and_presets_update_range(self):
        self.shell.navigate("logs"); page = self.shell.pages["logs"]; self.process()
        QTest.mouseClick(page.query_date, Qt.LeftButton); self.process()
        self.assertTrue(page.query_date.calendarWidget().isVisible())
        QTest.keyClick(page.query_date.calendarWidget(), Qt.Key_Escape); self.process()
        page.period.setValue("month"); page._apply_period()
        self.assertEqual(page.query_date.date().day(), 1)
        self.assertEqual(page.query_end.date().month(), page.query_date.date().month())

    def test_telemetry_preview_is_the_actual_next_payload_and_excludes_trip_names(self):
        from telemetry.runtime import TelemetryRuntime
        self.gateway.telemetry = TelemetryRuntime(self.directory,"0.9",uploader=None)
        self.bridge.set_telemetry_consent(True)
        self.bridge.rename_trip("A","机密项目名称")
        self.gateway.telemetry.record_request(provider="custom", model="fixture-model",status=200,
            elapsed_seconds=1,input_tokens=10,output_tokens=2,call_channel="relay")
        payload = self.bridge.telemetry_preview_payload()
        expected = self.gateway.telemetry.batches.list_retryable(2)[0]["payload"]
        self.assertEqual(payload,expected)
        self.assertNotIn("机密项目名称",json.dumps(payload,ensure_ascii=False))
        self.assertNotIn("fixture-key",json.dumps(payload))
        self.bridge.set_telemetry_consent(False)
        self.assertIsNone(self.bridge.telemetry_preview_payload())


if __name__ == "__main__": unittest.main()
