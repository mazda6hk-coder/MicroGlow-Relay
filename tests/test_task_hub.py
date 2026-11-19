"""MG-RELAY-TASKHUB-001: worker 结果必须回主线程派发。

背景：任务（拉模型、连接测试）比页面活得久。旧的「每任务一对信号」写法
下，worker 线程会在页面销毁后直接调用裸 lambda 回调——C++ 侧没有 receiver
可自动断连，进程级段错误（UI 批量测试里稳定复现在第 22 个用例之后）。

本测试锁住三条性质：
1. 回调在主线程执行（不在 worker 线程）；
2. 失败走 on_error，成功走 on_done，互不串门；
3. 回调绑定的控件已销毁时，结果被安全丢弃，不抛异常、不崩。
"""
from __future__ import annotations

import os
import sys
import threading
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
for _path in (str(ROOT), str(ROOT / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from PySide6.QtCore import QThread  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from app.bridge import Task, task_hub  # noqa: E402


def _pump(app: QApplication, rounds: int = 60) -> None:
    for _ in range(rounds):
        app.processEvents()


class TaskHubTests(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.hub = task_hub()
        self.main_thread = QThread.currentThread()

    def _run(self, payload, on_done=None, on_error=None):
        Task(payload, {"finished": [on_done] if on_done else [],
                       "failed": [on_error] if on_error else []}).run()

    def test_callback_runs_on_main_thread(self):
        """回调必须在主线程执行：这是消除跨线程调用已析构控件的关键。"""
        seen = {}

        def done(value):
            seen["value"] = value
            seen["thread"] = QThread.currentThread()

        # 直接在"worker 线程"里跑：另起一个 Python 线程模拟线程池。
        worker = threading.Thread(target=lambda: self._run(lambda: 41 + 1, done))
        worker.start()
        worker.join()
        _pump(self.app)

        self.assertEqual(seen.get("value"), 42)
        self.assertIs(seen.get("thread"), self.main_thread)

    def test_failure_goes_to_error_callback_only(self):
        seen = {"ok": [], "error": []}

        def boom():
            raise ValueError("upstream down")

        self._run(boom,
                  on_done=lambda value: seen["ok"].append(value),
                  on_error=lambda error: seen["error"].append(error))
        _pump(self.app)

        self.assertEqual(seen["ok"], [])
        self.assertEqual(len(seen["error"]), 1)
        self.assertIsInstance(seen["error"][0], ValueError)

    def test_callback_bound_to_deleted_widget_is_safe(self):
        """控件已销毁：回调里碰它是安全的，别的回调照常收到结果。

        本机 PySide6 对已删控件的方法调用是静默忽略（不抛错）；即便某个
        版本抛 RuntimeError，中枢 _deliver 也会吞掉。两种行为下结果一致：
        不崩、不阻塞后续回调。
        """
        label = QLabel("temp")
        label.deleteLater()
        _pump(self.app)
        received = []

        def touch_deleted(value):
            try:
                label.setText(str(value))
            except RuntimeError:      # 版本差异：抛错也属正常
                pass

        self._run(lambda: 7, lambda v: (touch_deleted(v), received.append(v)))
        _pump(self.app)

        self.assertEqual(received, [7])

    def test_callback_exception_does_not_poison_event_loop(self):
        """回调抛运行时异常：打印后继续，同一任务的后续回调照常执行。"""
        import builtins

        log, printed = [], []

        def boom(value):
            raise ValueError("callback bug")

        real_print = builtins.print
        builtins.print = lambda *args, **kwargs: printed.append(args)
        try:
            Task(lambda: 1, {"finished": [boom, log.append],
                             "failed": []}).run()
            _pump(self.app)
        finally:
            builtins.print = real_print

        self.assertEqual(log, [1], "抛错的那个回调不应阻断后续回调")
        self.assertTrue(printed, "异常要打印出来，便于排障")


if __name__ == "__main__":
    unittest.main()
