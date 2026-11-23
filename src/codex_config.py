# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Reversible Codex integration for MicroGlow Relay."""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import tomllib

import tomlkit

from storage import APP_NAME, REASONING_VALUES, ROUTER_MODEL, atomic_write
from model_names import friendly_slug
from native_models import (NATIVE_MODELS, native_catalog_entry,
                           native_passthrough_available, resolve_native_target)


PROVIDER_ID = "microglow_relay"
STATUS_NONE = "none"
STATUS_ACTIVE = "active"
STATUS_DRIFTED = "drifted"
MANAGED_KEYS = (
    "model_provider",
    "model",
    "model_catalog_json",
    "model_context_window",
    "web_search",
)
REMOVED_KEYS = (
    "forced_login_method",
    "preferred_auth_method",
    "model_auto_compact_token_limit",
)


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def model_catalog(settings) -> dict:
    """为 Codex 导出按供应商分块的模型目录（profile 条目 + 原生模型）。

    slug 用友好名（model_names.py）：人类可读、与 Claude /model 共用；
    配置 id 仍被网关按原样接受（解析链：id → 友好名 → 原生 slug → 404），
    旧会话里写的 id 不会失效。Codex /model 选中哪条，后续请求的
    model 字段就是哪个 slug，切换只影响当前会话（Codex 侧语义），天然按会话隔离。
    原生条目：Codex 的 model_catalog_json 是整体替换语义，Relay 一接入原生表
    就被换掉了；这里把 Codex 自己那份完整条目（含系统提示词）并回来。没有出口
    的原生条目不导出——点了必 404 的按钮比没有更糟。详见 src/native_models.py。
    """
    profiles = settings.profiles()
    # 渠道全部关闭的模型不进目录：选择器里不放点了必失败的选项。
    enabled = [profile for profile in profiles
               if not ((profile.get("channels") or [])
                       and not any(channel.get("enabled", True)
                                   for channel in profile["channels"]))]
    # 按供应商分块：块序 = 供应商在设置里首次出现的顺序，块内按模型名排序。
    # Codex 的选择器是平铺列表，没有分组/子菜单；连续排列 + 统一前缀是唯一
    # 能表达「分组」的手段（客户端 schema 无 group/section 字段）。
    block_order: dict[str, int] = {}
    for profile in enabled:
        block_order.setdefault(_provider_name(profile), len(block_order))
    enabled.sort(key=lambda profile: (block_order[_provider_name(profile)],
                                      str(profile.get("model") or "").lower()))
    entries: list[dict] = []
    seen: dict[str, int] = {}
    for profile in enabled:
        label = _profile_label(profile)
        if seen.get(label):
            label = f"{label}（{int(profile['input_tokens']) // 1000}K）"
        seen[_profile_label(profile)] = seen.get(_profile_label(profile), 0) + 1
        entries.append(_profile_entry(profile, label,
                                      slug=friendly_slug(profile, profiles)))
    taken = {friendly_slug(p, profiles) for p in profiles} | {ROUTER_MODEL}
    native_direct = native_passthrough_available()
    for native in NATIVE_MODELS:
        if native["slug"] in taken:
            # 同名配置的友好 slug 已经占了这个名字：再导出原生条目就是重复项
            # （Codex 要求 slug 唯一）。
            continue
        routed = resolve_native_target(profiles, native["slug"]) is not None
        if not routed and not native_direct:
            # 没有出口的原生条目是「点了必 404」的死按钮。Codex 的
            # visibility="hide" 不可靠（openai/codex#36215 实测仍会显示），
            # 唯一可靠的做法是不写进目录。
            continue
        entries.append(_native_entry(native, routed=routed,
                                     direct=native_direct and not routed))

    if not entries:
        # 一个可用模型都没有：保留「跟随」项，避免选择器空白。
        entries.append(_router_entry(profiles))
    return {"models": entries}


def _reasoning_levels() -> list[dict]:
    return [{"effort": level, "description": label}
            for label, level in (("低", "low"), ("中", "medium"), ("高", "high"))]


