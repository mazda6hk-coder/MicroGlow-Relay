"""Trip 读数口径三档（全局|Codex|Claude）——账按协议分桶并行累计。

对着这几个容易静默出错的地方写：

* 同一行日志必须同时进「本协议桶」，全局 = 两桶合并派生，不能另记一本；
* 切换口径**只换视角不动账**：切走再切回，读数分毫不变；
* 口径选择落盘：重启后 UI 停在用户选的那一档；
* 清零保留口径；撤销恢复把三本账 + 口径一起带回来；
* Claude Code 与 Codex 并发时（本功能的出发点），各口径数字各归各。
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trips import TripStore  # noqa: E402


def _row(incoming: int, outgoing: int, client: str | None, timestamp=None) -> dict:
    row = {"timestamp": timestamp or time.time(),
           "input_tokens": incoming, "output_tokens": outgoing}
    if client is not None:
        row["client"] = client
    return row


class TripScopeTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="microglow-relay-scope-"))
        self.store = TripStore(self.directory, log_name="demo.jsonl")
        self._anchor = 0  # note_row 锚点必须链式对齐：before=上一条的 after

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def _feed(self, row: dict) -> None:
        payload = (str(row) + "\n").encode("utf-8")
        after = self._anchor + len(payload)
        self.store.note_row(row, filename="demo.jsonl",
                            before=self._anchor, after=after)
        self._anchor = after

    def test_rows_split_into_protocol_buckets_and_merge_to_all(self):
        """分桶与合并：Codex 进 responses、Claude 进 anthropic，全局 = 两桶之和。"""
        self._feed(_row(1000, 100, "responses"))
        self._feed(_row(400, 40, "anthropic"))
        self._feed(_row(10, 1, "responses"))
        slot = self.store.summary()["A"]
        self.assertEqual(slot["scopes"]["responses"]["tokens"], 1111)
        self.assertEqual(slot["scopes"]["anthropic"]["tokens"], 440)
        self.assertEqual(slot["scopes"]["all"]["tokens"], 1551)
        self.assertEqual(slot["scopes"]["all"]["requests"], 3)
        # 顶层读数默认全局口径。
        self.assertEqual(slot["tokens"], 1551)

    def test_missing_client_field_folds_into_responses(self):
        """老日志行没有 client 列：按 responses 兜底（与 records.py 同口径）。"""
        self._feed(_row(300, 30, None))
        slot = self.store.summary()["A"]
        self.assertEqual(slot["scopes"]["responses"]["tokens"], 330)
        self.assertEqual(slot["scopes"]["anthropic"]["tokens"], 0)

    def test_scope_switch_never_touches_the_accounts(self):
        """切换只换视角：切走再切回，每个口径的读数分毫不变。"""
        self._feed(_row(1000, 100, "responses"))
        self._feed(_row(400, 40, "anthropic"))
        before = self.store.summary()["A"]
        self.store.set_scope("A", "anthropic")
        mid = self.store.summary()["A"]
        self.assertEqual(mid["tokens"], 440)          # 顶层读数已切到 Claude
        self.store.set_scope("A", "all")
        after = self.store.summary()["A"]
        for scope in ("all", "responses", "anthropic"):
            self.assertEqual(before["scopes"][scope]["tokens"],
                             after["scopes"][scope]["tokens"])
        self.assertEqual(after["tokens"], before["tokens"])

    def test_scope_choice_survives_restart(self):
        """口径选择落盘：重启后仍是用户选的那一档。"""
        self._feed(_row(500, 50, "responses"))
        self.store.set_scope("B", "responses")
        self.store.flush()
        reopened = TripStore(self.directory, log_name="demo.jsonl")
        slot = reopened.summary()["B"]
        self.assertEqual(slot["scope"], "responses")
        self.assertEqual(slot["tokens"], 550)

    def test_reset_keeps_scope_and_buckets_rebuild_from_zero(self):
        """清零保留口径；清零后各桶从零开始，只有新调用入账。"""
        self._feed(_row(1000, 100, "responses"))
        self.store.set_scope("A", "anthropic")
        time.sleep(0.01)
        self.store.reset("A")
        slot = self.store.summary()["A"]
        self.assertEqual(slot["scope"], "anthropic")   # 口径保留
        self.assertEqual(slot["scopes"]["all"]["tokens"], 0)
        time.sleep(0.01)
        self._feed(_row(70, 7, "anthropic"))
        slot = self.store.summary()["A"]
        self.assertEqual(slot["scopes"]["anthropic"]["tokens"], 77)
        self.assertEqual(slot["scopes"]["responses"]["tokens"], 0)
        self.assertEqual(slot["tokens"], 77)          # 顶层 = 选中口径

    def test_undo_restore_brings_back_all_buckets_and_scope(self):
        """撤销/账本恢复：三本账 + 口径一起回来（快照带 scopes 整包）。"""
        self._feed(_row(1000, 100, "responses"))
        self._feed(_row(400, 40, "anthropic"))
        self.store.set_scope("A", "responses")
        reading = self.store.summary()["A"]
        time.sleep(0.01)
        self.store.reset("A")
        self.assertEqual(self.store.summary()["A"]["tokens"], 0)
        self.store.restore_reading("A", reading)
        slot = self.store.summary()["A"]
        self.assertEqual(slot["scope"], "responses")
        self.assertEqual(slot["scopes"]["responses"]["tokens"], 1100)
        self.assertEqual(slot["scopes"]["anthropic"]["tokens"], 440)

    def test_unknown_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.set_scope("A", "claude")
        with self.assertRaises(ValueError):
            self.store.set_scope("C", "all")

    def test_concurrent_clients_each_get_their_own_reading(self):
        """本功能的出发点：Claude Code 与 Codex 并发，各口径各归各。"""
        for _ in range(3):
            self._feed(_row(12000, 900, "responses"))   # Codex 跑大任务
            self._feed(_row(300, 30, "anthropic"))      # Claude 跑小任务
        slot = self.store.summary()["A"]
        self.assertEqual(slot["scopes"]["responses"]["requests"], 3)
        self.assertEqual(slot["scopes"]["anthropic"]["requests"], 3)
        self.assertEqual(slot["scopes"]["responses"]["tokens"], 3 * 12900)
        self.assertEqual(slot["scopes"]["anthropic"]["tokens"], 3 * 330)


if __name__ == "__main__":
    unittest.main()
