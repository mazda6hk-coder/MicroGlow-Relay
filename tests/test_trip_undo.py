"""UI-090-TRIP-UNDO: 清零撤销与账本快照（任务书第 5 节）。

- 清零即快照入账本，账本数字与清零前显示完全一致（构造保证）；
- 10 秒内可撤销，撤销后读数恢复（等于清零从未发生）；
- 账本可改名/删除/导出 CSV。
"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication

from storage import Settings  # noqa: E402
from server import Gateway  # noqa: E402
from trip_ledger import TripLedger  # noqa: E402
from trips import TripStore  # noqa: E402


def _feed(store: TripStore, incoming: int, outgoing: int = 0) -> None:
    store.note_row({"timestamp": time.time(), "input_tokens": incoming,
                    "output_tokens": outgoing},
                   filename="activity.jsonl", before=0, after=0)


class TripUndoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="microglow-trip-undo-")
        self.settings = Settings(Path(self.temporary.name))
        self.gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)

    def tearDown(self):
        self.gateway.stop()
        self.temporary.cleanup()

    def test_reset_snapshots_to_ledger(self):
        """清零即入账本：数字与清零前读数一致（走 Bridge 全链路）。"""
        from app.bridge import Bridge

        store = self.gateway.activity.trips
        _feed(store, 120, 30)
        before = store.summary()["A"]
        self.assertEqual(before["tokens"], 150)

        bridge = Bridge(self.settings, self.gateway)
        bridge.reset_trip("A")
        entry = self.gateway.trip_ledger.entries("A")[-1]
        self.assertEqual(int(entry["input_tokens"]), 120)
        self.assertEqual(int(entry["output_tokens"]), 30)
        self.assertEqual(int(entry["requests"]), 1)

    def test_bridge_reset_writes_ledger_and_undo_restores(self):
        """Bridge.reset_trip 走账本；undo_reset_trip 恢复读数。"""
        from app.bridge import Bridge

        _feed(self.gateway.activity.trips, 500, 50)
        bridge = Bridge(self.settings, self.gateway)
        reading = bridge.trip_stats()["A"]
        self.assertEqual(reading["tokens"], 550)

        bridge.reset_trip("A")
        self.assertEqual(bridge.trip_stats()["A"]["tokens"], 0)
        self.assertEqual(len(bridge.trip_ledger_entries()), 1)

        restored = bridge.undo_reset_trip("A", reading)
        self.assertEqual(restored["A"]["tokens"], 550)
        self.assertEqual(restored["A"]["requests"], reading["requests"])

    def test_ledger_rename_delete_and_csv(self):
        ledger = TripLedger(Path(self.temporary.name))
        # snapshot 期望 TripStore.summary() 的整包形状（{key: 段读数}）。
        slot = {"input_tokens": 10, "output_tokens": 5, "requests": 2,
                "started_at": time.time()}
        snapshot = ledger.snapshot("B", {"A": slot, "B": slot})
        entry_id = snapshot["id"]
        self.assertTrue(ledger.rename(entry_id, " demo 区间 "))
        entries = ledger.entries("B")
        self.assertEqual(entries[0]["name"], "demo 区间")   # 首尾空白裁剪
        self.assertTrue(ledger.delete(entry_id))
        self.assertEqual(ledger.entries("B"), [])
        # 空账本导出只有表头。
        csv_text = ledger.to_csv()
        self.assertIn("区间名称", csv_text)

    def test_snapshot_persists_across_instances(self):
        """账本落盘：新实例（重启）读回同一批记录。"""
        directory = Path(self.temporary.name)
        ledger = TripLedger(directory)
        slot = {"input_tokens": 7, "output_tokens": 3, "requests": 1}
        ledger.snapshot("A", {"A": slot, "B": slot})
        again = TripLedger(directory)
        self.assertEqual(len(again.entries("A")), 1)


if __name__ == "__main__":
    unittest.main()
