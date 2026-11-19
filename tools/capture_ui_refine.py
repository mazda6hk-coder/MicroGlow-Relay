# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Eight-language review and optional native UI with isolated synthetic data."""
from pathlib import Path
import argparse
import json
import os
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'tools')]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--language', default='zh-CN')
    args = parser.parse_args()
    os.environ['QT_QPA_PLATFORM'] = 'windows' if args.native else 'offscreen'
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QLabel, QAbstractButton
    from app import theme
    from app.i18n import LANGUAGE_CHOICES
    from app.window import Shell
    from capture_ui_final import build_fixture
    app = QApplication([])
    theme.apply_palette('winter-day'); app.setStyleSheet(theme.stylesheet())
    base = Path(tempfile.gettempdir())/'relay-captures'; base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='capture-', dir=base) as temporary:
        directory = Path(temporary)
        os.environ['CODEX_HOME'] = str(directory / 'codex')
        os.environ['CLAUDE_CONFIG_DIR'] = str(directory / 'claude')
        settings, gateway, bridge = build_fixture(directory)
        settings.data['auto_update'] = False; settings.save()
        with patch.object(bridge, 'status', return_value='active'), patch.object(bridge, 'claude_status', return_value='none'):
            gateway.start(0)
            shell = Shell(bridge); shell.resize(1340,900); shell.show()
            if args.native:
                shell.setWindowTitle('MicroGlow Relay · ')
                shell.apply_language(args.language)
                app.exec()
            else:
                output = ROOT / 'docs//screenshots'; output.mkdir(parents=True,exist_ok=True)
                written, clipping, clipped_buttons = [], [], []
                for code, _ in LANGUAGE_CHOICES:
                    shell.apply_language(code)
                    for key, tab, suffix in (('dashboard',None,'01-dashboard'),('models',None,'02-models'),('logs','usage','03-usage'),('logs','trips','04-trips'),('settings',None,'05-settings')):
                        shell.navigate(key)
                        if tab: shell.pages['logs'].show_tab(tab)
                        if key == 'models':
                            shell.pages[key].selected_model = 'deepseek-v4.1-flash'; shell.pages[key].rebuild()
                        if tab == 'trips':
                            shell.pages['logs']._selected_trip=bridge.trip_ledger_entries()[-1]['id']; shell.pages['logs']._refresh_trips()
                        for _ in range(5): app.processEvents()
                        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
                        name=f'{code}-{suffix}.png'; shell.grab().save(str(output/name)); written.append(name)
                        for w in shell.pages[key].findChildren(QLabel):
                            if not w.isVisible() or not w.text() or '<' in w.text() or w.wordWrap(): continue
                            if w.fontMetrics().horizontalAdvance(w.text()) > w.width() + 2:
                                clipping.append(dict(language=code,page=suffix,text=w.text(),width=w.width(),needed=w.fontMetrics().horizontalAdvance(w.text())))
                        for w in shell.pages[key].findChildren(QAbstractButton):
                            if w.isVisible() and w.text() and w.fontMetrics().horizontalAdvance(w.text()) > w.width() - 4:
                                clipped_buttons.append(dict(language=code,page=suffix,text=w.text(),width=w.width(),needed=w.fontMetrics().horizontalAdvance(w.text())))
                shell.apply_language('zh-CN'); shell.resize(1005,675)
                for key,tab,suffix in (('dashboard',None,'01-dashboard'),('models',None,'02-models'),('logs','usage','03-usage'),('logs','trips','04-trips'),('settings',None,'05-settings')):
                    shell.navigate(key)
                    if tab: shell.pages[key].show_tab(tab)
                    for _ in range(4): app.processEvents()
                    name=f'minimum-{suffix}.png'; shell.grab().save(str(output/name)); written.append(name)
                (output/'index.json').write_text(json.dumps(dict(files=written,clipping=clipping,clipped_buttons=clipped_buttons),ensure_ascii=False,indent=2),encoding='utf-8')
                print(json.dumps(dict(screenshots=len(written),clipped_labels=len(clipping),clipped_buttons=len(clipped_buttons)),ensure_ascii=False))
            shell.hide(); shell.deleteLater(); app.processEvents(); gateway.close()

if __name__ == '__main__': main()
