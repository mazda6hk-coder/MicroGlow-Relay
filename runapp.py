# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Desktop entry point for MicroGlow Relay.

Run from source with::

    python runapp.py

Package into a single binary with::

    .\\build-app.ps1
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
_DLL_DIRECTORY_HANDLES = []
if getattr(sys, "frozen", False) and os.name == "nt":
    # PyInstaller extracts Qt and shiboken into sibling directories.  Register
    # both before importing PySide6 so Windows can resolve their private DLLs.
    bundle_root = Path(getattr(sys, "_MEIPASS", ROOT))
    for relative in ("PySide6", "shiboken6"):
        directory = bundle_root / relative
        if directory.is_dir():
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))
else:
    for path in (str(ROOT), str(SRC)):
        if path not in sys.path:
            sys.path.insert(0, path)

from app.launcher import run  # noqa: E402  (import after sys.path setup)

if __name__ == "__main__":
    raise SystemExit(run())
