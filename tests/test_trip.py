# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Token 小计（TRIP A / B）——与既有统计口径同源的分段计数器。

这一组用例对着验收标准写，重点不在"数字对不对"，而在四个容易静默出错的地方：

* 重启后从锚点重扫，**不能重复累加**（重复了没人看得出来）；
* 日志轮转后归档换了名字，**不能重算一遍**（小计会凭空翻倍）；
* 清零只清一段，**日总量与历史日志一行不动**；
* 小计口径必须与 `today()` 逐字一致，否则两处数字对不上时无法判断谁错。
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from records import ActivityLog  # noqa: E402
from trips import TripStore  # noqa: E402

PROFILE = {"id": "trip-test", "provider": "openai",
           "provider_name": "示例中转", "model": "gpt-6-astra"}


def _add(log, incoming, outgoing, status=200):
    log.add(profile=PROFILE, elapsed=1.0, status=status,
            input_tokens=incoming, output_tokens=outgoing)


class TripCounterTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="microglow-relay-trip-"))

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    # ------------------------------------------------------------ 基本口径

    def test_both_trips_start_at_zero_and_accumulate_together(self):
        log = ActivityLog(self.directory)
        self.assertEqual(log.trip_summary()["A"]["tokens"], 0)
        self.assertEqual(log.trip_summary()["B"]["tokens"], 0)
        for incoming, outgoing in ((100, 10), (200, 20), (300, 30)):
            _add(log, incoming, outgoing)
        for key in ("A", "B"):
            trip = log.trip_summary()[key]
            self.assertEqual(trip["input_tokens"], 600)
            self.assertEqual(trip["output_tokens"], 60)
            self.assertEqual(trip["tokens"], 660)
            self.assertEqual(trip["requests"], 3)

    def test_totals_match_existing_usage_definition(self):
        """小计口径必须等于 today()：同一条记录的 input+output，不另立算法。"""
        log = ActivityLog(self.directory)
        for incoming, outgoing in ((1_204, 318), (87_650, 2_509), (0, 47)):
            _add(log, incoming, outgoing)
        _add(log, 900, 100, status=429)  # 失败的请求也用了上游 token，照样计
        today = log.today()
        trip = log.trip_summary()["A"]
        self.assertEqual(trip["tokens"], today["tokens"])
        self.assertEqual(trip["input_tokens"], today["input_tokens"])
        self.assertEqual(trip["output_tokens"], today["output_tokens"])
        self.assertEqual(trip["requests"], today["requests"])

    def test_failed_requests_still_count_toward_the_trip(self):
        log = ActivityLog(self.directory)
        _add(log, 500, 0, status=503)
        self.assertEqual(log.trip_summary()["A"]["tokens"], 500)

    # ---------------------------------------------------------------- 清零

    def test_reset_zeroes_one_trip_and_keeps_the_other(self):
        log = ActivityLog(self.directory)
        for _ in range(3):
            _add(log, 100, 10)
        log.reset_trip("A")
        summary = log.trip_summary()
        self.assertEqual(summary["A"]["tokens"], 0)
        self.assertEqual(summary["A"]["requests"], 0)
        self.assertEqual(summary["B"]["tokens"], 330)

    def test_requests_after_reset_only_reach_the_new_segment(self):
        log = ActivityLog(self.directory)
        for _ in range(3):
            _add(log, 100, 10)
        log.reset_trip("A")
        time.sleep(0.02)          # 让清零时刻与下一条记录的时间戳明确分开
        _add(log, 500, 50)
        summary = log.trip_summary()
        self.assertEqual(summary["A"]["tokens"], 550)
        self.assertEqual(summary["B"]["tokens"], 880)

    def test_reset_leaves_daily_totals_and_history_untouched(self):
        log = ActivityLog(self.directory)
        for _ in range(4):
            _add(log, 100, 10)
        before_today = log.today()["tokens"]
        before_rows = len(log.recent(100))
        log.reset_trip("A")
        log.reset_trip("B")
        self.assertEqual(log.today()["tokens"], before_today)
        self.assertEqual(len(log.recent(100)), before_rows)
        self.assertEqual(before_today, 440)

    def test_reset_rejects_unknown_segment(self):
        log = ActivityLog(self.directory)
        with self.assertRaises(ValueError):
            log.reset_trip("C")

    # ------------------------------------------------------- 持久化与重启

    def test_counts_survive_restart_without_double_counting(self):
        log = ActivityLog(self.directory)
        for _ in range(5):
            _add(log, 100, 10)
        log.trips.flush()
        reopened = ActivityLog(self.directory)
        trip = reopened.trip_summary()["A"]
        self.assertEqual(trip["tokens"], 550)
        self.assertEqual(trip["requests"], 5)

    def test_counts_are_rebuilt_when_process_died_before_flush(self):
        """落盘有节流：被杀时文件里的锚点落后，重开必须补齐而不是从零或翻倍。"""
        log = ActivityLog(self.directory)
        for _ in range(6):
            _add(log, 100, 10)
        # 故意不 flush，直接换一个实例读同一目录
        reopened = ActivityLog(self.directory)
        trip = reopened.trip_summary()["A"]
        self.assertEqual(trip["tokens"], 660)
        self.assertEqual(trip["requests"], 6)

    def test_reset_moment_survives_restart(self):
        log = ActivityLog(self.directory)
        for _ in range(3):
            _add(log, 100, 10)
        log.reset_trip("B")
        _add(log, 70, 7)
        log.trips.flush()
        reopened = ActivityLog(self.directory)
        summary = reopened.trip_summary()
        self.assertEqual(summary["A"]["tokens"], 407)
        self.assertEqual(summary["B"]["tokens"], 77)
        self.assertGreater(summary["B"]["reset_at"], summary["A"]["reset_at"])

    def test_timer_starts_at_the_first_call_after_reset_not_at_reset(self):
        """计时触发条件：清零键只归零，秒表在本段第一笔调用入账时才启动。"""
        log = ActivityLog(self.directory)
        for _ in range(2):
            _add(log, 100, 10)
        log.reset_trip("A")
        # 清零后、第一笔调用之前：计时未启动，elapsed 必须是 None，不是 0。
        self.assertIsNone(log.trip_summary()["A"]["elapsed"])
        self.assertIsNone(log.trip_summary()["A"]["started_at"])
        before = time.time()
        _add(log, 100, 10)
        trip = log.trip_summary()["A"]
        self.assertIsNotNone(trip["started_at"])
        self.assertGreaterEqual(trip["started_at"], before - 1.0)
        self.assertLess(trip["elapsed"], 5.0)
        # B 段一直在跑：起点是它自己的第一笔，不是 A 的清零时刻。
        self.assertIsNotNone(log.trip_summary()["B"]["elapsed"])

    def test_timer_start_uses_the_rows_timestamp_when_backfilling(self):
        """补账重扫时，计时起点必须是那一笔真实发生的时间，不是补账的墙钟。"""
        log = ActivityLog(self.directory)
        log.trips.flush()
        two_hours_ago = time.time() - 7200
        row = {"timestamp": two_hours_ago, "time": "2026-10-27 07:00:00",
               "profile_id": "p", "provider": "x", "model": "m", "status": 200,
               "ok": True, "elapsed": 1.0, "input_tokens": 50, "output_tokens": 5}
        log.path.write_bytes((json.dumps(row) + "\n").encode("utf-8"))
        state = log.trips._state
        for trip in state["trips"].values():
            trip["reset_at"] = two_hours_ago - 60  # 清零早于这一笔
        state["anchor"].clear()
        log.trips._save()

        reopened = ActivityLog(self.directory)
        trip = reopened.trip_summary()["A"]
        self.assertEqual(trip["started_at"], two_hours_ago)
        self.assertGreaterEqual(trip["elapsed"], 7200 - 5)

    def test_timer_start_survives_restart_and_reset_clears_it(self):
        log = ActivityLog(self.directory)
        _add(log, 100, 10)
        log.trips.flush()
        reopened = ActivityLog(self.directory)
        self.assertIsNotNone(reopened.trip_summary()["A"]["started_at"])
        reopened.reset_trip("A")
        self.assertIsNone(reopened.trip_summary()["A"]["elapsed"])
        # 重启后仍是"未开始"：清零状态要落盘，不能重启后凭空开始计时。
        reopened.trips.flush()
        self.assertIsNone(ActivityLog(self.directory).trip_summary()["A"]["elapsed"])

    def test_legacy_state_without_started_at_falls_back_to_reset_at(self):
        """v1 状态文件升级 v2：分桶从日志重扫重建，清零时刻保留。

        v1 段没有按协议分桶，旧计数有意丢弃——真值在日志里，保留 reset_at
        意味着重开实例的全量重扫会把每一桶精确重建，读数回到应有水平。
        """
        log = ActivityLog(self.directory)
        for _ in range(3):
            _add(log, 100, 10)
        log.trips.flush()
        # 把状态文件改写回 v1 形状（无 by_client / scope，扁平计数）
        legacy = {"version": 1,
                  "trips": {key: {"reset_at": state_trip["reset_at"],
                                  "started_at": None,
                                  "input_tokens": 330, "output_tokens": 33,
                                  "requests": 3}
                            for key, state_trip in log.trips._state["trips"].items()},
                  "anchor": dict(log.trips._state["anchor"])}
        log.trips.path.write_text(json.dumps(legacy, ensure_ascii=False),
                                  encoding="utf-8")

        reopened = ActivityLog(self.directory)
        trip = reopened.trip_summary()["A"]
        # 旧计数（330/33/3 是随手写的假数）被丢弃，由重扫从日志精确重建：
        # 三笔 × (100 入 + 10 出)，无 client 字段全落 responses 桶。
        self.assertEqual(trip["input_tokens"], 300)
        self.assertEqual(trip["output_tokens"], 30)
        self.assertEqual(trip["requests"], 3)
        self.assertEqual(trip["scopes"]["responses"]["tokens"], 330)
        self.assertEqual(trip["scopes"]["anthropic"]["tokens"], 0)
        self.assertIsNotNone(trip["started_at"])

    # ---------------------------------------------------------- 轮转与并发

    def test_rotation_does_not_recount_archived_rows(self):
        log = ActivityLog(self.directory)
        log._rotate_bytes = 300        # 逼它频繁轮转
        for _ in range(12):
            _add(log, 100, 10)
        self.assertGreater(len(list(self.directory.glob("*.jsonl"))), 1)
        self.assertEqual(log.trip_summary()["A"]["tokens"], 1_320)
        log.trips.flush()
        reopened = ActivityLog(self.directory)
        self.assertEqual(reopened.trip_summary()["A"]["tokens"], 1_320)

    def test_concurrent_writes_are_not_lost(self):
        log = ActivityLog(self.directory)

        def worker():
            for _ in range(25):
                _add(log, 10, 1)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        trip = log.trip_summary()["A"]
        self.assertEqual(trip["requests"], 200)
        self.assertEqual(trip["tokens"], 2_200)
        log.trips.flush()
        self.assertEqual(ActivityLog(self.directory).trip_summary()["A"]["tokens"], 2_200)

    # -------------------------------------------------- 跨自然日 / 容错

    def test_a_new_calendar_day_does_not_reset_the_trip(self):
        """跨自然日不清零：小计只认清零时刻，不认日界。

        先把清零时刻挪到两天前，再放一条"昨天"的记录进去——它必须计入小计，
        同时**不能**计入今日总量。这两件事一起才能证明"只差在日界，不差在清零"。
        """
        log = ActivityLog(self.directory)
        log.trips.flush()
        yesterday = time.time() - 26 * 3600
        row = {"timestamp": yesterday, "time": "2026-10-20 10:00:00",
               "profile_id": "p", "provider": "x", "model": "m", "status": 200,
               "ok": True, "elapsed": 1.0, "input_tokens": 400, "output_tokens": 40}
        log.path.write_bytes((json.dumps(row) + "\n").encode("utf-8"))
        state = log.trips._state
        for trip in state["trips"].values():
            trip["reset_at"] = time.time() - 2 * 86400
        state["anchor"].clear()          # 逼它整体重扫
        log.trips._save()

        reopened = ActivityLog(self.directory)
        self.assertEqual(reopened.trip_summary()["A"]["tokens"], 440)
        self.assertEqual(reopened.today()["tokens"], 0)
        # 计时从那笔"昨天"的调用起算（≈26 小时），不是从两天前的清零时刻起算。
        elapsed = reopened.trip_summary()["A"]["elapsed"]
        self.assertGreaterEqual(elapsed, 26 * 3600 - 5)
        self.assertLess(elapsed, 2 * 86400)

    def test_broken_log_file_never_raises(self):
        log = ActivityLog(self.directory)
        log.path.write_bytes(b"{not json}\n\x00\x01\n")
        _add(log, 10, 1)
        summary = log.trip_summary()
        self.assertIn("A", summary)
        self.assertEqual(summary["A"]["requests"], 1)

    def test_corrupt_state_file_falls_back_to_fresh_counters(self):
        log = ActivityLog(self.directory)
        _add(log, 10, 1)
        log.trips.flush()
        TripStore.log_name = "microglow-relay-usage.jsonl"
        log.trips.path.write_text("{ this is not json", encoding="utf-8")
        reopened = TripStore(self.directory, log_name="microglow-relay-usage.jsonl")
        summary = reopened.summary()
        self.assertEqual(summary["A"]["tokens"], 0)
        self.assertEqual(summary["B"]["tokens"], 0)

    def test_anchor_does_not_skip_rows_written_by_another_instance(self):
        """另一个临时实例写过日志：锚点对不上时宁可不记，等 sync 顺序补，不能跳记。"""
        log = ActivityLog(self.directory)
        _add(log, 100, 10)
        log.trips.flush()
        # 第二个实例（load=False，常见于连接测试）往同一个日志里追加一行
        probe = ActivityLog(self.directory, load=False)
        _add(probe, 250, 25)
        log.trips.flush()
        reopened = ActivityLog(self.directory)
        self.assertEqual(reopened.trip_summary()["A"]["tokens"], 385)


if __name__ == "__main__":
    unittest.main()
