# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Package bootstrap.

The reusable core lives in ``src`` as plain top-level modules.  When running
from source it is appended to ``sys.path``; inside the frozen executable
PyInstaller already collected those modules.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if not getattr(sys, "frozen", False) and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

__all__ = ["ROOT", "SRC"]
