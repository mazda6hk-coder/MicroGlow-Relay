"""把 Relay 已写入的 Codex 供应商表纠正为 ``requires_openai_auth = true``。

用途
----
0.8 及更早版本的 Relay 每次「接入」都会把这一项写成 ``false``。Codex 因此
不加载 ChatGPT 账号身份（``getAuthStatus`` 返回 ``authMethod = null``），
桌面端账号上下文 ``owner`` 为空，原生项目分组整组沉进「非激活账号」桶，
表现就是「项目分组消失、会话没有项目归属」。

新版本源码已改正（``codex_config.provider_config``），但在旧包还在跑的时候
可以用这个脚本救急：只改这一项，其它键原样保留。

同时会把接入凭据里的供应商快照同步过去。**这一步不能省**：只改 config 不改
凭据，界面会把配置判成 drifted，你再点一下「让 Codex 使用 Relay」的开关，
旧版会立刻把 ``false`` 写回来。

用法::

    python tools/fix_codex_auth.py
    python tools/fix_codex_auth.py --data-dir "C:\\Users\\你\\AppData\\Local\\MicroGlow Relay\\data"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from datetime import datetime
from pathlib import Path

import tomlkit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codex_config import PROVIDER_ID, receipt_path  # noqa: E402
from storage import atomic_write  # noqa: E402


def default_config() -> Path:
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return home / "config.toml"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="纠正 Codex 接入配置里的 requires_openai_auth")
    parser.add_argument("--data-dir", type=Path,
                        default=Path(os.environ.get("LOCALAPPDATA", ""))
                        / "MicroGlow Relay" / "data")
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args(argv)

    target = args.config or default_config()
    if not target.exists():
        print(f"找不到 Codex 配置文件：{target}")
        return 2

    raw = target.read_text(encoding="utf-8-sig")
    document = tomlkit.parse(raw)
    providers = document.get("model_providers")
    table = providers.get(PROVIDER_ID) if isinstance(providers, dict) else None
    if table is None:
        print(f"{target} 里没有 [{PROVIDER_ID}]，说明 Codex 当前没接入 Relay。先接入再跑本脚本。")
        return 3

    before = table.get("requires_openai_auth")
    table["requires_openai_auth"] = True
    output = tomlkit.dumps(document)
    live = tomllib.loads(output)["model_providers"][PROVIDER_ID]

    recorder = receipt_path(type("S", (), {"directory": args.data_dir})()) \
        if args.data_dir.exists() else None
    receipt = None
    if recorder is not None and recorder.exists():
        try:
            receipt = json.loads(recorder.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            receipt = None

    provider_changed = before is not True
    receipt_changed = bool(receipt) and receipt.get("provider") != live
    if not provider_changed and not receipt_changed:
        print("已是最新：config.toml 与接入凭据都已经是 requires_openai_auth = true，无需改动。")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if provider_changed:
        atomic_write(target.with_name(f"config.toml.bak-fixauth-{stamp}"), raw)
        atomic_write(target, output)
        print(f"config.toml：requires_openai_auth {before} -> True")

    if receipt_changed:
        atomic_write(recorder.with_name(f"{recorder.name}.bak-fixauth-{stamp}"),
                     recorder.read_text(encoding="utf-8"))
        receipt["provider"] = live
        atomic_write(recorder, json.dumps(receipt, ensure_ascii=False, indent=2))
        print("接入凭据：供应商快照已同步（不会再被判成 drifted）")

    print("完成。重启 Codex 生效。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
