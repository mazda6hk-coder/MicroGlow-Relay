# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""MicroGlow Relay configuration, validation and Windows secret storage."""
from __future__ import annotations

import base64
import copy
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import uuid
from urllib.parse import urlsplit, urlunsplit


APP_NAME = "MicroGlow Relay"
VERSION = "1.3"
ROUTER_MODEL = "microglow-relay"
# 形状教训缓存有效期：7 天。Codex/上游修复后自动过期，避免长期套用旧降级。
SHAPE_LESSON_TTL = 7 * 24 * 3600
# Fingerprint of a retired model identifier. It is recognized only to avoid
# mistaking historical third-party sessions for official subscription sessions.
_RETIRED_ROUTER_MODEL_SHA256 = "dc49a6c5a8f50c512c13d6a0600daff7ac45beb335138a9b06776da3370fd14a"


def is_retired_router_model(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 14
            and hashlib.sha256(value.encode("utf-8")).hexdigest() == _RETIRED_ROUTER_MODEL_SHA256)


PROVIDERS = {
    "自定义 / 中转服务": {"base_url": "", "protocol": "chat"},
    "OpenAI": {"base_url": "https://api.openai.com/v1/responses", "protocol": "responses"},
    "DeepSeek": {"base_url": "https://api.deepseek.com/chat/completions", "protocol": "chat"},
    "Anthropic": {"base_url": "https://api.anthropic.com/v1/messages", "protocol": "anthropic"},
    "智谱 AI": {"base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "protocol": "chat"},
    "Moonshot AI": {"base_url": "https://api.moonshot.cn/v1/chat/completions", "protocol": "chat"},
    "硅基流动": {"base_url": "https://api.siliconflow.cn/v1/chat/completions", "protocol": "chat"},
    "Ollama（本机）": {"base_url": "http://127.0.0.1:11434/v1/chat/completions", "protocol": "chat"},
}

REASONING_LEVELS = ("低", "中", "高")
REASONING_VALUES = {"低": "low", "中": "medium", "高": "high"}
# responses 通道里推理项的形态：auto 按上游主机判定，其余为显式覆盖。
REASONING_ECHO_LEVELS = ("auto", "text", "summary", "off")
REASONING_ECHO_LABELS = {
    "auto": "自动识别",
    "text": "回传推理正文",
    "summary": "仅回传摘要",
    "off": "不处理",
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class _Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(payload: bytes, decrypting: bool) -> bytes:
    if os.name != "nt":
        raise RuntimeError("MicroGlow Relay 的密钥保险箱需要 Windows。")
    buffer = ctypes.create_string_buffer(payload)
    source = _Blob(len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = _Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    if decrypting:
        ok = crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result))
    else:
        ok = crypt32.CryptProtectData(ctypes.byref(source), APP_NAME, None, None, None, 1, ctypes.byref(result))
    if not ok:
        raise RuntimeError("当前 Windows 账户无法读取密钥，请重新填写 API Key。")
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel32.LocalFree(result.data)


def protect(value: str) -> str:
    return base64.b64encode(_dpapi(value.encode("utf-8"), False)).decode("ascii") if value else ""


def unprotect(value: str) -> str:
    return _dpapi(base64.b64decode(value), True).decode("utf-8") if value else ""


def normalize_base_url(value: str) -> str:
    return validate_api_url(value)


# 各协议的生成端点后缀；顺序即候选优先级（/v1 前缀是 OpenAI 兼容服务的惯例）。
ENDPOINT_SUFFIXES = {
    "chat": ("/v1/chat/completions", "/chat/completions"),
    "responses": ("/v1/responses", "/responses"),
    "anthropic": ("/v1/messages", "/messages"),
    # 图像生成不是 SSE 流，走独立端点；后缀与 chat/responses 并列只为复用
    # 「裸地址自动补全」这一段，请求本身由 server.py 的专用 handler 处理。
    "images": ("/v1/images/generations", "/images/generations"),
}


def complete_endpoint(base: str, protocol: str) -> str:
    """按协议把「裸地址」补全成完整生成端点。

    用户粘贴的常常是站根（https://api.example.com）或带 /v1 的基地址，
    以前这会直接被「接口地址必须以 … 结尾」挡掉。规则：

    * 已经是完整端点（含 /chat/completions、/responses、/messages）→ 原样返回；
    * 裸地址 → 依次试 /v1/<path> 与 /<path>，返回第一个候选；
      候选是否可用由探测/请求时的回退逻辑验证，这里只负责生成。
    """
    return endpoint_candidates(base, protocol)[0]


def endpoint_candidates(base: str, protocol: str) -> list[str]:
    """一个地址在该协议下所有可能的完整端点，按优先级排序。

    完整端点只返回自身；裸地址返回 /v1 与非 /v1 两个候选（已带 /v1
    的基地址则直接拼生成路径，不再叠一层 /v1）。
    """
    base = validate_api_url(base)
    suffixes = ENDPOINT_SUFFIXES.get(protocol, ENDPOINT_SUFFIXES["chat"])
    for suffix in suffixes:
        if base.endswith(suffix):
            return [base]
    # /models 结尾是发现端点，不是生成端点；校验时原样放行。
    if base.endswith("/models"):
        return [base]
    if base.endswith("/v1"):
        # 已带 /v1 的基地址只拼尾部，避免产生 /v1/v1/...。按协议取尾部，
        # 不再写死三种文本端点（images 是第四种）。
        tails = []
        for suffix in suffixes:
            tail = suffix[len("/v1"):] if suffix.startswith("/v1/") else suffix
            if tail not in tails:
                tails.append(tail)
        return [base + tail for tail in tails]
    return [base + suffix for suffix in suffixes]


def validate_api_url(value: str) -> str:
    """Validate a supplier endpoint exactly as published; never rewrite it."""
    value = str(value or "").strip().rstrip("/")
    if not value:
        raise ValueError("请填写接口地址。")
    if "://" not in value:
        local = value.startswith(("localhost", "127.0.0.1", "[::1]"))
        value = ("http://" if local else "https://") + value
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("接口地址必须是有效的 HTTP 或 HTTPS 地址。")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("接口地址不能包含账号、密码、查询参数或片段。")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))

