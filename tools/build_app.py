"""Build MicroGlow Relay into a single Windows executable.

Usage (from the project root)::

    python tools/build_app.py

A PowerShell wrapper is provided as ``build-app.ps1``.  The build logic lives in
Python so Chinese paths and the executable name survive every Windows code page.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / "work" / "venv" / "Scripts" / "python.exe"
sys.path.insert(0, str(ROOT / "src"))
from storage import VERSION  # noqa: E402 - build name follows the application version

EXE_NAME = f"MicroGlow-Relay-{VERSION}"


def run(arguments: list[str]) -> None:
    print("$ " + " ".join(arguments), flush=True)
    result = subprocess.run(arguments, cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit(f"命令失败（退出码 {result.returncode}）：{arguments[0]}")


def interpreter() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    run([sys.executable, "-m", "venv", str(ROOT / "work" / "venv")])
    return str(VENV_PYTHON)


def main() -> int:
    python = interpreter()
    run([python, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt"),
         "-r", str(ROOT / "requirements-app.txt"), "--disable-pip-version-check"])
    run([python, str(ROOT / "tools" / "make_icon.py")])
    run([python, "-m", "unittest", "discover", "-s", str(ROOT / "tests")])

    arguments = [
        python, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--distpath", str(ROOT),
        "--workpath", str(ROOT / "work" / "build-ui3"),
        str(ROOT / f"{EXE_NAME}.spec"),
    ]
    run(arguments)

    target = ROOT / f"{EXE_NAME}.exe"
    if not target.exists():
        raise SystemExit("构建结束但没有找到可执行文件。")
    print(f"\n交付文件：{target}")
    print(f"文件大小：{target.stat().st_size:,} 字节")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
