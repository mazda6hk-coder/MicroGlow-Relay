"""MG-RELAY-THREAD-001: Gateway 生命周期不得泄漏后台线程。

背景：`Gateway(settings)` 默认附带本地聚合线程（microglow-telemetry-local），
旧实现没有任何收尾路径——每个实例留一条永不退出的守护线程，还攥着
各自临时目录里的 SQLite 连接。几十个 UI 用例连跑后，几十条线程挤在
同一进程里反复访问已删目录的文件句柄，是 C 层访问冲突的来源之一。

本测试锁住：close() 之后聚合线程必须退出。
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _path in (str(ROOT), str(ROOT / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from server import Gateway  # noqa: E402
from storage import Settings  # noqa: E402

THREAD_NAME = "microglow-telemetry-local"


class ThreadLeakTests(unittest.TestCase):
    def _gateways_threads(self):
        return [t for t in threading.enumerate()
                if t.name == THREAD_NAME and t.is_alive()]

    def test_close_stops_telemetry_thread(self):
        temporary = Path(tempfile.mkdtemp(prefix="microglow-thread-leak-"))
        settings = Settings(temporary)
        gateway = Gateway(settings, load_activity=False)
        try:
            self.assertTrue(self._gateways_threads(),
                            "默认构造应起一条本地聚合线程")
        finally:
            gateway.close()

        deadline = time.monotonic() + 2.0
        while self._gateways_threads() and time.monotonic() < deadline:
            time.sleep(0.05)
        remaining = self._gateways_threads()
        shutil.rmtree(temporary, ignore_errors=True)

        self.assertEqual(remaining, [], "close() 之后聚合线程必须退出")

    def test_disabled_telemetry_gateway_close_is_tolerated(self):
        """禁遥测的 Gateway：close() 同样要干净返回。"""
        temporary = Path(tempfile.mkdtemp(prefix="microglow-thread-off-"))
        gateway = Gateway(Settings(temporary), with_telemetry=False,
                          load_activity=False)
        gateway.close()
        shutil.rmtree(temporary, ignore_errors=True)
        # 走到这里不抛错即为通过


if __name__ == "__main__":
    unittest.main()