def validate_connection(profile: dict, *, require_custom_name: bool = True) -> dict:
    result = copy.deepcopy(profile)
    provider = str(result.get("provider") or "自定义 / 中转服务").strip()
    if provider not in PROVIDERS:
        provider = "自定义 / 中转服务"
    result["provider"] = provider
    provider_name = str(result.get("provider_name") or "").strip()
    if provider == "自定义 / 中转服务":
        if require_custom_name and not provider_name:
            raise ValueError("自定义供应商请填写供应商名称。")
        provider_name = provider_name or "自定义供应商"
    else:
        provider_name = provider
    if len(provider_name) > 100:
        raise ValueError("供应商名称不能超过 100 个字符。")
    result["provider_name"] = provider_name
    protocol = str(result.get("protocol") or PROVIDERS[provider]["protocol"])
    if protocol not in {"chat", "responses", "anthropic", "images"}:
        raise ValueError("供应商协议无效。")
    result["protocol"] = protocol
    # 裸地址按协议自动补全成完整端点；完整端点原样保留。
    # 存储里始终是完整端点，请求层不需要再猜。
    result["base_url"] = complete_endpoint(result.get("base_url", ""), protocol)
    return result


def _validate_channels(value) -> list[dict]:
    """渠道组校验：空/缺失 → []（单渠道语义），有值则逐项校验。

    渠道 base_url 的协议感知补全在 validate_profile 里做（那里才有协议）；
    这里只做形状校验与归一。
    """
    if value in (None, "", []):
        return []
    if not isinstance(value, list):
        raise ValueError("渠道组必须是数组。")
    cleaned = []
    for channel in value:
        if not isinstance(channel, dict):
            raise ValueError("渠道项必须是对象。")
        base = str(channel.get("base_url") or "").strip()
        if not base:
            raise ValueError("渠道必须填写接口地址。")
        try:
            weight = int(channel.get("weight") or 1)
        except (TypeError, ValueError) as error:
            raise ValueError("渠道权重必须是整数。") from error
        cleaned.append({
            "label": str(channel.get("label") or "").strip()[:100],
            "base_url": base,   # 协议感知补全在 validate_profile 里统一做
            "weight": max(1, min(100, weight)),
            "enabled": bool(channel.get("enabled", True)),
        })
    if len(cleaned) == 1 and not cleaned[0]["label"]:
        return []   # 单渠道且没有备注：退化为单渠道语义，避免无意义的嵌套
    return cleaned


