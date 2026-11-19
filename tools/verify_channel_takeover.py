# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Record focused gateway regressions separately from prior UI tasks."""
from pathlib import Path
import sys
import verify_ui_final
verify_ui_final.OUTPUT=Path(__file__).resolve().parents[1]/'work/ROUTE-FAILOVER-003/verification'
if len(sys.argv)==1:
    sys.argv+=['test_channel_takeover.py','test_channels.py','test_router.GatewayTests',
               'test_router.RetryPolicyTests','test_mitigation.py','test_claude_inbound.py',
               'test_request_model_trace.py','test_ui_final.py','test_ui_refine.py']
raise SystemExit(verify_ui_final.main())
