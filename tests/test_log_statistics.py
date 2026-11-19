# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Local calendar-period statistics without API or telemetry traffic."""
from datetime import date, datetime
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from records import ActivityLog, calendar_period


class LogStatisticsTests(unittest.TestCase):
    def test_saved_history_all_periods_not_limited_to_memory_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(Path(directory))
            samples = [(2026, 9, 30, 10, True), (2026, 10, 1, 20, False),
                       (2026, 10, 4, 30, True), (2026, 10, 5, 40, True),
                       (2026, 12, 31, 50, False), (2027, 1, 1, 60, True)]
            rows = [dict(timestamp=datetime(y, m, d, 12).timestamp(),
                         input_tokens=tokens - 1, output_tokens=1, ok=ok)
                    for y, m, d, tokens, ok in samples]
            log.path.write_text("\n".join(json.dumps(row) for row in rows) + "\ninvalid\n", encoding="utf-8")
            self.assertEqual(len(log.rows), 0)
            for period, count, tokens, success in (("day", 1, 30, 1), ("week", 3, 60, 2),
                                                   ("month", 3, 90, 2), ("quarter", 4, 140, 2),
                                                   ("year", 5, 150, 3)):
                stats = log.period_summary(period, date(2026, 10, 4))
                self.assertEqual((stats["requests"], stats["tokens"], stats["success"]),
                                 (count, tokens, success))
                self.assertEqual(stats["failures"], count - success)

    def test_explicit_range_is_inclusive_on_both_ends(self):
        """自定义范围必须两端都算进来，否则用户会看到少一天的历史。"""
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(Path(directory))
            samples = [(2026, 9, 30, True), (2026, 10, 1, True), (2026, 10, 3, False),
                       (2026, 10, 5, True)]
            log.path.write_text(
                "\n".join(json.dumps(dict(
                    timestamp=datetime(y, m, d, 12).timestamp(),
                    input_tokens=9, output_tokens=1, ok=ok))
                    for y, m, d, ok in samples) + "\n", encoding="utf-8")
            stats = log.range_summary(date(2026, 10, 1), date(2026, 10, 3))
            self.assertEqual((stats["start"], stats["end"]),
                             (date(2026, 10, 1), date(2026, 10, 3)))
            self.assertEqual((stats["requests"], stats["tokens"], stats["success"]), (2, 20, 1))
            self.assertEqual(stats["failures"], 1)
            # 单日范围等于「日」视图
            one = log.range_summary(date(2026, 10, 5), date(2026, 10, 5))
            self.assertEqual((one["requests"], one["tokens"]), (1, 10))
            # 反向输入不会被当成空区间
            reversed_range = log.range_summary(date(2026, 10, 5), date(2026, 10, 1))
            self.assertEqual(reversed_range["requests"], 3)

    def test_calendar_boundaries_and_leap_year(self):
        self.assertEqual(calendar_period("month", date(2024, 2, 29)),
                         (date(2024, 2, 1), date(2024, 3, 1)))
        self.assertEqual(calendar_period("quarter", date(2026, 12, 31)),
                         (date(2026, 10, 1), date(2027, 1, 1)))
        self.assertEqual(calendar_period("week", date(2027, 1, 1)),
                         (date(2026, 12, 28), date(2027, 1, 4)))

    def test_empty_history(self):
        with tempfile.TemporaryDirectory() as directory:
            stats = ActivityLog(Path(directory)).period_summary("year", date(2026, 10, 4))
            self.assertEqual((stats["requests"], stats["success"], stats["tokens"]), (0, 0, 0))

    def test_model_totals_and_standard_error_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(Path(directory))
            statuses = [200, 401, 403, 429, 408, 504, 502, 503, 400, 422, 500, 524]
            rows = [dict(timestamp=datetime(2026, 10, 4, 12).timestamp(), status=status,
                         ok=status == 200, model=f"model-{index % 3}", input_tokens=10,
                         output_tokens=2) for index, status in enumerate(statuses)]
            log.path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            stats = log.period_summary("day", date(2026, 10, 4))
            self.assertEqual(sum(row["requests"] for row in stats["models"].values()), 12)
            self.assertEqual(sum(row["tokens"] for row in stats["models"].values()), stats["tokens"])
            self.assertEqual(stats["errors"], dict(authentication=2, rate_limit=1, timeout=2,
                                                   unavailable=2, invalid_request=2, other=2))
            self.assertEqual(sum(stats["errors"].values()), stats["failures"])
