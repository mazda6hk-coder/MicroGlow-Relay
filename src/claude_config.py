# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Reversible Claude Code integration for MicroGlow Relay.

与 codex_config.py 同构：把 Claude Code 的 `~/.claude/settings.json` 指向本机 Relay，
退出/恢复时按 receipt 精确还原。差别只在载体：Codex 是 TOML，Claude 是 JSON。

管理的键（settings.json）：
* `model`                     —— 默认入口，跟随 Relay 选择
* `env.ANTHROPIC_BASE_URL`    —— 指向本机网关（不带 /v1，Claude Code 自己拼）
* `env.ANTHROPIC_AUTH_TOKEN`  —— 本地随机访问令牌
* `env.ANTHROPIC_SMALL_FAST_MODEL` —— 后台小模型也走默认入口，否则 haiku
  名字打到 Relay 只会换来 404，标题生成这类后台功能会静默坏掉
* `env.ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` —— 2.1 起的三个别名档位，
  不钉住的话 `/model opus|sonnet|haiku` 会解析到 claude-opus-5-5 这类官方名 → 404
* `env.CLAUDE_CODE_MAX_CONTEXT_TOKENS` —— 当前生效模型的输入窗口，随模型切换同步。
  Claude Code 对不认识的模型 id 一律假定 1M 窗口，不声明就会「撑爆了才报错」，
  而不是提前压缩上下文；值取模型配置里的 input_tokens，未设则兜底 128000。

独立选择模型：Claude Code 会话里 `/model <配置id>` 或设置 `"model": "<配置id>"`，
Relay 按与 Codex 相同的规则路由（配置 id → 该配置；默认入口 → 跟随）。
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path

from storage import APP_NAME, ROUTER_MODEL, atomic_write

PROVIDER_ID = "microglow_relay"
STATUS_NONE = "none"
STATUS_ACTIVE = "active"
STATUS_DRIFTED = "drifted"

CONTEXT_WINDOW_KEY = "CLAUDE_CODE_MAX_CONTEXT_TOKENS"
# validate_profile 的默认 input_tokens 也是 128000，两边保持一致。
DEFAULT_CONTEXT_WINDOW = "128000"

ENV_KEYS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_SMALL_FAST_MODEL",
    # Claude Code 2.1 起把「别名档位的解析目标」拆成三个变量，
    # ANTHROPIC_SMALL_FAST_MODEL 已被官方标记为废弃。三个别名（/model opus|sonnet|haiku）
    # 默认解析到 claude-opus-5-5 / claude-sonnet-5-5 / claude-haiku-5-5，
    # 这些名字打到 Relay 只会换来 404，必须一起钉到路由模型上。
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    CONTEXT_WINDOW_KEY,
)
MANAGED_KEYS = ("model",)


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def receipt_path(settings) -> Path:
    return settings.directory / "microglow-relay-claude-receipt.json"


def load_receipt(settings) -> dict | None:
    path = receipt_path(settings)
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def managed_target(settings) -> Path:
    """The Claude Code settings file this installation manages."""
    receipt = load_receipt(settings)
    if receipt and receipt.get("target"):
        return Path(str(receipt["target"]))
    return claude_home() / "settings.json"


