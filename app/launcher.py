"""Qt application bootstrap for the MicroGlow Relay shell."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sys
import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from codex_config import heal_provider_config, receipt_path, restore_native
from server import Gateway
from storage import APP_NAME, VERSION, Settings

from . import icons, theme
from .bridge import Bridge
from .data_paths import migrate_portable_data, resolve_data_directory
from .i18n import set_language, trf
from .window import Shell


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--headless", action="store_true", help="start only the gateway")
    parser.add_argument("--port", type=int)
    parser.add_argument("--smoke-test", action="store_true", help="quit shortly after startup")
    parser.add_argument("--capture", type=Path, help="save a window screenshot and quit (build check)")
    return parser.parse_known_args(argv)[0]


def _single_instance_guard(data_directory: Path):
    """Returns a mutex handle when this is the only instance, otherwise ``None``."""
    if os.name != "nt":
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    identity = hashlib.sha256(str(data_directory).casefold().encode("utf-8")).hexdigest()[:24]
    handle = kernel32.CreateMutexW(None, False, "Local\\MicroGlowRelayUi-" + identity)
    duplicate = ctypes.get_last_error() == 183
    if duplicate:
        ctypes.windll.user32.MessageBoxW(None, trf('{0} 已在运行。', APP_NAME), APP_NAME, 64)
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        if handle:
            kernel32.CloseHandle(handle)
        return None
    return handle


def run(argv=None) -> int:
    args = parse_args(argv)
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    frozen = bool(getattr(sys, "frozen", False))
    data_directory = resolve_data_directory(
        root, args.data_dir, frozen=frozen, windows=os.name == "nt")

    mutex = _single_instance_guard(data_directory)
    if mutex is None:
        return 0

    gateway = None
    bridge = None
    try:
        if frozen and os.name == "nt" and args.data_dir is None:
            migrate_portable_data(root, data_directory)
        settings = Settings(data_directory)
        # 老版本把 requires_openai_auth 写成了 false，升级后就地纠正一次：
        # 否则 Codex 拿不到账号身份，原生项目分组会整组消失。失败不阻断启动。
        try:
            heal_provider_config(settings)
        except Exception:  # noqa: BLE001 - 修配置不能挡住启动
            pass
        gateway = Gateway(settings)

        if args.headless:
            gateway.start(args.port)
            if sys.stdout:
                print(json.dumps({"status": "ready", "port": gateway.port, "version": VERSION},
                                 ensure_ascii=False), flush=True)
            threading.Event().wait()
            return 0

        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        app = QApplication.instance() or QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        if os.name == "nt":
            try:
                # AppUserModelID 必须跨版本稳定（任务栏固定图标按它归组），不随 VERSION 变化。
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MicroGlow.Relay")
            except Exception:  # noqa: BLE001 - cosmetic only
                pass

        bridge = Bridge(settings, gateway)
        set_language(bridge.language())
        theme.apply_theme(bridge.theme().rpartition("-")[0], bridge.day_night_mode())
        theme.install_palette()
        app.setStyleSheet(theme.stylesheet())
        app.setWindowIcon(icons.brand_status_icon())

        bridge.log("success", trf('{0} 已启动', APP_NAME))

        shell = Shell(bridge)
        from .update_controller import UpdateController
        shell.updater = UpdateController(shell, automatic=not (args.capture or args.smoke_test or args.data_dir))
        shell.show()
        if args.capture:
            target = Path(args.capture).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            QTimer.singleShot(1600, lambda: (shell.grab().save(str(target), "PNG"), app.quit()))
        elif args.smoke_test:
            # Exercise the same graceful exit handler as the tray menu, not only
            # the Qt event-loop shortcut (which missed a close-event regression).
            QTimer.singleShot(1500, shell.quit)
        result = app.exec()
        bridge.restore_on_exit()
        try:
            gateway.shutdown()
        except Exception:  # noqa: BLE001 - shutdown must never block
            pass
        return result
    except KeyboardInterrupt:
        if bridge is not None:
            bridge.restore_on_exit()
        elif gateway is not None and receipt_path(gateway.settings).exists():
            restore_native(gateway.settings)
        if gateway is not None:
            gateway.shutdown()
        return 0
    except Exception as error:  # noqa: BLE001 - last-resort feedback dialog
        message = str(error)
        try:
            QMessageBox.critical(None, trf('{0} 启动失败', APP_NAME), message)
        except Exception:  # noqa: BLE001 - nothing else we can do
            ctypes.windll.user32.MessageBoxW(None, message, trf('{0} 启动失败', APP_NAME), 16)
        return 1
    finally:
        if gateway is not None:
            try:
                gateway.stop()
            except Exception:  # noqa: BLE001 - shutdown must never block
                pass
        if mutex and os.name == "nt":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    raise SystemExit(run())