def _entry(*, slug: str, display_name: str, description: str,
           context_window: int, images: bool,
           default_effort: str = "medium") -> dict:
    return {
        "slug": slug,
        "display_name": display_name,
        "description": description,
        "default_reasoning_level": default_effort,
        "supported_reasoning_levels": _reasoning_levels(),
        "shell_type": "shell_command",
        "visibility": "list",
        "supported_in_api": True,
        "priority": 0,
        "base_instructions": "You are a coding assistant. Follow the user's request and applicable AGENTS.md instructions. Inspect relevant files, preserve unrelated work, use tools carefully, and verify changes.",
        "supports_reasoning_summaries": False,
        "support_verbosity": False,
        "default_verbosity": None,
        "apply_patch_tool_type": "freeform",
        "web_search_tool_type": "text",
        "supports_search_tool": False,
        "truncation_policy": {"mode": "tokens", "limit": 10_000},
        "supports_parallel_tool_calls": True,
        "context_window": int(context_window),
        "max_context_window": int(context_window),
        "effective_context_window_percent": 90,
        "experimental_supported_tools": [],
        "input_modalities": ["text", "image"] if images else ["text"],
        "prefer_websockets": False,
        "minimal_client_version": "0.144.0",
        "upgrade": None,
    }


def _router_entry(profiles: list[dict]) -> dict:
    """兜底项：目录里一个 profile 都没有时才导出（跟随 Relay 当前选中）。"""
    context = min([profile["input_tokens"] for profile in profiles] or [128_000])
    images = any(profile.get("image_input") for profile in profiles)
    return _entry(
        slug=ROUTER_MODEL,
        display_name=f"{APP_NAME}（跟随 Relay 选择）",
        description="由 MicroGlow Relay 当前选中的模型配置路由。",
        context_window=context,
        images=images,
    )


def _default_slug(settings, profiles: list[dict]) -> str:
    """导出配置的默认模型：优先当前选中项，其次第一个可用 profile。"""
    enabled = [profile for profile in profiles
               if not (profile.get("channels")
                       and not any(channel.get("enabled", True) for channel in profile["channels"]))]
    try:
        selected = settings.selected()
    except ValueError:
        selected = None
    if selected:
        for profile in enabled:
            if profile["id"] == selected["id"]:
                return friendly_slug(profile, profiles)
    if enabled:
        return friendly_slug(enabled[0], profiles)
    # 一个 profile 都没有、但本机登录了 Codex：默认模型落到第一条原生条目。
    # 否则配置里会写一个目录中不存在的 ROUTER_MODEL，Codex 启动即报错。
    if native_passthrough_available():
        return NATIVE_MODELS[0]["slug"]
    return ROUTER_MODEL


def _profile_entry(profile: dict, display_name: str = "", slug: str = "") -> dict:
    provider = str(profile.get("provider_name") or profile.get("provider") or "")
    model = str(profile.get("model") or "")
    effort = REASONING_VALUES.get(str(profile.get("reasoning_effort") or "中"), "medium")
    return _entry(
        # slug 用友好名（model_names.py）：Codex /model 列表里显示的名字，
        # 与 Claude Code 里可手输的名字是同一个。旧会话里的配置 id 仍然有效——
        # 网关 _profile_for 按 id 解析在前，友好名只是加在 id 之上的别名。
        slug=slug or str(profile["id"]),
        display_name=display_name or _profile_label(profile),
        description=f"经 MicroGlow Relay 路由到 {provider} 的 {model}。",
        context_window=int(profile["input_tokens"]),
        images=bool(profile.get("image_input")),
        default_effort=effort,
    )


def _native_entry(native: dict, *, routed: bool, direct: bool) -> dict:
    """Codex 原生模型条目。

    优先使用 Codex 自己那份完整条目：系统提示词、推理档位、工具形态都写在
    条目里，手写一份短条目不叫直通，叫降级。数据文件缺失时才退回快照字段。

    ``routed`` 走 Relay 里的同名配置（跨供应商时推理链降级为文本）；
    ``direct`` 走官方直通（推理链完整）。
    """
    base = native_catalog_entry(native["slug"])
    if base is not None:
        entry = json.loads(json.dumps(base))      # 深拷贝，别让调用方改到缓存
    else:
        entry = _entry(
            slug=native["slug"],
            display_name=native["display_name"],
            description=native["description"],
            context_window=native["context_window"],
            images=native["images"],
            default_effort=native["default_effort"],
        )
    entry["slug"] = native["slug"]
    entry["display_name"] = f"原生｜{native['display_name']}"
    entry["visibility"] = "list"
    entry["description"] = (
        "Codex 原生模型 · 直通本机 ChatGPT 登录态（推理链完整）。"
        if direct else
        "Codex 原生模型 · 经 Relay 同名配置透传（跨供应商时推理链降级为文本）。"
    )
    return entry


def _provider_name(profile: dict) -> str:
    return str(profile.get("provider_name") or profile.get("provider") or "").strip()