def _read_json(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return {}
    try:
        value = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def desired_context_window(settings) -> str:
    """当前生效模型的输入窗口（字符串，env 里只放字符串）。

    取不到（没选模型 / 字段非法）时兜底 128000：宁可提前压缩，
    也不要把 1M 的默认假设留给上游，让请求撑到报错为止。
    """
    try:
        profile = settings.selected()
        value = int(profile.get("input_tokens") or 0)
    except Exception:  # noqa: BLE001 - 没有可用模型就用兜底值
        return DEFAULT_CONTEXT_WINDOW
    return str(value) if value > 0 else DEFAULT_CONTEXT_WINDOW


def applied_values(settings) -> dict:
    """接入时要写入的全部键值（顶层 model + env 六件套）。"""
    snapshot = settings.snapshot()
    return {
        "model": ROUTER_MODEL,
        "env": {
            "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{snapshot['port']}",
            "ANTHROPIC_AUTH_TOKEN": settings.local_token(),
            "ANTHROPIC_SMALL_FAST_MODEL": ROUTER_MODEL,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": ROUTER_MODEL,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": ROUTER_MODEL,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": ROUTER_MODEL,
            CONTEXT_WINDOW_KEY: desired_context_window(settings),
        },
    }


def _readable_token(settings) -> str | None:
    """本地令牌；密钥库被锁/未解锁时返回 None，而不是抛穿整个启动流程。

    Linux 桌面（Secret Service 未解锁）与构建容器（无密钥库）都会走到这里。
    以前 claude_view() 无条件读令牌，一个读不到就抛异常 → UI 启动即失败；
    正确行为是「当作未接入」，让用户还能进设置页重新填 Key。
    """
    try:
        return settings.local_token()
    except Exception:  # noqa: BLE001 - 锁着的密钥库不是启动失败
        return None


def claude_view(settings) -> dict:
    """What Claude Code currently resolves from its settings file."""
    path = managed_target(settings)
    parsed = _read_json(path)
    env = parsed.get("env") if isinstance(parsed.get("env"), dict) else {}
    base_url = str(env.get("ANTHROPIC_BASE_URL") or "")
    expected = f"http://127.0.0.1:{settings.snapshot()['port']}"
    token = _readable_token(settings)
    return {
        "path": path,
        "exists": path.exists(),
        "model": str(parsed.get("model") or ""),
        "base_url": base_url,
        # 指向本路由 = base_url 对上且带了我们的令牌。不比对 SmallFast/Model：
        # 那两个是「默认在哪」，用户改它们不构成脱离 Relay。
        "points_to_router": bool(token)
        and base_url == expected
        and str(env.get("ANTHROPIC_AUTH_TOKEN") or "") == token,
        "context_window": str(env.get(CONTEXT_WINDOW_KEY) or ""),
    }


def integration_status(settings) -> str:
    """``none`` | ``active`` | ``drifted`` — based on the live Claude settings."""
    receipt = load_receipt(settings)
    if receipt is None:
        return STATUS_NONE
    view = claude_view(settings)
    if not view["exists"]:
        return STATUS_DRIFTED
    applied = receipt.get("applied") or {}
    if not applied:
        return STATUS_DRIFTED
    parsed = _read_json(view["path"])
    env = parsed.get("env") if isinstance(parsed.get("env"), dict) else {}
    for key in MANAGED_KEYS:
        if parsed.get(key) != (applied.get(key)):
            return STATUS_DRIFTED
    applied_env = applied.get("env") or {}
    for key in ENV_KEYS:
        # 旧版 receipt 没有后加的键（2.1 的三个别名、上下文窗口）：
        # 缺席即「不归那次接入管」，不能当成漂移，否则升级后一启动就红着告警。
        if key not in applied_env:
            continue
        if env.get(key) != applied_env.get(key):
            return STATUS_DRIFTED
    return STATUS_ACTIVE


def integration_conflicts(settings) -> list[str]:
    """Keys changed outside the router after the last successful integration."""
    receipt = load_receipt(settings)
    if receipt is None:
        return []
    view = claude_view(settings)
    if not view["exists"]:
        return ["settings.json"]
    parsed = _read_json(view["path"])
    applied = receipt.get("applied") or {}
    conflicts = [key for key in MANAGED_KEYS if parsed.get(key) != applied.get(key)]
    env = parsed.get("env") if isinstance(parsed.get("env"), dict) else {}
    applied_env = applied.get("env") or {}
    conflicts.extend(f"env.{key}" for key in ENV_KEYS
                     if key in applied_env and env.get(key) != applied_env.get(key))
    return conflicts


def sync_context_window(settings) -> str | None:
    """把当前生效模型的输入窗口同步进 settings.json，并就地刷新 receipt。

    只对「已接入且仍然生效」的配置动手：接管一个已经漂移的文件属于越权，
    那时应当让漂移告警照常出现，等用户选择重新接入。
    写完后 receipt 的 applied 同步更新，否则我们自己写进去的值
    会在下一次轮询里被当成「用户外部修改」，天天误报漂移。
    返回实际写入的值；没有动作时返回 None。
    """
    receipt = load_receipt(settings)
    if receipt is None:
        return None
    applied = dict(receipt.get("applied") or {})
    applied_env = dict(applied.get("env") or {})
    desired = desired_context_window(settings)
    # 先判状态再判值：外部手改过这个键时状态已经是 drifted，
    # 此时既不该写文件，也不该把 receipt 改成「这就是我们写的」。
    if integration_status(settings) != STATUS_ACTIVE:
        return None
    if applied_env.get(CONTEXT_WINDOW_KEY) == desired:
        return desired              # 已经是这个值，不必再写一次文件
    target = Path(str(receipt.get("target") or managed_target(settings)))
    parsed = _read_json(target)
    if not parsed:
        return None
    env = parsed.get("env") if isinstance(parsed.get("env"), dict) else {}
    document = dict(parsed)
    document["env"] = {**env, CONTEXT_WINDOW_KEY: desired}
    atomic_write(target, json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    applied_env[CONTEXT_WINDOW_KEY] = desired
    applied["env"] = applied_env
    receipt["applied"] = applied
    atomic_write(receipt_path(settings), json.dumps(receipt, ensure_ascii=False, indent=2))
    return desired


def managed_settings_path() -> Path | None:
    """企业级策略文件。Windows 上没有这套约定，直接跳过。"""
    if os.name == "nt":
        return None
    return Path("/etc/claude-code/managed-settings.json")


def _project_candidates(workspace: Path | None = None) -> list[Path]:
    """从工作目录向上找有限几层 `.claude/settings.json`，不扫整盘。"""
    current = Path(workspace or Path.cwd()).resolve()
    found = []
    for _ in range(4):
        found.append(current / ".claude" / "settings.json")
        if current.parent == current:
            break
        current = current.parent
    return found


def high_priority_sources(settings, workspace: Path | None = None) -> list[str]:
    """优先级高于用户级 settings.json、但 Relay 不去改的文件（仅用于提示）。

    遵循 Claude Code 原生优先级：企业策略 > 项目级 > 用户级。
    IT 下发的策略、仓库里签入的项目配置都是别人的地盘，
    越权改写只会让接入看起来成功、实际不生效，还可能把公司策略改坏。
    """
    target = managed_target(settings)
    try:
        resolved_target = target.resolve()
    except OSError:
        resolved_target = target
    found: list[str] = []
    managed = managed_settings_path()
    if managed is not None and managed.exists():
        found.append(str(managed))
    for candidate in _project_candidates(workspace):
        try:
            if not candidate.exists() or candidate.resolve() == resolved_target:
                continue
        except OSError:
            continue
        found.append(str(candidate))
    return found


def integrate(settings, target: Path | None = None, force: bool = False) -> Path:
    """Point Claude Code at this router. Backs up the live file first."""
    if not settings.profiles():
        raise ValueError("请先保存至少一个模型配置。")
    target = Path(target or managed_target(settings))
    recorder = receipt_path(settings)
    if recorder.exists() and not force:
        raise ValueError("Claude Code 已接入。如需重新接入，请先恢复配置。")
    parsed = _read_json(target)
    applied = applied_values(settings)
    before = {
        "model": {"present": "model" in parsed, "value": parsed.get("model")},
        "env": {
            key: {"present": key in (parsed.get("env") or {}),
                  "value": (parsed.get("env") or {}).get(key)}
            for key in ENV_KEYS
        },
        "env_present": "env" in parsed,
    }
    document = dict(parsed)
    env_before = parsed.get("env") if isinstance(parsed.get("env"), dict) else {}
    document["env"] = {**env_before, **applied["env"]}
    document["model"] = applied["model"]
    output = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = target.with_name(f"settings.json.before-microglow-relay-{timestamp}.bak")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        atomic_write(backup, target.read_text(encoding="utf-8-sig"))
    else:
        atomic_write(backup, "{}\n")
    receipt = {
        "target": str(target),
        "backup": str(backup),
        "existed": target.exists(),
        "before": before,
        "applied": applied,
    }
    atomic_write(recorder, json.dumps(receipt, ensure_ascii=False, indent=2))
    try:
        atomic_write(target, output)
    except Exception:
        recorder.unlink(missing_ok=True)
        raise
    _trim_backups(target)
    return backup


def restore(settings, force: bool = False) -> Path:
    """Revert Claude Code settings to exactly what they were before integration."""
    recorder = receipt_path(settings)
    if not recorder.exists():
        raise ValueError("没有可恢复的 MicroGlow Relay Claude 接入记录。")
    receipt = json.loads(recorder.read_text(encoding="utf-8"))
    target = Path(receipt["target"])
    parsed = _read_json(target)
    before = receipt["before"]
    applied = receipt["applied"]
    applied_env = applied.get("env") or {}
    conflicts = []
    live_env = parsed.get("env") if isinstance(parsed.get("env"), dict) else {}
    # 每个被管理的键只有两种合法状态：还是我们写入的值（still_applied），
    # 或已被外部精确还原成接入前的样子（already_restored）。其余都是冲突。
    previous_model = before["model"]
    still_applied = "model" in parsed and parsed.get("model") == applied.get("model")
    already_restored = ("model" in parsed) == previous_model["present"] and (
        not previous_model["present"] or parsed.get("model") == previous_model["value"])
    if not still_applied and not already_restored:
        conflicts.append("model")
    for key in ENV_KEYS:
        # 新版 receipt 才管的键：不属于本次接入时不必比对，直接跳过。
        if key not in applied_env:
            continue
        current = live_env.get(key)
        still_applied = current == applied_env.get(key)
        # 旧版 receipt 里没有这个键：按「接入前不存在」还原。
        previous = before["env"].get(key) or {"present": False, "value": None}
        already_restored = (key in live_env) == previous["present"] and (
            not previous["present"] or current == previous["value"])
        if not still_applied and not already_restored:
            conflicts.append(f"env.{key}")
    if conflicts and not force:
        raise ValueError("检测到接入后的外部修改，未覆盖：" + "、".join(conflicts))
    document = dict(parsed)
    env = dict(live_env)
    for key in ENV_KEYS:
        if key not in applied_env:
            continue          # 旧版 receipt 不管这个键，就别去动它
        previous = before["env"].get(key) or {"present": False, "value": None}
        if previous["present"]:
            env[key] = previous["value"]
        else:
            env.pop(key, None)
    if env or before.get("env_present"):
        document["env"] = env
    else:
        document.pop("env", None)
    if before["model"]["present"]:
        document["model"] = before["model"]["value"]
    else:
        document.pop("model", None)
    output = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    if target.exists():
        atomic_write(target.with_name(
            f"settings.json.before-microglow-relay-restore-{timestamp}.bak"),
            target.read_text(encoding="utf-8-sig"))
    atomic_write(target, output)
    recorder.rename(settings.directory / f"microglow-relay-claude-restored-{timestamp}.json")
    _trim_backups(target)
    return Path(receipt["backup"])


def _trim_backups(target: Path) -> None:
    """Keep only the two newest backups owned by Relay, never other tools' files."""
    backups = sorted(target.parent.glob("settings.json.before-microglow-relay-*.bak"),
                     key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
    for old in backups[2:]:
        old.unlink()


def is_integrated(settings) -> bool:
    """True only when the live Claude settings still point at the router."""
    return integration_status(settings) == STATUS_ACTIVE
