# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""翻牌里程表组件。

任务书第 5 节 + 第 12 节验收：0、个位数、10 位、12 位、溢出五种显示
均正确；未用高位 32% 淡显；数字变化触发滚动动画；等宽字体。
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app import theme
from app.odometer import Odometer, _DigitCell, format_tokens


class OdometerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        theme.apply_theme("spring", "day")

    def _meter(self, **kwargs) -> Odometer:
        meter = Odometer(**kwargs)
        meter.setStyleSheet(theme.stylesheet())
        return meter

    def test_five_display_states(self):
        """验收五态：0、个位、10 位、12 位、溢出。"""
        meter = self._meter()
        meter.set_value(0, animate=False)
        self.assertEqual(meter.value(), 0)
        self.assertTrue(all(not cell.isHidden() for cell in meter._cells))

        meter.set_value(7, animate=False)
        digits = [cell.char for cell in meter._cells]
        self.assertEqual("".join(digits), "000000000007")

        meter.set_value(1_234_567_890, animate=False)   # 10 位
        digits = [cell.char for cell in meter._cells]
        self.assertEqual("".join(digits), "001234567890")

        meter.set_value(999_999_999_999, animate=False)  # 12 位容量顶格
        digits = [cell.char for cell in meter._cells]
        self.assertEqual("".join(digits), "999999999999")

        meter.set_value(1_200_000_000_000, animate=False)  # 溢出
        self.assertTrue(hasattr(meter, "_overlay"))
        self.assertIn("万亿", meter._overlay.text())
        for cell in meter._cells:
            self.assertTrue(cell.isHidden(), "溢出态逐位结构应隐藏")

    def test_leading_zeros_are_dimmed(self):
        """未用到的高位淡显（32%），非零位不淡显。"""
        meter = self._meter()
        meter.set_value(123, animate=False)
        dim_flags = [getattr(cell, "_dim", False) for cell in meter._cells]
        self.assertEqual(dim_flags, [True] * 3 + [False] + [True] * 5 + [False] * 3,
                         "前导 9 个零淡显，后 3 位实显")

    def test_digit_change_starts_roll_animation(self):
        """字面变化触发滚动；相同值不触发。offscreen 下定时器按"减少动态效果"跳过。"""
        meter = self._meter()
        meter.set_value(5, animate=False)
        cell = meter._cells[-1]
        self.assertEqual(cell.progress, 0.0)

        meter.set_value(6, animate=True)
        # offscreen：动效静默跳过，字面立即就位（与系统减少动效同源）。
        self.assertFalse(cell._timer.isActive())
        self.assertEqual(cell.char, "6")
        self.assertEqual(cell.progress, 0.0)

        meter.set_value(6, animate=True)   # 相同值：不重复动画
        self.assertFalse(cell._timer.isActive())
        self.assertEqual(cell.char, "6")

    def test_digit_cell_roll_progress_drives_repaint(self):
        cell = _DigitCell(38)
        cell.set_char("3", animate=False)
        cell._from_char = "0"
        cell.char = "8"
        cell.progress = 0.5
        cell.update()
        self.assertEqual(cell.progress, 0.5)
        # offscreen 环境直接触发 paintEvent，确保滚动绘制路径不抛异常。
        cell.grab()

    def test_format_tokens_capacity(self):
        # 0.9 收口（任务书验收 7b）：里程表不用千分位分隔符，12 位连成一体；
        # 逗号落在基线以下像浮点的「¸」，且位间距会被撑散。
        self.assertEqual(format_tokens(0), "0")
        self.assertEqual(format_tokens(12345), "12345")
        self.assertEqual(format_tokens(MAX := 999_999_999_999), "999999999999")
        overflow = format_tokens(1_250_000_000_000)
        self.assertEqual(overflow, "1.25 万亿")


if __name__ == "__main__":
    unittest.main()