def _profile_label(profile: dict) -> str:
    """「供应商｜模型」；同供应商同模型的重复名追加上下文窗口区分。"""
    base = f"{_provider_name(profile)}｜{profile.get('model') or ''}".strip("｜")
    return base[:80]


def provider_config(settings) -> dict:
    return {
        "name": APP_NAME,
        "base_url": f"http://127.0.0.1:{settings.snapshot()['port']}/v1",
        "wire_api": "responses",
        "experimental_bearer_token": settings.local_token(),
        # 必须是 True。这一个开关决定 Codex 要不要加载 ChatGPT 账号身份：
        # 置 False 时 getAuthStatus 返回 authMethod=null，桌面端账号上下文
        # owner 为空，侧栏把整个项目分组塞进「非激活账号」桶，用户看到的就是
        # 「原生项目分组消失、会话没有项目归属」。实测 True 不影响转发：
        # Codex 仍然发 experimental_bearer_token（Bearer <local_token>）；
        # 没登录过 OpenAI 的机器也照常可用（getAuthStatus 依旧返回 null）。
        "requires_openai_auth": True,
        "supports_websockets": False,
        "request_max_retries": 0,
        "stream_max_retries": 0,
        "stream_idle_timeout_ms": 300_000,
    }


def export_files(settings) -> tuple[Path, Path]:
    directory = settings.directory / "microglow-relay-codex"
    directory.mkdir(parents=True, exist_ok=True)
    catalog_path = directory / "models.json"
    config_path = directory / "config.toml"
    atomic_write(catalog_path, json.dumps(model_catalog(settings), ensure_ascii=False, indent=2))
    document = tomlkit.document()
    document["model_provider"] = PROVIDER_ID
    document["model"] = _default_slug(settings, settings.profiles())
    document["model_catalog_json"] = str(catalog_path)
    document["web_search"] = "disabled"
    document["model_providers"] = {PROVIDER_ID: provider_config(settings)}
    atomic_write(config_path, tomlkit.dumps(document))
    return config_path, catalog_path


def receipt_path(settings) -> Path:
    return settings.directory / "microglow-relay-codex-receipt.json"


def refresh_catalog_if_active(settings) -> bool:
    """接入生效时按最新 profile 重建 Codex 模型目录。

    profile 增删改后调用；未接入、写失败一律静默返回 False，
    不阻断界面主流程（下次接入时会重建，旧格式目录同步升级）。
    """
    try:
        if not is_integrated(settings):
            return False
        export_files(settings)
        return True
    except Exception:
        return False


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
    """The Codex configuration file this installation manages."""
    receipt = load_receipt(settings)
    if receipt and receipt.get("target"):
        return Path(str(receipt["target"]))
    return codex_home() / "config.toml"


