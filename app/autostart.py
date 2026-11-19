# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""开机自启（任务书第 8 节）：HKCU Run 项，不写系统级注册表、不要管理员权限。

非 Windows 平台一律视为"不支持"，界面据此把开关灰掉——不假装成功。
"""
from __future__ import annotations

import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "MicroGlow Relay"


def _command() -> str:
    """当前可执行入口：打包后是 exe，源码运行时是 pythonw runapp.py。"""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable)}"'
    root = Path(__file__).resolve().parents[1]
    launcher = root / "runapp.py"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    executable = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{executable}" "{launcher}"'


def supported() -> bool:
    return sys.platform == "win32"


def is_enabled() -> bool:
    if not supported():
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
        return str(value).strip() != ""
    except OSError:
        return False


def set_enabled(enabled: bool) -> bool:
    """写入/删除自启项，返回操作后的真实状态。"""
    if not supported():
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
    except OSError:
        return is_enabled()
    return is_enabled()
