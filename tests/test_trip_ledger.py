# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Trip 账本 + 缓存读写拆分 + 恢复读数（任务书第 5 节后端）。"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trip_ledger import TripLedger  # noqa: E402
from trips import TripStore  # noqa: E402


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.store = TripStore(self.directory, log_name="demo.jsonl")
        self.ledger = TripLedger(self.directory)

    def tearDown(self):
        self.temp.cleanup()

    def _feed(self, store: TripStore, *, input_tokens=100, output_tokens=20,
              cached=None, creation=None, timestamp=None):
        row = {"timestamp": timestamp or time.time(),
               "input_tokens": input_tokens, "output_tokens": output_tokens,
               "requests": 1}
        if cached is not None:
            row["cached_tokens"] = cached
        if creation is not None:
            row["cache_creation_input_tokens"] = creation
        store.note_row(row, filename="demo.jsonl", before=0, after=10)

    def test_snapshot_matches_display_exactly(self):
        """账册数字与清零前 summary 完全一致（构造保证，不靠巧合）。"""
        self._feed(self.store, input_tokens=1234, output_tokens=56)
        before = self.store.summary()["A"]
        entry = self.ledger.snapshot("A", self.store.summary())
        self.assertEqual(entry["input_tokens"], before["input_tokens"])
        self.assertEqual(entry["output_tokens"], before["output_tokens"])
        self.assertEqual(entry["requests"], before["requests"])
        self.assertEqual(entry["from"], before["started_at"])

    def test_snapshot_then_reset_then_restore(self):
        self._feed(self.store, input_tokens=500, output_tokens=50)
        entry = self.ledger.snapshot("A", self.store.summary())
        self.store.reset("A")
        self.assertEqual(self.store.summary()["A"]["tokens"], 0)
        # 恢复为当前区间：读数原样回来。
        self.assertTrue(self.ledger.restore(entry["id"], self.store))
        restored = self.store.summary()["A"]
        self.assertEqual(restored["input_tokens"], 500)
        self.assertEqual(restored["output_tokens"], 50)
        self.assertEqual(restored["requests"], 1)
        # 定稿要求：恢复后的记录从历史中移除。
        self.assertEqual(len(self.ledger.entries("A")), 0)

    def test_rename_delete_and_persistence(self):
        self._feed(self.store)
        entry = self.ledger.snapshot("A", self.store.summary())
        self.assertTrue(self.ledger.rename(entry["id"], "五月冲刺"))
        self.assertTrue(self.ledger.delete(entry["id"]))
        self.assertEqual(self.ledger.entries(), [])
        # 重启后仍持久。
        self.ledger.snapshot("B", self.store.summary())
        reopened = TripLedger(self.directory)
        self.assertEqual(len(reopened.entries("B")), 1)

    def test_csv_export_carries_all_columns(self):
        self._feed(self.store, input_tokens=100, output_tokens=10)
        self.ledger.snapshot("A", self.store.summary())
        text = self.ledger.to_csv()
        self.assertIn("区间名称", text)
        self.assertIn("总 Token", text)
        self.assertIn("110", text)          # 100 + 10
        self.assertIn("\ufeff", text[:1])   # BOM


class CacheSplitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_cached_and_creation_tokens_fold_into_trip(self):
        store = TripStore(self.directory, log_name="demo.jsonl")
        store.note_row({"timestamp": time.time(), "input_tokens": 1000,
                        "output_tokens": 100, "cached_tokens": 400,
                        "cache_creation_input_tokens": 200},
                       filename="demo.jsonl", before=0, after=10)
        slot = store.summary()["A"]
        self.assertEqual(slot["input_tokens"], 1000)      # 输入口径不变
        self.assertEqual(slot["cached_input_tokens"], 400)
        self.assertEqual(slot["cache_creation_tokens"], 200)

    def test_cache_fields_survive_reopen(self):
        store = TripStore(self.directory, log_name="demo.jsonl")
        store.note_row({"timestamp": time.time(), "input_tokens": 100,
                        "output_tokens": 10, "cached_tokens": 60},
                       filename="demo.jsonl", before=0, after=10)
        store.flush()
        reopened = TripStore(self.directory, log_name="demo.jsonl")
        self.assertEqual(reopened.summary()["A"]["cached_input_tokens"], 60)

    def test_odo_equals_log_total(self):
        """ODO ≥ A、B 且与日志累计同源：同一行日志，A/B/ODO 看到的是同一份数。"""
        store = TripStore(self.directory, log_name="demo.jsonl")
        for index in range(3):
            store.note_row({"timestamp": time.time(), "input_tokens": 10,
                            "output_tokens": 5},
                           filename="demo.jsonl", before=index * 10, after=(index + 1) * 10)
        # 两段都没清零过 → 每段都是全量 45；ODO（日志累计）同为 45，
        # 不等式 ODO ≥ max(A,B) 取等，与任务书「总里程 ≥ A、B」一致。
        slot_a = store.summary()["A"]
        slot_b = store.summary()["B"]
        log_total = 45   # 3 行 × (10+5)，与 ActivityLog 口径相同（input+output）
        self.assertEqual(slot_a["tokens"], log_total)
        self.assertEqual(slot_b["tokens"], log_total)
        self.assertGreaterEqual(log_total, max(slot_a["tokens"], slot_b["tokens"]))


if __name__ == "__main__":
    unittest.main()