def validate_profile(profile: dict, *, require_custom_name: bool = True) -> dict:
    result = validate_connection(profile, require_custom_name=require_custom_name)
    result["model"] = str(result.get("model") or "").strip()
    if not result["model"] or len(result["model"]) > 200:
        raise ValueError("请填写模型名称，且长度不能超过 200 个字符。")
    for key, default, minimum, maximum in (
        ("input_tokens", 128000, 2048, 10_000_000),
        ("output_tokens", 8192, 64, 1_000_000),
    ):
        try:
            result[key] = int(result.get(key, default))
        except (TypeError, ValueError) as error:
            raise ValueError("输入、输出 Token 必须是整数。") from error
        if not minimum <= result[key] <= maximum:
            raise ValueError(f"{key} 必须在 {minimum} 到 {maximum} 之间。")
    if result["output_tokens"] >= result["input_tokens"]:
        raise ValueError("输出 Token 必须小于输入 Token。")
    for key in ("tool_calls", "image_input", "thinking"):
        result[key] = bool(result.get(key, False))
    result["channels"] = _validate_channels(result.get("channels"))
    # 渠道端点按 profile 协议补全（渠道自身可能只填了站根）。
    for channel in result["channels"]:
        channel["base_url"] = complete_endpoint(channel["base_url"], result["protocol"])
    effort = str(result.get("reasoning_effort") or "中")
    result["reasoning_effort"] = effort if effort in REASONING_LEVELS else "中"
    echo = str(result.get("reasoning_echo") or "auto").strip().lower()
    result["reasoning_echo"] = echo if echo in REASONING_ECHO_LEVELS else "auto"
    result["id"] = str(result.get("id") or "")
    return result


