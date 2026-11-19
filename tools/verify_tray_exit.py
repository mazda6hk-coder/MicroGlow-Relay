"""Isolated real Qt event-loop exit check. Never starts a model request or opens user data."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("offscreen", "windows"), default="offscreen")
    parser.add_argument("--exit-option", choices=("disabled", "success", "failure"), default="disabled")
    args = parser.parse_args()
    os.environ["QT_QPA_PLATFORM"] = args.platform
    with tempfile.TemporaryDirectory(prefix="relay-exit-check-") as directory:
        os.environ["CODEX_HOME"] = str(Path(directory) / "empty-codex")
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from app.bridge import Bridge
        from app.window import Shell
        from server import Gateway
        from storage import Settings
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        settings = Settings(Path(directory) / "data")
        gateway = Gateway(settings)
        gateway.start(0)
        bridge = Bridge(settings, gateway)
        calls = []
        if args.exit_option != "disabled":
            bridge.session_compatibility.save_options(exit_login=True)

            def on_exit():
                calls.append("exit")
                if args.exit_option == "failure":
                    raise RuntimeError("Synthetic exit failure")
                return {"state": "disabled"}
            bridge.session_compatibility.on_exit = on_exit
        shell = Shell(bridge)
        shell.show()
        began = time.monotonic()

        def trigger():
            if shell._tray is not None:
                print("Trigger: actual tray Quit action", flush=True)
                shell._tray.contextMenu().actions()[-1].trigger()
            else:
                print("Trigger: shell Quit handler (no system tray on this platform)", flush=True)
                shell.quit()

        def timeout():
            print(f"FAIL exit timed out: window_visible={shell.isVisible()}, gateway_running={gateway.running}", flush=True)
            app.exit(124)
        QTimer.singleShot(100, trigger)
        QTimer.singleShot(6000, timeout)
        result = app.exec()
        stopped = not gateway.running
        print(f"exit_code={result}, elapsed={time.monotonic() - began:.3f}s, gateway_stopped={stopped}, exit_calls={len(calls)}", flush=True)
        gateway.stop()
        return result or (0 if stopped else 1)


if __name__ == "__main__":
    raise SystemExit(main())
