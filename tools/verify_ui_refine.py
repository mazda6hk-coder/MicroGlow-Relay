# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Keep this revision's verification separate from the previous task record."""
from pathlib import Path
import sys
import verify_ui_final

verify_ui_final.OUTPUT = Path(__file__).resolve().parents[1] / 'work//verification'
if len(sys.argv) == 1:
    sys.argv += ['test_ui_refine.py','test_ui_final.py','test_odometer.py','test_i18n.py','test_channel_bridge.py','test_channel_editor.py','test_channels.py']
raise SystemExit(verify_ui_final.main())