class Settings:
    """Thread-safe version-2 settings store, intentionally separate from v1 data."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.path = self.directory / "microglow-relay-settings.json"
        self.lock = threading.RLock()
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data.get("schema") != 2 or not isinstance(data.get("profiles"), list):
                    raise ValueError("配置版本不受支持")
                data["profiles"] = [
                    validate_profile(profile, require_custom_name=False)
                    for profile in data["profiles"]
                ]
                self.data = data
            except Exception as error:
                raise RuntimeError(f"新版配置无法读取，原文件已保留：{self.path}") from error
        else:
            self.data = {
                "schema": 2,
                "port": 4141,
                "selected": "",
                "profiles": [],
                "local_token": protect(secrets.token_urlsafe(32)),
            }
            self.save()

    def save(self) -> None:
        with self.lock:
            atomic_write(self.path, json.dumps(self.data, ensure_ascii=False, indent=2))

    # ---------------------------------------------------------- shape lessons
    def shape_lessons(self) -> dict:
        """provider|model -> {"actions":[...], "ts":epoch}。读时过滤过期。"""
        import time as _time
        with self.lock:
            raw = self.data.get("shape_lessons") or {}
        now = _time.time()
        out = {}
        for key, val in raw.items():
            if isinstance(val, dict) and now - float(val.get("ts", 0)) < SHAPE_LESSON_TTL:
                out[key] = val
        return out

    def record_shape_lesson(self, provider: str, model: str, actions) -> None:
        import time as _time
        if not actions:
            return
        key = f"{provider}|{model}"
        with self.lock:
            lessons = self.data.setdefault("shape_lessons", {})
            cur = set(lessons.get(key, {}).get("actions", []))
            cur.update(actions)
            lessons[key] = {"actions": sorted(cur), "ts": _time.time()}
            self.save()

    def clear_shape_lessons(self) -> None:
        with self.lock:
            self.data.pop("shape_lessons", None)
            self.save()

    def snapshot(self) -> dict:
        with self.lock:
            return copy.deepcopy(self.data)

    def local_token(self) -> str:
        with self.lock:
            return unprotect(self.data["local_token"])

    def profiles(self) -> list[dict]:
        with self.lock:
            return [self._public(item) for item in self.data["profiles"]]

    def selected(self, include_key: bool = False) -> dict:
        with self.lock:
            profile = next((p for p in self.data["profiles"] if p["id"] == self.data["selected"]), None)
            if profile is None:
                raise ValueError("请先保存并选择一个模型。")
            result = copy.deepcopy(profile)
        if include_key:
            return self._with_keys(result)
        return self._public(result)

    @staticmethod
    def _with_keys(profile: dict) -> dict:
        """解密主 key 与渠道 key；include_key 专用。"""
        result = copy.deepcopy(profile)
        result["api_key"] = unprotect(result.pop("secret", ""))
        if result.get("channels") and result.get("channel_secrets"):
            channels = result["channels"]
            secrets = result.pop("channel_secrets")
            for index, channel in enumerate(channels):
                raw = secrets[index].get("secret", "") if index < len(secrets) else ""
                channel["api_key"] = unprotect(raw)
        result.pop("channel_secrets", None)
        return result

    def profile(self, profile_id: str, include_key: bool = False) -> dict:
        with self.lock:
            profile = next((p for p in self.data["profiles"] if p["id"] == profile_id), None)
            if profile is None:
                raise ValueError("模型配置不存在。")
            result = copy.deepcopy(profile)
        if include_key:
            return self._with_keys(result)
        return self._public(result)

    def upsert(self, profile: dict, api_key: str | None = None,
               channel_keys: list[str] | None = None) -> dict:
        return self.upsert_many([profile], api_key, channel_keys=channel_keys)[0]

    def upsert_many(self, profiles: list[dict], api_key: str | None = None,
                    channel_keys: list[str] | None = None) -> list[dict]:
        cleaned = [validate_profile(profile) for profile in profiles]
        with self.lock:
            before = copy.deepcopy(self.data)
            try:
                for order, clean in enumerate(cleaned):
                    current = next((p for p in self.data["profiles"] if p["id"] == clean.get("id")), None)
                    clean["id"] = current["id"] if current else "model-" + uuid.uuid4().hex[:12]
                    clean["secret"] = protect(api_key) if api_key is not None else (current.get("secret", "") if current else "")
                    # 渠道 key 与渠道一一对应地加密保存；None 表示「不动现有密钥」，
                    # 与主 key 的语义一致（编辑配置不填 key = 保留旧 key）。
                    if clean.get("channels"):
                        stored_secrets = clean.pop("channel_secrets", None)
                        if channel_keys is not None:
                            protected = [{"secret": protect(str(channel_keys[i] or ""))}
                                         if i < len(channel_keys) else {"secret": protect("")}
                                         for i in range(len(clean["channels"]))]
                        else:
                            prior = stored_secrets if stored_secrets is not None else (current or {}).get("channel_secrets", [])
                            protected = [copy.deepcopy(prior[i]) if i < len(prior) else {"secret": protect("")}
                                         for i in range(len(clean["channels"]))]
                        clean["channel_secrets"] = protected
                    else:
                        clean.pop("channel_secrets", None)
                        if current:
                            current.pop("channel_secrets", None)
                    self.data["profiles"] = [p for p in self.data["profiles"] if p["id"] != clean["id"]] + [clean]
                    if not self.data["selected"]:
                        self.data["selected"] = clean["id"]
                self.save()
            except Exception:
                self.data = before
                raise
        return [self._public(clean) for clean in cleaned]

    def upsert_channel_models(self, profile_id: str, index: int,
                              profiles: list[dict], api_key: str) -> list[dict]:
        """Save full model parameters for exactly one supplier, in one write.

        Connection-only edits keep the channel identity. Changes to shared model
        parameters detach only that channel into its own profile; routing still
        groups profiles with the same model name.
        """
        cleaned = [validate_profile(dict(p, channels=[])) for p in profiles]
        if not cleaned:
            raise ValueError("No model selected")
        shared = ("provider", "model", "protocol", "tool_calls", "image_input",
                  "thinking", "reasoning_effort", "input_tokens", "output_tokens")
        with self.lock:
            before = copy.deepcopy(self.data)
            try:
                source = next(p for p in self.data["profiles"] if p["id"] == profile_id)
                channels = copy.deepcopy(source.get("channels") or [{
                    "label": source.get("provider_name", ""), "base_url": source["base_url"],
                    "weight": 1, "enabled": True}])
                target = channels[index]
                secrets = copy.deepcopy(source.get("channel_secrets") or [{"secret": source.get("secret", "")}])
                encrypted = protect(api_key)
                saved = []
                for order, clean in enumerate(cleaned):
                    channel = dict(target, label=clean["provider_name"], base_url=clean["base_url"])
                    if order == 0 and len(channels) > 1 and all(clean.get(k) == source.get(k) for k in shared):
                        channels[index] = channel
                        secrets[index] = {"secret": encrypted}
                        source.update(channels=channels, channel_secrets=secrets)
                        saved.append(source)
                        continue
                    own = dict(source, **clean)
                    own.update(secret=encrypted, channels=[channel], channel_secrets=[{"secret": encrypted}])
                    if order == 0 and len(channels) == 1:
                        own["id"] = profile_id
                        self.data["profiles"] = [own if p["id"] == profile_id else p for p in self.data["profiles"]]
                    else:
                        own["id"] = "model-" + uuid.uuid4().hex[:12]
                        self.data["profiles"].append(own)
                        if order == 0:
                            channels.pop(index); secrets.pop(index)
                            source.update(channels=channels, channel_secrets=secrets,
                                          base_url=channels[0]["base_url"], secret=secrets[0]["secret"])
                    saved.append(own)
                self.save()
            except Exception:
                self.data = before
                raise
        return [self._public(p) for p in saved]

    def select(self, profile_id: str) -> None:
        with self.lock:
            if not any(p["id"] == profile_id for p in self.data["profiles"]):
                raise ValueError("模型配置不存在。")
            self.data["selected"] = profile_id
            self.save()

    def delete(self, profile_id: str) -> None:
        with self.lock:
            self.data["profiles"] = [p for p in self.data["profiles"] if p["id"] != profile_id]
            if self.data["selected"] == profile_id:
                self.data["selected"] = self.data["profiles"][0]["id"] if self.data["profiles"] else ""
            self.save()

    def set_port(self, port: int) -> None:
        port = int(port)
        if not 1024 <= port <= 65535:
            raise ValueError("端口必须在 1024 到 65535 之间。")
        with self.lock:
            self.data["port"] = port
            self.save()

    @staticmethod
    def _public(profile: dict) -> dict:
        result = copy.deepcopy(profile)
        result.pop("secret", None)
        result.pop("channel_secrets", None)
        return result


def redact(message: object, api_key: str = "") -> str:
    text = str(message or "")
    if api_key:
        text = text.replace(api_key, "[API KEY 已隐藏]")
    return text[:800]


Store = Settings
