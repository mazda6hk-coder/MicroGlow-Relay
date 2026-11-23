# -*- coding: utf-8 -*-
# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""抓取 Codex 原生模型目录快照 → src/native_catalog.json.gz。

Codex 升级后跑一次：
    python tools/capture_native_catalog.py
默认从 WindowsApps 里找最新的 Codex，也可以显式传 codex.exe 路径。
"""
from __future__ import annotations

import glob
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from native_models import NATIVE_SLUGS  # noqa: E402


def find_codex(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    found = shutil.which("codex")
    if found and found.lower().endswith(".exe"):
        return Path(found)
    # WindowsApps 目录默认不可枚举，只在有权限时兜底。
    pattern = "C:/Program Files/WindowsApps/OpenAI.Codex_*_x64__*/app/resources/codex.exe"
    matches = sorted(glob.glob(pattern), reverse=True)
    if matches:
        return Path(matches[0])
    raise SystemExit(
        "没找到 codex.exe。请显式传入路径，例如：\n"
        "  python tools/capture_native_catalog.py "
        "\"C:/Program Files/WindowsApps/OpenAI.Codex_<版本>_x64__<哈希>/app/resources/codex.exe\""
    )


def main(argv: list[str]) -> int:
    codex = find_codex(argv[1] if len(argv) > 1 else None)
    done = subprocess.run([str(codex), "debug", "models", "--bundled"],
                          capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        raise SystemExit(done.stderr.strip() or "codex debug models 失败。")
    payload = json.loads(done.stdout)
    wanted = set(NATIVE_SLUGS)
    picked = []
    for entry in payload.get("models") or ():
        if entry.get("slug") not in wanted:
            continue
        entry.pop("base_instructions", None)     # 与 instructions_template 重复
        picked.append(entry)
    missing = wanted - {entry["slug"] for entry in picked}
    if missing:
        raise SystemExit("快照里缺少：" + ", ".join(sorted(missing)))
    out = ROOT / "src" / "native_catalog.json.gz"
    raw = json.dumps({"models": picked}, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    with gzip.open(out, "wb", compresslevel=9) as fh:
        fh.write(raw)
    print(f"{len(picked)} models, {len(raw)} raw bytes -> {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
