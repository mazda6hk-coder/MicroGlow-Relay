# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for MicroGlow Relay 1.3 (Windows).

Slim build: only QtCore/QtGui/QtWidgets/QtSvg are imported by the app;
everything else in the Qt distribution is excluded up front.
"""
from pathlib import Path


ROOT = Path.cwd()
EXCLUDES = [
    "numpy", "tkinter", "pystray", "PIL",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtSql",
    "PySide6.QtTest", "PySide6.QtDesigner",
    "PySide6.QtNetwork", "PySide6.QtConcurrent", "PySide6.QtOpenGL",
    "PySide6.QtDBus", "PySide6.QtPrintSupport", "PySide6.QtStateMachine",
    "PySide6.QtSvgWidgets", "PySide6.QtUiPlugin", "PySide6.QtQuickWidgets",
    "PySide6.QtPdf", "PySide6.QtWebSockets", "PySide6.QtBluetooth",
    "PySide6.QtNfc", "PySide6.QtSerialPort", "PySide6.QtPositioning",
    "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtWebChannel",
    "PySide6.QtTextToSpeech", "PySide6.QtDataVisualization",
    "PySide6.Qt3DCore", "PySide6.Qt3DLogic", "PySide6.Qt3DInput",
    "PySide6.Qt3DRender", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
]

a = Analysis(
    [str(ROOT / "runapp.py")],
    pathex=[str(ROOT / "src"), str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / "assets" / "microglow-logo.png"), "assets"),
           # 只收 ui-final 根层贴图；relay-design-01 是设计原稿目录，不随 EXE 分发。
           *[(str(path), "assets/ui-final")
             for path in sorted((ROOT / "assets" / "ui-final").glob("*.png"))],
           (str(ROOT / "assets" / "fonts" / "source-sans-3" / "SourceSans3-Bold.ttf"),
            "assets/fonts/source-sans-3"),
           (str(ROOT / "assets" / "openai-mark.svg"), "assets"),
           (str(ROOT / "assets" / "simple-icons-LICENSE.txt"), "assets"),
           (str(ROOT / "assets" / "model-brands"), "assets/model-brands"),
           # 只打包 DISPLAY_ORDER（即 THEME_ORDER）内的主题预览；black/white/ios/
           # cyberpunk/gold 是旧主题键的遗留图（LEGACY_THEME_MAP 已重定向），不随 EXE 分发。
           *[(str(ROOT / "assets" / "theme-previews" / f"{key}.png"), "assets/theme-previews")
             for key in ("springmagnolia", "mistblue", "graphite", "microglow", "nightfall",
                         "goldglow", "moonwhite", "starpark")],
           (str(ROOT / "docs" / "USER-GUIDE.md"), "docs"),
           (str(ROOT / "docs" / "USER-AGREEMENT.md"), "docs"),
           (str(ROOT / "docs" / "PRIVACY-POLICY.md"), "docs"),
           (str(ROOT / "docs" / "THIRD-PARTY-NOTICES.md"), "docs"),
           (str(ROOT / "docs" / "licenses"), "docs/licenses"),
           (str(ROOT / "assets" / "microglow-icon-idle.png"), "assets"),
           (str(ROOT / "assets" / "microglow-icon-transfer.png"), "assets"),
           (str(ROOT / "src" / "telemetry" / "official_api_hosts.json"), "telemetry"),
           # 原生直通用的完整目录快照（含系统提示词）；刻意不进 PYZ，
           # 由 native_models.native_catalog() 按 _MEIPASS 读取。
           (str(ROOT / "src" / "native_catalog.json.gz"), ".")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=2,
)

# ICU 由 Windows 自带 CRL 提供，剔除可省数十 MB 且避免 DLL 冲突。
a.binaries = [
    entry for entry in a.binaries
    if Path(entry[0]).name.casefold() not in {"icuuc.dll", "icudt78.dll"}
]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MicroGlow-Relay-1.3",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(ROOT / "tools" / "windows_version_1_3.py"),
    icon=[str(ROOT / "assets" / "app.ico")],
)
