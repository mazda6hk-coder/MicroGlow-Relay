from pathlib import Path
import sys
import verify_ui_final

verify_ui_final.OUTPUT=Path(__file__).resolve().parents[1]/'work/UI-LANGUAGE-004/verification'
if len(sys.argv)==1:
    sys.argv+=['test_language_popup.py','test_ui_refine.py','test_ui_final.py','test_i18n.py']
raise SystemExit(verify_ui_final.main())