def _read_config(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return ""


def codex_view(settings) -> dict:
    """What Codex currently resolves from its configuration file."""
    path = managed_target(settings)
    raw = _read_config(path)
    try:
        parsed = tomllib.loads(raw) if raw.strip() else {}
    except tomllib.TOMLDecodeError:
        parsed = {}
    providers = parsed.get("model_providers")
    provider = providers.get(PROVIDER_ID) if isinstance(providers, dict) else None
    return {
        "path": path,
        "exists": path.exists(),
        "provider": str(parsed.get("model_provider") or ""),
        "model": str(parsed.get("model") or ""),
        "catalog": str(parsed.get("model_catalog_json") or ""),
        "provider_table": provider,
        "points_to_router": str(parsed.get("model_provider") or "") == PROVIDER_ID
        and isinstance(provider, dict),
    }


def integration_status(settings) -> str:
    """``none`` | ``active`` | ``drifted`` — based on the live Codex file."""
    receipt = load_receipt(settings)
    if receipt is None:
        return STATUS_NONE
    view = codex_view(settings)
    if not view["exists"]:
        return STATUS_DRIFTED
    applied = receipt.get("applied") or {}
    if not applied:
        return STATUS_DRIFTED
    try:
        parsed = tomllib.loads(_read_config(view["path"]) or "")
    except tomllib.TOMLDecodeError:
        return STATUS_DRIFTED
    for key, value in applied.items():
        if parsed.get(key) != value:
            return STATUS_DRIFTED
    if view["provider_table"] != receipt.get("provider"):
        return STATUS_DRIFTED
    catalog = str(applied.get("model_catalog_json") or "")
    if catalog and not Path(catalog).exists():
        return STATUS_DRIFTED
    return STATUS_ACTIVE


def integration_conflicts(settings) -> list[str]:
    """Keys changed outside the router after the last successful integration."""
    receipt = load_receipt(settings)
    if receipt is None:
        return []
    view = codex_view(settings)
    raw = _read_config(view["path"])
    try:
        parsed = tomllib.loads(raw) if raw.strip() else {}
    except tomllib.TOMLDecodeError:
        return ["config.toml"]
    conflicts = [
        key for key, value in (receipt.get("applied") or {}).items() if parsed.get(key) != value
    ]
    receipt_provider_id = str((receipt.get("applied") or {}).get("model_provider") or PROVIDER_ID)
    providers = parsed.get("model_providers")
    provider_table = providers.get(receipt_provider_id) if isinstance(providers, dict) else None
    if provider_table != receipt.get("provider"):
        conflicts.append(f"model_providers.{receipt_provider_id}")
    return conflicts


def integrate(settings, target: Path | None = None, force: bool = False) -> Path:
    if not settings.profiles():
        raise ValueError("请先保存至少一个模型配置。")
    target = Path(target or managed_target(settings))
    recorder = receipt_path(settings)
    if recorder.exists() and not force:
        raise ValueError("Codex 已接入。如需重新接入，请先恢复配置。")
    raw = target.read_text(encoding="utf-8-sig") if target.exists() else ""
    parsed = tomllib.loads(raw)
    document = tomlkit.parse(raw)
    _, catalog_path = export_files(settings)
    replacements = {
        "model_provider": PROVIDER_ID,
        "model": _default_slug(settings, settings.profiles()),
        "model_catalog_json": str(catalog_path),
        "web_search": "disabled",
    }
    before = {
        key: {"present": key in parsed, "value": parsed.get(key)}
        for key in (*MANAGED_KEYS, *REMOVED_KEYS)
    }
    for key in REMOVED_KEYS:
        document.pop(key, None)
    for key, value in replacements.items():
        document[key] = value
    if "model_providers" not in document:
        document["model_providers"] = tomlkit.table()
    provider = provider_config(settings)
    providers_before = parsed.get("model_providers")
    provider_before = providers_before.get(PROVIDER_ID) if isinstance(providers_before, dict) else None
    document["model_providers"][PROVIDER_ID] = provider
    output = tomlkit.dumps(document)
    tomllib.loads(output)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = target.with_name(f"config.toml.before-microglow-relay-{timestamp}.bak")
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(backup, raw)
    receipt = {
        "target": str(target),
        "backup": str(backup),
        "before": before,
        "applied": replacements,
        "removed": list(REMOVED_KEYS),
        "provider": provider,
        "model_providers_present": "model_providers" in parsed,
        "provider_before_present": provider_before is not None,
        "provider_before": provider_before,
    }
    atomic_write(recorder, json.dumps(receipt, ensure_ascii=False, indent=2))
    try:
        atomic_write(target, output)
    except Exception:
        recorder.unlink(missing_ok=True)
        raise
    _trim_config_backups(target)
    return backup


def _trim_config_backups(target: Path) -> None:
    """Keep only the two newest backups owned by Relay, never other tools' files."""
    backups = sorted(target.parent.glob("config.toml.before-microglow-relay-*.bak"),
                     key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
    for old in backups[2:]:
        old.unlink()


def restore_native(settings) -> Path:
    """Select built-in OpenAI, not an arbitrary historical provider snapshot."""
    target = managed_target(settings)
    raw = target.read_text(encoding="utf-8-sig") if target.exists() else ""
    document = tomlkit.parse(raw)
    document["model"] = "gpt-5.6-sol"
    document["model_provider"] = "openai"
    for key in ("model_catalog_json", "preferred_auth_method", "forced_login_method"):
        document.pop(key, None)
    # Remove Relay's model limits/search override only when still our applied values.
    receipt = load_receipt(settings) or {}
    for key in ("model_context_window", "web_search"):
        if key in document and document[key] == receipt.get("applied", {}).get(key):
            document.pop(key, None)
    output = tomlkit.dumps(document)
    tomllib.loads(output)
    backup = target.with_name("config.toml.before-microglow-relay-native-" +
                              datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".bak")
    if output != raw:
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(backup, raw)
        atomic_write(target, output)
    receipt_path(settings).unlink(missing_ok=True)
    _trim_config_backups(target)
    return backup


def restore(settings, force: bool = False) -> Path:
    recorder = receipt_path(settings)
    if not recorder.exists():
        raise ValueError("没有可恢复的 MicroGlow Relay Codex 接入记录。")
    receipt = json.loads(recorder.read_text(encoding="utf-8"))
    target = Path(receipt["target"])
    raw = target.read_text(encoding="utf-8-sig") if target.exists() else ""
    parsed = tomllib.loads(raw)
    document = tomlkit.parse(raw)
    conflicts = []
    for key, previous in receipt["before"].items():
        if key in receipt["removed"]:
            still_applied = key not in parsed
        else:
            still_applied = parsed.get(key) == receipt["applied"].get(key)
        already_restored = (key in parsed) == previous["present"] and (
            not previous["present"] or parsed.get(key) == previous["value"]
        )
        if not still_applied and not already_restored:
            conflicts.append(key)
    # A receipt may predate the current provider identifier. Restore exactly
    # the provider table named in that receipt; do not touch unrelated tables.
    receipt_provider_id = str(receipt.get("applied", {}).get("model_provider") or PROVIDER_ID)
    provider_now = parsed.get("model_providers", {}).get(receipt_provider_id)
    if provider_now is not None and provider_now != receipt["provider"]:
        conflicts.append(f"model_providers.{receipt_provider_id}")
    if conflicts and not force:
        raise ValueError("检测到接入后的外部修改，未覆盖：" + "、".join(conflicts))
    for key, previous in receipt["before"].items():
        if previous["present"]:
            document[key] = previous["value"]
        else:
            document.pop(key, None)
    if receipt.get("provider_before_present"):
        if "model_providers" not in document:
            document["model_providers"] = tomlkit.table()
        document["model_providers"][receipt_provider_id] = receipt.get("provider_before")
    elif "model_providers" in document:
        document["model_providers"].pop(receipt_provider_id, None)
        if not receipt.get("model_providers_present") and not document["model_providers"]:
            document.pop("model_providers", None)
    output = tomlkit.dumps(document)
    tomllib.loads(output)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    atomic_write(target.with_name(f"config.toml.before-microglow-relay-restore-{timestamp}.bak"), raw)
    atomic_write(target, output)
    recorder.rename(settings.directory / f"microglow-relay-codex-restored-{timestamp}.json")
    return Path(receipt["backup"])


def is_integrated(settings) -> bool:
    """True only when the live Codex configuration still points at the router."""
    return integration_status(settings) == STATUS_ACTIVE


def heal_provider_config(settings) -> bool:
    """把旧版本写入的供应商表就地升级到当前 ``provider_config()``。

    0.8 及更早版本写的是 ``requires_openai_auth = False``；这个值会一直留在
    线上 config.toml 里，老用户即使装上新版本也还是拿不到账号身份、看不到
    项目分组。所以升级时必须主动纠正一次。

    边界很窄，只做「确认没被动过」的纠正：
      * 未接入、或接入已漂移 → 不动，交给界面按 drifted 处理；
      * 线上供应商表必须与接入时留下的快照逐键相等，否则视为用户或其它
        工具改过，一律不覆盖；
      * 只有与当前 provider_config() 不一致才写盘，写前留备份。
    返回是否真的改了盘。
    """
    receipt = load_receipt(settings)
    if receipt is None:
        return False
    if integration_status(settings) != STATUS_ACTIVE:
        return False
    applied = receipt.get("provider")
    if not isinstance(applied, dict):
        return False
    expected = provider_config(settings)
    if applied == expected:
        return False        # 已经是最新表，什么都不用做
    target = managed_target(settings)
    try:
        raw = target.read_text(encoding="utf-8-sig")
        parsed = tomllib.loads(raw)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    live = (parsed.get("model_providers") or {}).get(PROVIDER_ID)
    if not isinstance(live, dict) or live != applied:
        return False        # 线上表被人动过，不覆盖
    document = tomlkit.parse(raw)
    providers = document.get("model_providers")
    if not isinstance(providers, dict) or PROVIDER_ID not in providers:
        return False
    providers[PROVIDER_ID] = expected
    output = tomlkit.dumps(document)
    try:
        tomllib.loads(output)
    except tomllib.TOMLDecodeError:
        return False
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    atomic_write(target.with_name(f"config.toml.before-microglow-relay-heal-{timestamp}.bak"), raw)
    recorder = receipt_path(settings)
    updated = dict(receipt)
    updated["provider"] = expected
    atomic_write(recorder, json.dumps(updated, ensure_ascii=False, indent=2))
    try:
        atomic_write(target, output)
    except Exception:
        # 主文件写失败就把凭据文件退回去，别留下「说改了其实没改」的状态。
        atomic_write(recorder, json.dumps(receipt, ensure_ascii=False, indent=2))
        raise
    _trim_config_backups(target)
    return True
