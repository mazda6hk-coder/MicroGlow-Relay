"""Protocol translation for MicroGlow Relay.

The public side always speaks the OpenAI Responses API.  A selected supplier
may receive Responses, Chat Completions, or Anthropic Messages.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from urllib.parse import unquote_to_bytes, urlsplit

from storage import REASONING_VALUES, complete_endpoint


class ProtocolFailure(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "invalid_request"):
        super().__init__(message)
        self.status = status
        self.code = code


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def read_sse(lines):
    """Yield JSON values from an SSE stream, including multiline data fields."""
    data = []
    for raw in lines:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
        if not line:
            if data:
                payload = "\n".join(data)
                data.clear()
                if payload == "[DONE]":
                    yield payload
                else:
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError as error:
                        raise ProtocolFailure("上游返回了无效的流式数据。", 502, "bad_upstream_stream") from error
            continue
        if line.startswith("data:"):
            data.append(line[5:].lstrip())
    if data:
        payload = "\n".join(data)
        if payload == "[DONE]":
            yield payload
        else:
            try:
                yield json.loads(payload)
            except json.JSONDecodeError as error:
                raise ProtocolFailure("上游流式响应意外中断。", 502, "bad_upstream_stream") from error


class ToolNames:
    def __init__(self, tools):
        self.outbound = {}
        self.inbound = {}
        self.schemas = []
        self._collect(tools or [])

    def _collect(self, tools, prefix=""):
        for tool in tools:
            if not isinstance(tool, dict):
                raise ProtocolFailure("工具定义必须是对象。")
            kind = tool.get("type")
            if kind == "namespace":
                name = str(tool.get("name") or "")
                self._collect(tool.get("tools") or [], prefix + name + ".")
                continue
            if kind not in {"function", "custom"}:
                raise ProtocolFailure("所选供应商仅支持函数工具与自定义文本工具。")
            original = prefix + str(tool.get("name") or "")
            if not original:
                raise ProtocolFailure("工具缺少名称。")
            safe = "".join(char if char.isalnum() or char in "_-" else "_" for char in original)[:64]
            base = safe or "tool"
            suffix = 2
            while safe in self.inbound and self.inbound[safe] != original:
                tail = "_" + str(suffix)
                safe = base[:64-len(tail)] + tail
                suffix += 1
            self.outbound[original] = safe
            self.inbound[safe] = original
            if kind == "custom":
                parameters = {
                    "type": "object",
                    "properties": {"input": {"type": "string", "description": "Raw text passed to the custom tool."}},
                    "required": ["input"],
                    "additionalProperties": False,
                }
            else:
                parameters = tool.get("parameters") or {"type": "object", "properties": {}}
            self.schemas.append({
                "type": "function",
                "function": {
                    "name": safe,
                    "description": str(tool.get("description") or "")[:1024],
                    "parameters": parameters,
                },
            })

    def encode(self, name: str) -> str:
        return self.outbound.get(name, name)

    def decode(self, name: str) -> tuple[str, bool]:
        original = self.inbound.get(name, name)
        return original, original in self.outbound and any(
            schema["function"]["name"] == name
            and schema["function"]["parameters"].get("properties", {}).get("input", {}).get("description", "").startswith("Raw text")
            for schema in self.schemas
        )

    def split_namespace(self, name: str) -> tuple[str, str | None]:
        """回程把展平名拆回 (tool, namespace)。

        Codex 桌面端按 namespace+name 两段识别 MCP/插件工具；chat 上游只能带
        单段 function.name，出站展平为 ``ns.tool``。回程必须拆回，否则 Codex
        收到整串 name、namespace=null 判 unsupported call。仅对确由 namespace
        展平而来（inbound 映射含 '.'）的名字拆分，普通函数名不受影响。
        """
        original = self.inbound.get(name, name)
        if "." in original:
            ns, _, tool = original.rpartition(".")
            if ns and tool:
                return tool, ns
        return original, None

    def merge_namespace(self, item: dict) -> str:
        """出站重发历史时把 namespace+name 合并成展平名，保证与工具声明一致。"""
        name = str(item.get("name") or "")
        ns = item.get("namespace")
        if ns:
            return self.encode(f"{ns}.{name}")
        return self.encode(name)


def _image_for_chat(part: dict) -> dict:
    url = part.get("image_url")
    if not isinstance(url, str) or not url:
        raise ProtocolFailure("图片内容缺少 image_url。")
    return {"type": "image_url", "image_url": {"url": url, "detail": part.get("detail") or "auto"}}


def _message_content(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        raise ProtocolFailure("消息 content 格式无效。")
    result = []
    for part in content:
        if not isinstance(part, dict):
            raise ProtocolFailure("消息内容分片格式无效。")
        kind = part.get("type")
        if kind in {"input_text", "output_text", "text"}:
            block = {"type": "text", "text": str(part.get("text") or "")}
            # 提示缓存标记在内部形状里跟着 part 走；出站按协议决定去留
            #（chat 上游在 _chat_request 里统一剥，Anthropic 上游原样下发）。
            control = part.get("cache_control")
            if isinstance(control, dict) and control.get("type"):
                block["cache_control"] = {"type": str(control["type"])}
            result.append(block)
        elif kind == "input_image":
            result.append(_image_for_chat(part))
        elif kind == "refusal":
            result.append({"type": "text", "text": str(part.get("refusal") or "")})
        else:
            raise ProtocolFailure(f"暂不支持消息内容类型：{kind}")
    return result


def contains_images(body: dict) -> bool:
    source = body.get("input")
    if not isinstance(source, list):
        return False
    return any(
        isinstance(item, dict)
        and isinstance(item.get("content"), list)
        and any(isinstance(part, dict) and part.get("type") == "input_image" for part in item["content"])
        for item in source
    )


def _orphan_output_text(output) -> str:
    """孤儿工具结果的正文：字符串原样，内容数组拼文本，其它压缩成 JSON。"""
    if isinstance(output, str):
        return output.strip()
    if isinstance(output, list):
        parts = []
        for part in output:
            if not isinstance(part, dict):
                continue
            if part.get("type") in {"input_text", "output_text", "text", "summary_text"}:
                parts.append(str(part.get("text") or ""))
            elif part.get("type") == "input_image":
                parts.append("[image]")
        return "\n".join(part for part in parts if part).strip()
    if output is None:
        return ""
    return compact_json(output)


def sanitize_orphan_outputs(items):
    """清洗孤儿工具结果：只作用于发往上游的副本，不改写调用方历史。

    Codex 会把内部簿记（派工回执 / 伴生页快照）以缺 call_id 的
    function_call_output 写进会话历史；严格上游（DeepSeek v4.1 实测）
    会因此 400 或在首个事件前掐断 SSE 流。规则：

    * call_id 缺失或对不上任何 function_call / custom_tool_call → 孤儿；
    * 带正文的孤儿降级为普通文本消息，语义不丢；
    * 空簿记（page_id:null 之类）直接丢弃。
    """
    if not isinstance(items, list):
        return items
    call_ids = {
        str(item.get("call_id") or "")
        for item in items
        if isinstance(item, dict) and item.get("type") in {"function_call", "custom_tool_call"}
    }
    call_ids.discard("")
    cleaned = []
    for item in items:
        if not isinstance(item, dict) or item.get("type") not in {"function_call_output", "custom_tool_call_output"}:
            cleaned.append(item)
            continue
        call_id = str(item.get("call_id") or "")
        if call_id and call_id in call_ids:
            cleaned.append(item)
            continue
        text = _orphan_output_text(item.get("output"))
        if text:
            name = item.get("name")
            label = name if isinstance(name, str) and name.strip() else "tool"
            cleaned.append({
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": f"[{label}] {text}"}],
            })
    return cleaned


# ---------------------------------------------------------------------------
# 工具形状收敛（第 3 层已知快洗 + 第 2 层兜底）。
# Codex 每个版本都可能新增私有工具载体 / 字段；严格上游按 serde 白名单拒收。
# 这里把「已知不兼容」确定性地降级，未知载体兜底收敛，目标保活不炸。
# 参考 cc-switch transform_codex_responses_xai_sanitize.rs 与 issue #7138 实测表。
# ---------------------------------------------------------------------------

# 上游 Responses 普遍接受的 tool type；其余视为 Codex 私有载体。
_RESPONSES_TOOL_TYPES = frozenset({
    "function", "web_search", "file_search", "code_interpreter", "mcp",
    "computer_use_preview", "image_generation", "local_shell",
})


def _empty_object_schema() -> dict:
    return {"type": "object", "properties": {}, "additionalProperties": True}


def _simplify_parameters(params) -> dict:
    """把 function 参数 schema 收敛成上游可接受的根 object。"""
    if not isinstance(params, dict) or not params:
        return _empty_object_schema()
    for union in ("oneOf", "anyOf"):
        branches = params.get(union)
        if isinstance(branches, list) and branches:
            objs = [b for b in branches if isinstance(b, dict) and b.get("type") == "object"]
            if objs:
                merged = {}
                required = None
                for b in objs:
                    merged.update(b.get("properties") or {})
                    br = set(b.get("required") or [])
                    required = br if required is None else (required & br)
                out = {"type": "object", "properties": merged}
                if required:
                    out["required"] = sorted(required)
                return out
            return _empty_object_schema()
    out = dict(params)
    if out.get("type") != "object":
        out["type"] = "object"
        out.setdefault("properties", {})
    return out


def converge_tools(tools):
    """第 3+2 层：custom→function 去 format；function 补/收敛 parameters；
    未知私有载体兜底丢弃。只作用于请求副本。返回 (新列表, 是否变化)。"""
    if not isinstance(tools, list):
        return tools, False
    changed = False
    out = []
    for tool in tools:
        if not isinstance(tool, dict):
            out.append(tool)
            continue
        kind = tool.get("type")
        if kind == "custom":
            # custom/freeform（apply_patch）→ function，输入为自由文本，丢 format。
            new = {"type": "function", "name": tool.get("name"),
                   "description": tool.get("description") or "",
                   "parameters": {"type": "object",
                                  "properties": {"input": {"type": "string"}},
                                  "required": ["input"], "additionalProperties": False}}
            out.append(new)
            changed = True
            continue
        if kind == "function":
            params = tool.get("parameters")
            simplified = _simplify_parameters(params)
            if params != simplified:
                tool = dict(tool, parameters=simplified)
                changed = True
            out.append(tool)
            continue
        if kind in _RESPONSES_TOOL_TYPES or kind == "namespace":
            out.append(tool)
            continue
        # 未知私有载体（tool_search/additional_tools/…）兜底丢弃，保活。
        changed = True
    return out, changed


def repair_tools_from_error(payload: dict, detail: str):
    """第 1 层反应式：读上游 400/422 错误里的工具字段提示，定点降级后重试。

    不预判 Codex 新字段；只要上游报错带字段名（tools[i].format / .strict /
    oneOf / custom …），就剥掉对应字段或收敛 schema。返回 (新 payload, 是否变化)。
    """
    if not isinstance(payload, dict):
        return payload, False
    tools = payload.get("tools")
    if not isinstance(tools, list) or not tools:
        return payload, False
    text = detail or ""
    changed = False
    new_tools = []
    import re as _re
    idx_match = _re.search(r"tools\[(\d+)\]", text)
    target_idx = int(idx_match.group(1)) if idx_match else None
    for i, tool in enumerate(tools):
        if not isinstance(tool, dict):
            new_tools.append(tool)
            continue
        hit = (target_idx is None) or (i == target_idx)
        t = dict(tool)
        if hit and ("format" in text) and "format" in t:
            t.pop("format", None)
            changed = True
        if hit and ("strict" in text) and t.get("strict") is True:
            t["strict"] = False
            changed = True
        if hit and ("oneOf" in text or "anyOf" in text or "allOf" in text or "schema" in text):
            if "parameters" in t:
                t["parameters"] = _simplify_parameters(t.get("parameters"))
                changed = True
        if hit and ("custom" in text) and t.get("type") == "custom":
            t = {"type": "function", "name": t.get("name"),
                 "description": t.get("description") or "",
                 "parameters": {"type": "object", "properties": {"input": {"type": "string"}},
                                "required": ["input"], "additionalProperties": False}}
            changed = True
        new_tools.append(t)
    if not changed:
        return payload, False
    result = dict(payload)
    result["tools"] = new_tools
    return result, True


# ---------------------------------------------------------------------------
# 形状教训缓存：把「某供应商×模型 靠剥 X 修好」记下来，下次预洗，避免白打 400。
# 键 = provider|model；值 = 已验证有效的降级动作集合。只增不减、保守应用（剥字段
# 是放宽，不会把好的变坏）。带 TTL，Codex/上游修复后自动过期。纯内存+持久化由
# storage 负责；这里只做纯函数 apply_lessons / lesson_actions_from_error。
# ---------------------------------------------------------------------------

LESSON_ACTIONS = ("strip_format", "disable_strict", "collapse_schema", "custom_to_function")


def lesson_actions_from_error(detail: str) -> tuple:
    """从上游报错推断应记住的降级动作（与 repair_tools_from_error 同口径）。"""
    text = detail or ""
    acts = []
    if "format" in text:
        acts.append("strip_format")
    if "strict" in text:
        acts.append("disable_strict")
    if "oneOf" in text or "anyOf" in text or "allOf" in text or "schema" in text:
        acts.append("collapse_schema")
    if "custom" in text:
        acts.append("custom_to_function")
    return tuple(a for a in acts if a in LESSON_ACTIONS)


def apply_lessons(payload: dict, actions) -> tuple:
    """按已记住的动作预洗工具形状。返回 (新 payload, 是否变化)。"""
    if not isinstance(payload, dict) or not actions:
        return payload, False
    tools = payload.get("tools")
    if not isinstance(tools, list) or not tools:
        return payload, False
    acts = set(actions)
    changed = False
    out = []
    for tool in tools:
        if not isinstance(tool, dict):
            out.append(tool)
            continue
        t = dict(tool)
        if "strip_format" in acts and "format" in t:
            t.pop("format", None)
            changed = True
        if "disable_strict" in acts and t.get("strict") is True:
            t["strict"] = False
            changed = True
        if "collapse_schema" in acts and "parameters" in t:
            simp = _simplify_parameters(t.get("parameters"))
            if simp != t.get("parameters"):
                t["parameters"] = simp
                changed = True
        if "custom_to_function" in acts and t.get("type") == "custom":
            t = {"type": "function", "name": t.get("name"),
                 "description": t.get("description") or "",
                 "parameters": {"type": "object", "properties": {"input": {"type": "string"}},
                                "required": ["input"], "additionalProperties": False}}
            changed = True
        out.append(t)
    if not changed:
        return payload, False
    result = dict(payload)
    result["tools"] = out
    return result, True


def _chat_messages(body: dict, tools: ToolNames, profile: dict, reasoning_cache=None) -> list[dict]:
    source = body.get("input", "")
    if isinstance(source, str):
        messages = [{"role": "user", "content": source}]
    elif not isinstance(source, list):
        raise ProtocolFailure("input 必须是字符串或消息数组。")
    else:
        messages = []
        pending_reasoning = ""
        for item in source:
            if not isinstance(item, dict):
                raise ProtocolFailure("input 数组中存在无效项目。")
            kind = item.get("type")
            if kind in {"reasoning", "computer_initialize_state"}:
                if kind == "reasoning":
                    summary = item.get("summary") or []
                    pending_reasoning = "\n".join(
                        str(part.get("text") or "") for part in summary if isinstance(part, dict)
                    )
                continue
            if kind == "message" or ("role" in item and kind is None):
                role = item.get("role")
                if role not in {"user", "assistant", "system", "developer"}:
                    raise ProtocolFailure(f"不支持消息角色：{role}")
                upstream_role = "system" if role == "developer" else role
                message = {"role": upstream_role, "content": _message_content(item.get("content", ""))}
                if upstream_role == "assistant" and profile.get("thinking") and pending_reasoning:
                    message["reasoning_content"] = pending_reasoning
                messages.append(message)
                pending_reasoning = ""
                continue
            if kind in {"function_call", "custom_tool_call"}:
                name = tools.merge_namespace(item)
                arguments = item.get("arguments", "{}")
                if kind == "custom_tool_call":
                    arguments = compact_json({"input": item.get("input", "")})
                if not isinstance(arguments, str):
                    arguments = compact_json(arguments)
                call = {
                    "id": str(item.get("call_id") or item.get("id") or ""),
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
                # 提示缓存标记跟着工具调用走（Claude Code 常在 tool_use 上打标）。
                control = item.get("cache_control")
                if isinstance(control, dict) and control.get("type"):
                    call["cache_control"] = {"type": str(control["type"])}
                if messages and messages[-1].get("role") == "assistant" and messages[-1].get("tool_calls"):
                    target = messages[-1]
                else:
                    target = {"role": "assistant", "content": None, "tool_calls": []}
                    messages.append(target)
                target["tool_calls"].append(call)
                if profile.get("thinking") and "reasoning_content" not in target:
                    cached = reasoning_cache.get(call["id"]) if reasoning_cache and call["id"] else None
                    target["reasoning_content"] = cached or pending_reasoning or "Continue with the recorded tool result."
                pending_reasoning = ""
                continue
            if kind in {"function_call_output", "custom_tool_call_output"}:
                output = item.get("output", "")
                messages.append({
                    "role": "tool",
                    "tool_call_id": str(item.get("call_id") or ""),
                    "content": output if isinstance(output, str) else compact_json(output),
                })
                continue
            raise ProtocolFailure(f"暂不支持的 input 类型：{kind}")
    instructions = body.get("instructions")
    if isinstance(instructions, str) and instructions.strip():
        messages.insert(0, {"role": "system", "content": instructions})
    return messages


def _tool_choice(choice, names: ToolNames):
    if choice in (None, "auto", "none", "required"):
        return choice
    if isinstance(choice, dict) and choice.get("type") == "function":
        return {"type": "function", "function": {"name": names.encode(str(choice.get("name") or ""))}}
    return "auto"


def _chat_request(body: dict, profile: dict, reasoning_cache=None):
    names = ToolNames(body.get("tools"))
    payload = {
        "model": profile["model"],
        "messages": _chat_messages(body, names, profile, reasoning_cache),
        "stream": True,
        "max_tokens": min(int(body.get("max_output_tokens") or profile["output_tokens"]), profile["output_tokens"]),
    }
    # chat 上游不认识 cache_control（未知字段可能 400），出站前统一剥掉。
    for message in payload["messages"]:
        content = message.get("content")
        if isinstance(content, list):
            message["content"] = [
                {key: value for key, value in part.items() if key != "cache_control"}
                if isinstance(part, dict) else part
                for part in content
            ]
        for call in message.get("tool_calls") or []:
            call.pop("cache_control", None)
    if names.schemas:
        payload["tools"] = names.schemas
        payload["tool_choice"] = _tool_choice(body.get("tool_choice"), names)
    if profile.get("thinking"):
        payload["reasoning_effort"] = REASONING_VALUES[profile["reasoning_effort"]]
    return "", payload, names


def _anthropic_content(content):
    converted = []
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    for part in content:
        if part.get("type") in {"input_text", "output_text", "text"}:
            block = {"type": "text", "text": str(part.get("text") or "")}
        elif part.get("type") == "input_image":
            url = str(part.get("image_url") or "")
            if not url.startswith("data:") or ";base64," not in url:
                raise ProtocolFailure("Anthropic 图片必须是 base64 Data URL。")
            header, data = url.split(",", 1)
            block = {
                "type": "image",
                "source": {"type": "base64", "media_type": header[5:].split(";", 1)[0], "data": data},
            }
        else:
            raise ProtocolFailure(f"Anthropic 不支持内容类型：{part.get('type')}")
        # 提示缓存标记原样下发：Anthropic 上游靠它复用前缀，剥掉就是全价重算。
        control = part.get("cache_control")
        if isinstance(control, dict) and control.get("type"):
            block["cache_control"] = {"type": str(control["type"])}
        converted.append(block)
    return converted


def _anthropic_request(body: dict, profile: dict, reasoning_cache=None):
    names = ToolNames(body.get("tools"))
    chat = _chat_messages(body, names, profile, reasoning_cache)
    system = []
    messages = []
    for message in chat:
        role = message["role"]
        if role == "system":
            system.append(str(message.get("content") or ""))
            continue
        if role == "tool":
            messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": message["tool_call_id"], "content": message["content"]}]})
            continue
        content = _anthropic_content(message.get("content") or [])
        for call in message.get("tool_calls", []):
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError as error:
                raise ProtocolFailure("历史工具参数不是有效 JSON。") from error
            tool_use = {"type": "tool_use", "id": call["id"], "name": call["function"]["name"], "input": args}
            # 缓存标记从 function_call 链路搬回 tool_use 块。
            if isinstance(call.get("cache_control"), dict):
                tool_use["cache_control"] = {"type": str(call["cache_control"].get("type") or "ephemeral")}
            content.append(tool_use)
        target_role = "assistant" if role == "assistant" else "user"
        messages.append({"role": target_role, "content": content})
    # Anthropic Messages API 强制 user/assistant 严格交替；并行工具调用会产出
    # 连续的 user(tool_result) 消息，回放历史也可能带相邻同角色段。
    # 同角色相邻消息按内容块合并成一条，否则上游一律 400。
    merged = []
    for message in messages:
        if merged and merged[-1]["role"] == message["role"]:
            merged[-1]["content"] = merged[-1]["content"] + message["content"]
        else:
            merged.append(message)
    messages = merged
    # Anthropic 还要求首条消息必须是 user 角色。历史回放可能带 assistant 开场的
    # 序列；与其让上游回一个模糊 400，不如在本地给出可定位的协议错误。
    if messages and messages[0]["role"] != "user":
        raise ProtocolFailure(
            "Anthropic 通道要求首条消息为 user 角色，请检查会话历史形状。", 400,
            "invalid_message_order")
    payload = {
        "model": profile["model"],
        "messages": messages,
        "stream": True,
        "max_tokens": min(int(body.get("max_output_tokens") or profile["output_tokens"]), profile["output_tokens"]),
    }
    if system:
        payload["system"] = "\n\n".join(system)
    if names.schemas:
        payload["tools"] = [
            {"name": schema["function"]["name"], "description": schema["function"]["description"], "input_schema": schema["function"]["parameters"]}
            for schema in names.schemas
        ]
    if profile.get("thinking"):
        # Anthropic 硬性要求 thinking.budget_tokens >= 1024 且 < max_tokens。
        # max_tokens 装不下合法预算时（例如 128 的探测请求），下发 thinking 必然 400，
        # 此时静默省略该字段，让请求按非思考模式完成。
        budget = min({"低": 1024, "中": 4096, "高": 8192}[profile["reasoning_effort"]],
                     payload["max_tokens"] - 1)
        if budget >= 1024:
            payload["thinking"] = {"type": "enabled", "budget_tokens": budget}
    return "", payload, names


# ---------------------------------------------------------------------------
# 推理项形态适配
#
# responses 通道是逐字节透传的，但各供应商对“上一轮推理项”的形态要求并不一致：
#
# * text    —— 工具续接时必须回传非空 reasoning_text（深度探索 /responses）
# * summary —— 只认 summary 形态，遇到 reasoning_text 直接 400（菜鸟AI）
# * off     —— 两种都收（熊出没等宽容供应商）
#
# auto 按上游主机判定，profile 里的 reasoning_echo 可以显式覆盖。
# ---------------------------------------------------------------------------
REASONING_ECHO_MODES = ("auto", "text", "summary", "off")
REASONING_PLACEHOLDER = "Continue with the recorded tool result."
_TOOL_CALL_TYPES = frozenset({"function_call", "custom_tool_call"})
# 需要「紧邻前置推理项」的 assistant 侧条目：工具调用项，以及 assistant 消息本身。
# 实测（api.deepseek.com，2026-10-11，见 work/probe-reasoning-rule-2.py）：
#   * 当前轮首条 assistant 消息缺前置推理 → 400；在它之前插入合成项 → 200
#   * 工具输出之后出现的 assistant 消息缺前置推理 → 400（线上故障形态）；插入即 200
#   * 紧邻前项是另一条 assistant 消息时上游放行，且合成项不能插在两者之间（仍 400）
#   * 已有合规推理项时不做任何改动，正常请求字节不变
_REASONING_PREFIX_TYPES = _TOOL_CALL_TYPES


def reasoning_echo_mode(profile: dict) -> str:
    """Resolve the reasoning-item shape this upstream expects."""
    configured = str(profile.get("reasoning_echo") or "auto").strip().lower()
    if configured in {"text", "summary", "off"}:
        return configured
    host = (urlsplit(str(profile.get("base_url") or "")).hostname or "").lower()
    if host == "api.deepseek.com":
        return "text"
    if "buddybackend.cloud" in host:
        return "summary"
    return "off"


def _reasoning_item_text(item: dict) -> str:
    """First non-empty reasoning text, preferring content over summary."""
    for key, kind in (("content", "reasoning_text"), ("summary", "summary_text")):
        parts = item.get(key)
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict) and part.get("type") == kind:
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
    return ""

# ---------------------------------------------------------------------------
# 跨供应商推理续接：密文只有产出它的上游解得开
#
# Codex 续接一个「原生模型」会话时，会把整段历史连同原生 reasoning 项一起重放，
# 那些项带着 OpenAI 的真密文（实测 1.3K~1.7K 字符的不透明团）。
# 密文转给第三方上游毫无意义且必然被拒，于是整段会话直接废掉——
# 而 adapt_reasoning_input 原先只修「当前轮」的形状，历史项一个字节都不碰。
#
# 反方向（Relay 会话切回官方）另有一套规矩：官方 Responses 拒绝长度非零的
# reasoning content，所以要把文本折进 summary 再清空 content；Relay 自产的
# UUID 形占位密文对官方也是垃圾，一并丢掉。
# ---------------------------------------------------------------------------
PLACEHOLDER_CIPHERTEXT = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}(?:-\d{1,12})?")


def _is_openai_upstream(profile: dict) -> bool:
    """目标上游是不是 OpenAI 官方——只有它解得开 reasoning 密文。"""
    host = (urlsplit(str(profile.get("base_url") or "")).hostname or "").lower()
    return host == "api.openai.com" or host.endswith(".openai.com")


def _fold_reasoning_text_into_summary(item: dict) -> None:
    """把 content 里的 reasoning_text 折进 summary，再清空 content。"""
    summary = item.get("summary")
    if not isinstance(summary, list):
        summary = []
    has_summary = any(
        isinstance(part, dict) and part.get("type") == "summary_text"
        and str(part.get("text") or "").strip()
        for part in summary
    )
    body_text = _reasoning_item_text(item)
    if body_text and not has_summary:
        summary = summary + [{"type": "summary_text", "text": body_text}]
    item["summary"] = summary
    if item.get("content") is not None:
        item["content"] = []


def _neutralise_foreign_ciphertext(items: list, profile: dict) -> tuple[list, bool]:
    """让每条 reasoning 项的密文只对「解得开它的上游」可见。

    返回新列表与是否有改动。改动一律以复制改写的方式进行，不就地修改调用方
    传进来的对象——与 _ensure_reasoning_prefix 的约定一致。
    """
    official = _is_openai_upstream(profile)
    result: list = []
    changed = False
    for item in items:
        if not isinstance(item, dict) or item.get("type") != "reasoning":
            result.append(item)
            continue
        cipher = item.get("encrypted_content")
        carries_text = isinstance(item.get("content"), list) and bool(item["content"])
        if official:
            # 官方方向：真密文原样带回（切回原生模型时推理链才接得上）；
            # 只有 Relay 自产的占位符要丢，同时官方拒绝非空 content。
            placeholder = isinstance(cipher, str) and bool(
                PLACEHOLDER_CIPHERTEXT.fullmatch(cipher))
            if not placeholder and not carries_text:
                result.append(item)
                continue
            patched = dict(item)
            if placeholder:
                patched["encrypted_content"] = None
            if carries_text:
                _fold_reasoning_text_into_summary(patched)
            result.append(patched)
            changed = True
            continue
        # 第三方方向：密文一律作废。它解不开，带了就是 400。
        if not isinstance(cipher, str) or not cipher:
            result.append(item)
            continue
        patched = dict(item)
        patched["encrypted_content"] = None
        result.append(patched)
        changed = True
    return result, changed


def _fill_reasoning_text(item: dict) -> bool:
    """Guarantee a non-empty reasoning_text. Returns True when the item changed."""
    content = item.get("content")
    if not isinstance(content, list):
        content = []
    for part in content:
        if isinstance(part, dict) and part.get("type") == "reasoning_text":
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                return False
            part["text"] = _reasoning_item_text(item) or REASONING_PLACEHOLDER
            item["content"] = content
            return True
    content.append({"type": "reasoning_text", "text": _reasoning_item_text(item) or REASONING_PLACEHOLDER})
    item["content"] = content
    return True


def _strip_reasoning_text(item: dict) -> bool:
    """Move reasoning text into summary and empty the content list."""
    text = _reasoning_item_text(item)
    summary = item.get("summary")
    if not isinstance(summary, list):
        summary = []
    has_summary = any(
        isinstance(part, dict) and part.get("type") == "summary_text" and str(part.get("text") or "").strip()
        for part in summary
    )
    if text and not has_summary:
        summary = summary + [{"type": "summary_text", "text": text}]
    changed = False
    if item.get("content") != []:
        item["content"] = []
        changed = True
    if item.get("summary") != summary:
        item["summary"] = summary
        changed = True
    if item.get("encrypted_content") is not None:
        item["encrypted_content"] = None
        changed = True
    return changed


def _placeholder_reasoning() -> dict:
    return {
        "type": "reasoning",
        "id": str(uuid.uuid4()),
        "status": "completed",
        "summary": [],
        "content": [{"type": "reasoning_text", "text": REASONING_PLACEHOLDER}],
        "encrypted_content": None,
    }


def _nearest_reasoning_index(sequence: list, index: int):
    """Index of the nearest reasoning item above ``index``, skipping one message."""
    skipped_message = False
    cursor = index - 1
    while cursor >= 0:
        candidate = sequence[cursor]
        if not isinstance(candidate, dict):
            return None
        kind = candidate.get("type")
        if kind == "reasoning":
            return cursor
        if kind == "message":
            if skipped_message:
                return None
            skipped_message = True
        cursor -= 1
    return None


def _is_reasoning_prefixed_item(item) -> bool:
    """需要「紧邻前置推理项」的 assistant 侧条目：工具调用项，或 assistant 消息。"""
    if not isinstance(item, dict):
        return False
    if item.get("type") in _REASONING_PREFIX_TYPES:
        return True
    return item.get("type") == "message" and item.get("role") == "assistant"


def _is_assistant_message(item) -> bool:
    return (isinstance(item, dict) and item.get("type") == "message"
            and item.get("role") == "assistant")


def _is_tool_call_item(item) -> bool:
    """工具调用项。同一轮里并发的多个调用必须彼此紧邻，中间不得插入任何条目。

    实测（api.deepseek.com，2026-10-12，见 work/probe-reasoning-parallel.py）：
    在 ``function_call A`` 与 ``function_call B`` 之间插一条合成推理项，上游会把
    A 的工具输出判为缺失，立刻 400
    ``No tool output found for tool call call_...``，0.25 秒内就被拒。
    """
    return isinstance(item, dict) and item.get("type") in _TOOL_CALL_TYPES


def _has_reasoning_text(item) -> bool:
    """text 模式要求紧邻前置的推理项带**非空** reasoning_text（只有 summary 不合格）。"""
    if not isinstance(item, dict) or item.get("type") != "reasoning":
        return False
    parts = item.get("content")
    if not isinstance(parts, list):
        return False
    return any(isinstance(part, dict) and part.get("type") == "reasoning_text"
               and isinstance(part.get("text"), str) and part["text"].strip()
               for part in parts)


def _strip_reasoning_shape(tail: list) -> bool:
    """summary 模式：清理工具调用项邻域里的 reasoning_text（沿用原有宽松邻域）。"""
    changed = False
    for index, item in enumerate(tail):
        if not isinstance(item, dict) or item.get("type") not in _REASONING_PREFIX_TYPES:
            continue
        position = _nearest_reasoning_index(tail, index)
        if position is None:
            continue
        clone = dict(tail[position])
        if _strip_reasoning_text(clone):
            tail[position] = clone
            changed = True
    return changed


def _ensure_reasoning_prefix(tail: list, before) -> list | None:
    """text 模式：逐条保证 assistant 侧条目紧邻之上是合规推理项。

    判定用的是**紧邻前项**，不是「往上的最近推理项」——实测上游正是按紧邻关系校验的
    （跨过工具输出往上看会误判为合规，这正是线上 400 被漏掉的原因）。返回新列表；
    无需改动时返回 None，调用方保持原 payload 字节不变。
    """
    patched = [before]
    changed = False
    for item in tail:
        previous = patched[-1]
        if _is_reasoning_prefixed_item(item) and not _has_reasoning_text(previous):
            if isinstance(previous, dict) and previous.get("type") == "reasoning":
                # 已有推理项但缺 reasoning_text：就地补齐，不插新条目。
                clone = dict(previous)
                if _fill_reasoning_text(clone):
                    patched[-1] = clone
                    changed = True
            elif not _is_assistant_message(previous) and not _is_tool_call_item(previous):
                # 上游对「紧邻前项是另一条 assistant 消息」放行；否则在并发批次里
                # 后一个调用也不能被插队（插进去等于把前一个调用与它的工具输出拆开）。
                # 其余情况补一条合成项。
                patched.append(_placeholder_reasoning())
                changed = True
        patched.append(item)
    return patched[1:] if changed else None


def adapt_reasoning_input(payload: dict, profile: dict, *, force: str = "") -> tuple[dict, bool]:
    """Align reasoning items with the shape the upstream provider accepts.

    两件事，彼此独立：

    1. **全量**中和外来密文（见 _neutralise_foreign_ciphertext）。原生会话重放出的
       OpenAI 真密文只有官方解得开，转给第三方必然 400；反方向 Relay 的占位符和
       非空 content 官方也不收。这一步与 echo 模式无关，任何模式下都要做。
    2. 只修**当前轮**的形状：everything at or before the last
       ``user``/``developer`` message is passed through untouched. Returns the
       payload (unchanged object when nothing needed fixing) and a changed flag.

    规则（实测 api.deepseek.com，2026-10-11，见 work/probe-deepseek-direct.py）：
    当前轮里每个 assistant 侧条目（工具调用项、assistant 消息）的**紧邻前项**
    必须是带非空 reasoning_text 的推理项，或是另一条 assistant 消息；否则上游
    一律按形态 400 拒绝。缺一处补一处——只补其中一处仍然 400，所以这里逐条处理。
    合成项落在被拒条目紧邻之前即可（本轮开头同样合法）。
    """
    items = payload.get("input")
    if not isinstance(items, list) or not items:
        return payload, False
    cleaned, changed = _neutralise_foreign_ciphertext(items, profile)
    mode = str(force or "").strip().lower() or reasoning_echo_mode(profile)
    if mode in {"text", "summary"}:
        boundary = -1
        for index, item in enumerate(cleaned):
            if (isinstance(item, dict) and item.get("type") == "message"
                    and item.get("role") in {"user", "developer"}):
                boundary = index
        if boundary >= 0:
            tail = list(cleaned[boundary + 1:])
            if mode == "summary":
                # buddybackend 方向相反：只清理 reasoning_text，不插任何合成项。
                if _strip_reasoning_shape(tail):
                    changed = True
            else:
                patched = _ensure_reasoning_prefix(tail, cleaned[boundary])
                if patched is not None:
                    tail = patched
                    changed = True
            cleaned = list(cleaned[:boundary + 1]) + tail
    if not changed:
        return payload, False
    result = dict(payload)
    result["input"] = cleaned
    return result, True


def prepare_request(body: dict, profile: dict, reasoning_cache=None):
    if not isinstance(body, dict) or not isinstance(body.get("model"), str):
        raise ProtocolFailure("请求必须包含 model 字符串。")
    if isinstance(body.get("input"), list):
        # 孤儿工具结果在这里统一清洗：chat / anthropic / responses 三条路径共用。
        # 只作用于本次请求副本，绝不改写调用方的 body 与本地历史。
        body = dict(body)
        body["input"] = sanitize_orphan_outputs(body["input"])
    if isinstance(body.get("tools"), list):
        # 第 3+2 层：已知不兼容工具形状快洗 + 未知载体兜底收敛。
        body = dict(body)
        converged, _tools_changed = converge_tools(body["tools"])
        body["tools"] = converged
    if body.get("tools") and not profile.get("tool_calls"):
        raise ProtocolFailure("当前模型配置未启用工具调用。", 400, "tools_disabled")
    if contains_images(body) and not profile.get("image_input"):
        raise ProtocolFailure("当前模型配置未启用图片输入。", 400, "images_disabled")
    protocol = profile["protocol"]
    endpoint = profile["base_url"].rstrip("/")
    # 裸地址按协议自动补全：正常保存路径在 validate_connection 就已补全，
    # 这里兜住手改配置文件、或旧版本存了裸地址的现场。
    required_suffix = {"chat": "/chat/completions", "responses": "/responses", "anthropic": "/messages"}[protocol]
    if not endpoint.endswith(required_suffix):
        endpoint = complete_endpoint(endpoint, protocol)
    profile = dict(profile, base_url=endpoint)
    if protocol == "chat":
        return (*_chat_request(body, profile, reasoning_cache), protocol)
    if protocol == "anthropic":
        return (*_anthropic_request(body, profile, reasoning_cache), protocol)
    if body.get("previous_response_id") or body.get("conversation"):
        raise ProtocolFailure("路由切换要求发送完整 input，不能使用上游会话 ID。")
    payload = dict(body)
    payload["model"] = profile["model"]
    payload["stream"] = True
    payload["store"] = False
    payload["max_output_tokens"] = min(
        int(body.get("max_output_tokens") or profile["output_tokens"]),
        profile["output_tokens"],
    )
    if not profile.get("thinking"):
        payload.pop("reasoning", None)
    # Claude 客户端的 cache_control 标记可能落在 item 顶层（function_call）。
    # OpenAI Responses 不认识这个字段，逐项剥掉；content part 级的标记
    # 随透传保留（OpenAI 忽略未知 part 字段，实测无碍）。
    if isinstance(payload.get("input"), list):
        payload["input"] = [
            {key: value for key, value in item.items() if key != "cache_control"}
            if isinstance(item, dict) else item
            for item in payload["input"]
        ]
    payload, _reasoning_changed = adapt_reasoning_input(payload, profile)
    return "", payload, None, protocol


class ResponseBuilder:
    """Build Responses events and a final response from Chat/Anthropic deltas."""

    def __init__(self, model: str, names: ToolNames | None, emit, reasoning_cache=None):
        self.model = model
        self.names = names or ToolNames([])
        self.emit_callback = emit
        self.reasoning_cache = reasoning_cache
        self.response_id = "resp_" + uuid.uuid4().hex
        self.text = ""
        self.reasoning = ""
        self.calls = {}
        self.usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        self.finish_reason = None
        self.output = []
        self.sequence = 0
        self.message_id = "msg_" + uuid.uuid4().hex
        self.message_open = False

    def emit(self, kind: str, **data):
        event = {"type": kind, "sequence_number": self.sequence, **data}
        self.sequence += 1
        self.emit_callback(event)

    def response(self, status="in_progress"):
        return {
            "id": self.response_id,
            "object": "response",
            "created_at": int(time.time()),
            "status": status,
            "model": self.model,
            "output": self.output,
            "usage": self.usage,
            "error": None,
        }

    def start(self):
        self.emit("response.created", response=self.response("in_progress"))
        self.emit("response.in_progress", response=self.response("in_progress"))

    def add_text(self, text: str):
        if not text:
            return
        if not self.message_open:
            self.message_open = True
            item = {"id": self.message_id, "type": "message", "status": "in_progress", "role": "assistant", "content": []}
            self.output.append(item)
            self.emit("response.output_item.added", output_index=len(self.output)-1, item=item)
            part = {"type": "output_text", "text": "", "annotations": [], "logprobs": []}
            item["content"].append(part)
            self.emit("response.content_part.added", item_id=self.message_id, output_index=len(self.output)-1, content_index=0, part=part)
        self.text += text
        self.emit("response.output_text.delta", item_id=self.message_id, output_index=self.output.index(next(x for x in self.output if x["id"] == self.message_id)), content_index=0, delta=text, logprobs=[])

    def add_call_delta(self, index: int, call_id=None, name=None, arguments=None):
        call = self.calls.setdefault(index, {"id": call_id or "call_" + uuid.uuid4().hex, "name": name or "", "arguments": ""})
        if call_id:
            call["id"] = call_id
        if name:
            call["name"] = name
        if arguments:
            call["arguments"] += arguments

    def feed_chat(self, event: dict):
        usage = event.get("usage")
        if isinstance(usage, dict):
            incoming = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            outgoing = usage.get("completion_tokens", usage.get("output_tokens", 0))
            self.usage = {"input_tokens": int(incoming or 0), "output_tokens": int(outgoing or 0), "total_tokens": int(incoming or 0) + int(outgoing or 0)}
            # OpenAI 的缓存命中明细折成 Anthropic 口径，Claude 客户端才能对账。
            details = usage.get("prompt_tokens_details")
            if isinstance(details, dict) and details.get("cached_tokens") is not None:
                self.usage["cache_read_input_tokens"] = int(details["cached_tokens"])
        choices = event.get("choices") or []
        for choice in choices:
            delta = choice.get("delta") or {}
            self.add_text(str(delta.get("content") or ""))
            thought = delta.get("reasoning_content") or delta.get("reasoning")
            if thought:
                self.reasoning += str(thought)
            for raw_call in delta.get("tool_calls") or []:
                fn = raw_call.get("function") or {}
                self.add_call_delta(int(raw_call.get("index") or 0), raw_call.get("id"), fn.get("name"), fn.get("arguments"))
            if choice.get("finish_reason"):
                self.finish_reason = choice["finish_reason"]

    def feed_anthropic(self, event: dict):
        kind = event.get("type")
        if kind == "message_start":
            usage = (event.get("message") or {}).get("usage") or {}
            self.usage["input_tokens"] = int(usage.get("input_tokens") or 0)
            # 提示缓存读数原样保留：Claude 客户端靠它对账成本。
            for name in ("cache_read_input_tokens", "cache_creation_input_tokens"):
                if usage.get(name) is not None:
                    self.usage[name] = int(usage[name])
        elif kind == "content_block_start":
            block = event.get("content_block") or {}
            if block.get("type") == "tool_use":
                self.add_call_delta(int(event.get("index") or 0), block.get("id"), block.get("name"), compact_json(block.get("input") or {}) if block.get("input") else "")
        elif kind == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta":
                self.add_text(str(delta.get("text") or ""))
            elif delta.get("type") == "input_json_delta":
                self.add_call_delta(int(event.get("index") or 0), arguments=str(delta.get("partial_json") or ""))
            elif delta.get("type") == "thinking_delta":
                self.reasoning += str(delta.get("thinking") or "")
        elif kind == "message_delta":
            usage = event.get("usage") or {}
            self.usage["output_tokens"] = int(usage.get("output_tokens") or 0)
            self.usage["total_tokens"] = self.usage["input_tokens"] + self.usage["output_tokens"]
            self.finish_reason = (event.get("delta") or {}).get("stop_reason")

    def finish(self):
        if self.message_open:
            index = next(i for i, item in enumerate(self.output) if item["id"] == self.message_id)
            item = self.output[index]
            item["status"] = "completed"
            item["content"][0]["text"] = self.text
            self.emit("response.output_text.done", item_id=self.message_id, output_index=index, content_index=0, text=self.text, logprobs=[])
            self.emit("response.content_part.done", item_id=self.message_id, output_index=index, content_index=0, part=item["content"][0])
            self.emit("response.output_item.done", output_index=index, item=item)
        for _, call in sorted(self.calls.items()):
            original, custom = self.names.decode(call["name"])
            arguments = call["arguments"] or "{}"
            if custom:
                try:
                    raw_input = json.loads(arguments).get("input", "")
                except json.JSONDecodeError:
                    raw_input = arguments
                item = {"id": "item_" + uuid.uuid4().hex, "type": "custom_tool_call", "status": "completed", "call_id": call["id"], "name": original, "input": raw_input}
            else:
                try:
                    json.loads(arguments)
                except json.JSONDecodeError as error:
                    raise ProtocolFailure("上游返回了无效的工具参数 JSON。", 502, "invalid_tool_arguments") from error
                tool_name, tool_ns = self.names.split_namespace(call["name"])
                item = {"id": "item_" + uuid.uuid4().hex, "type": "function_call", "status": "completed", "call_id": call["id"], "name": tool_name, "arguments": arguments}
                if tool_ns:
                    item["namespace"] = tool_ns
            self.output.append(item)
            index = len(self.output) - 1
            self.emit("response.output_item.added", output_index=index, item={**item, "status": "in_progress"})
            self.emit("response.output_item.done", output_index=index, item=item)
            if self.reasoning and self.reasoning_cache:
                self.reasoning_cache.put(call["id"], self.reasoning)
        response = self.response("completed")
        self.emit("response.completed", response=response)
        return response


def anthropic_terminal(event: dict) -> bool:
    return isinstance(event, dict) and event.get("type") == "message_stop"


# ---------------------------------------------------------------------------
# Anthropic Messages 入站适配（Claude Code → Relay）
#
# 公共侧原本只讲 Responses；Claude 客户端讲的是 Anthropic Messages。
# 入站时把 Messages 请求折成内部统一的 Responses 形状，出站再把 Responses
# 事件/终态翻回 Messages 形状——上游链路、重试、统计口径一行不动。
#
# 刻意的取舍：
# * reasoning/thinking 不向 Claude 客户端回放。Relay 拿不到 Anthropic 的
#   signature，伪造的 thinking 块对客户端是毒药；v1 一律不吐出 thinking。
# * count_tokens 给估算值（约 4 字符 ≈ 1 token）。Claude Code 的自动压缩
#   只看量级，给它精确值的唯一办法是转发上游，那会把"本地估算"变成
#   "每次都烧一次上游请求"——不值。
# ---------------------------------------------------------------------------


def _anthropic_inbound_text(role: str, text: str) -> dict:
    part_type = "output_text" if role == "assistant" else "input_text"
    return {"type": "message", "role": role,
            "content": [{"type": part_type, "text": text}]}


def _carry_cache_control(source_block: dict, target_part: dict) -> None:
    """把 Anthropic 的 cache_control 标记搬到内部 Responses 的 content part 上。

    提示缓存是 Claude Code 的成本命脉：ephemeral 标记决定上游能不能复用
    前缀。内部形状里它跟着 content part 走，出站时按上游协议决定去留。
    """
    control = source_block.get("cache_control") if isinstance(source_block, dict) else None
    if isinstance(control, dict) and control.get("type"):
        target_part["cache_control"] = {"type": str(control["type"])}


def _anthropic_inbound_block(role: str, block: dict) -> list:
    """一个 Anthropic 内容块 → 零到多个 Responses 输入项。"""
    kind = block.get("type")
    if kind == "text":
        item = _anthropic_inbound_text(role, str(block.get("text") or ""))
        _carry_cache_control(block, item["content"][0])
        return [item]
    if kind == "image":
        source = block.get("source") or {}
        if source.get("type") != "base64":
            raise ProtocolFailure("仅支持 base64 图片内容。", 400, "unsupported_image")
        media_type = str(source.get("media_type") or "image/png")
        data = str(source.get("data") or "")
        if not data:
            raise ProtocolFailure("图片内容缺少 base64 数据。", 400, "unsupported_image")
        return [{"type": "message", "role": role, "content": [
            {"type": "input_image", "image_url": f"data:{media_type};base64,{data}"}]}]
    if kind == "tool_use":
        if role != "assistant":
            raise ProtocolFailure("tool_use 块只能出现在 assistant 消息里。", 400,
                                  "invalid_message_shape")
        call = {"type": "function_call",
                "call_id": str(block.get("id") or ""),
                "name": str(block.get("name") or ""),
                "arguments": compact_json(block.get("input") or {})}
        _carry_cache_control(block, call)
        return [call]
    if kind == "tool_result":
        content = block.get("content")
        if isinstance(content, list):
            output = "".join(str(part.get("text") or "") for part in content
                             if isinstance(part, dict) and part.get("type") == "text")
        else:
            output = content if isinstance(content, str) else compact_json(content or "")
        return [{"type": "function_call_output",
                 "call_id": str(block.get("tool_use_id") or ""),
                 "output": output}]
    if kind in {"thinking", "redacted_thinking"}:
        # 历史里的思考块折成 reasoning 项的 summary：密文/签名对第三方上游
        # 没有意义，adapt_reasoning_input 会按上游口味二次处理。
        text = str(block.get("thinking") or "")
        return [{"type": "reasoning",
                 "summary": [{"type": "summary_text", "text": text}] if text else [],
                 "content": [], "encrypted_content": None}]
    if kind in {"server_tool_use", "web_search_tool_result"}:
        # 官方服务端工具的历史痕迹，转发给第三方上游没有对应物；静默丢弃
        # 比 400 好——否则带过一次 web search 的会话整段作废。
        return []
    raise ProtocolFailure(f"暂不支持内容块类型：{kind}", 400, "unsupported_content_block")


def _anthropic_inbound_message(role: str, content) -> list:
    if isinstance(content, str):
        return [_anthropic_inbound_text(role, content)]
    if not isinstance(content, list):
        raise ProtocolFailure("消息 content 必须是字符串或内容块数组。", 400,
                              "invalid_message_shape")
    items = []
    for block in content:
        if not isinstance(block, dict):
            raise ProtocolFailure("消息内容块必须是对象。", 400, "invalid_message_shape")
        items.extend(_anthropic_inbound_block(role, block))
    return items


def _anthropic_inbound_tools(tools) -> list:
    if not isinstance(tools, list):
        return []
    converted = []
    for tool in tools:
        if not isinstance(tool, dict) or not tool.get("name"):
            raise ProtocolFailure("工具定义必须包含 name。", 400, "invalid_tool")
        converted.append({
            "type": "function",
            "name": str(tool["name"]),
            "description": str(tool.get("description") or "")[:1024],
            "parameters": tool.get("input_schema") or {"type": "object", "properties": {}},
        })
    return converted


def _anthropic_inbound_tool_choice(choice):
    if not isinstance(choice, dict):
        return "auto"
    kind = choice.get("type")
    if kind == "any":
        return "required"
    if kind == "none":
        return "none"
    if kind == "tool" and choice.get("name"):
        return {"type": "function", "name": str(choice["name"])}
    return "auto"


def _anthropic_plain_text(content) -> str:
    """把一条消息的 content 压成纯文本（只取 text 块，其余类型丢弃）。

    仅用于「role=system 混在 messages 里」这一非标准形态：它要进 instructions，
    而 instructions 只接受字符串，工具块/图片块挪不过去，丢弃比 400 便宜。
    """
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        content = [content]
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
        elif block.get("type") == "thinking":
            # 思考块不进系统提示，但保留它后面的文本块顺序不受影响。
            continue
    return "\n\n".join(part for part in parts if part)


def anthropic_request_to_responses(body: dict) -> dict:
    """Claude 客户端的 Messages 请求 → 内部统一的 Responses 请求。"""
    if not isinstance(body, dict) or not isinstance(body.get("model"), str):
        raise ProtocolFailure("请求必须包含 model 字符串。")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ProtocolFailure("请求必须包含非空 messages 数组。", 400, "invalid_request")
    items = []
    # Claude Code 2.1.x 起会在 messages 数组末尾追加一条 role=system 的消息
    # （官方的 system 字段之外的第二处系统提示，用于背景任务/会话提醒）。
    # 它是系统语义而不是对话回合，折进 instructions；若按非法角色 400 掉，
    # 整个客户端会「Every request fails」，等于不能用。
    hoisted = []
    for message in messages:
        if not isinstance(message, dict):
            raise ProtocolFailure("messages 中存在无效项目。", 400, "invalid_request")
        role = message.get("role")
        if role in {"system", "developer"}:
            hoisted.append(_anthropic_plain_text(message.get("content")))
            continue
        if role not in {"user", "assistant"}:
            raise ProtocolFailure(f"不支持消息角色：{role}", 400, "invalid_request")
        items.extend(_anthropic_inbound_message(role, message.get("content")))
    system = body.get("system")
    instructions = ""
    if isinstance(system, str):
        instructions = system
    elif isinstance(system, list):
        instructions = "\n\n".join(
            str(block.get("text") or "") for block in system
            if isinstance(block, dict) and block.get("type") == "text")
    hoisted_text = "\n\n".join(part for part in hoisted if part.strip())
    if hoisted_text:
        instructions = f"{instructions}\n\n{hoisted_text}".strip() if instructions else hoisted_text
    payload = {"model": body["model"], "input": items, "stream": bool(body.get("stream"))}
    if instructions.strip():
        payload["instructions"] = instructions
    max_tokens = body.get("max_tokens")
    if isinstance(max_tokens, int) and not isinstance(max_tokens, bool) and max_tokens > 0:
        payload["max_output_tokens"] = max_tokens
    tools = _anthropic_inbound_tools(body.get("tools"))
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = _anthropic_inbound_tool_choice(body.get("tool_choice"))
    return payload


def estimate_tokens_for_messages(body: dict) -> int:
    """count_tokens 的本地估算：约 4 字符一个 token，只做量级参考。"""
    try:
        text = json.dumps(body, ensure_ascii=False)
    except (TypeError, ValueError):
        return 0
    # base64 图片块会让字符数虚高几个数量级，估算时截掉 data 字段的长度。
    return max(1, len(text) // 4)


_ANTHROPIC_ERROR_TYPES = {
    400: "invalid_request_error", 401: "authentication_error", 403: "permission_error",
    404: "not_found_error", 413: "request_too_large", 429: "rate_limit_error",
}


def anthropic_error_body(failure: ProtocolFailure) -> dict:
    """Anthropic 客户端认识的错误信封。"""
    return {"type": "error", "error": {
        "type": _ANTHROPIC_ERROR_TYPES.get(failure.status, "api_error"),
        "message": str(failure),
    }}


def _anthropic_stop_reason(response: dict, builder_reason: str | None) -> str:
    output = response.get("output") or []
    if any(isinstance(item, dict) and item.get("type") in _TOOL_CALL_TYPES for item in output):
        return "tool_use"
    if builder_reason in {"length", "max_tokens", "max_output_tokens"}:
        return "max_tokens"
    if response.get("status") == "incomplete":
        return "max_tokens"
    return "end_turn"


def anthropic_message_from_response(response: dict, model: str) -> dict:
    """非流式：Responses 终态 → Anthropic message JSON。"""
    content = []
    for item in response.get("output") or []:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "message":
            text = "".join(
                str(part.get("text") or "") for part in item.get("content") or []
                if isinstance(part, dict) and part.get("type") in {"output_text", "text"})
            if text:
                content.append({"type": "text", "text": text})
        elif kind in _TOOL_CALL_TYPES:
            try:
                arguments = json.loads(str(item.get("arguments") or "{}"))
            except json.JSONDecodeError:
                arguments = {}
            content.append({"type": "tool_use",
                            "id": str(item.get("call_id") or item.get("id") or ""),
                            "name": str(item.get("name") or ""),
                            "input": arguments})
        # reasoning 项不回放：没有 Anthropic signature 的 thinking 块对客户端是毒药。
    usage = response.get("usage") or {}
    final_usage = {"input_tokens": int(usage.get("input_tokens") or 0),
                   "output_tokens": int(usage.get("output_tokens") or 0)}
    # 缓存读数透传（非流式分支）：口径与流式 message_delta 一致。
    if usage.get("cache_read_input_tokens"):
        final_usage["cache_read_input_tokens"] = int(usage["cache_read_input_tokens"])
    if usage.get("cache_creation_input_tokens"):
        final_usage["cache_creation_input_tokens"] = int(usage["cache_creation_input_tokens"])
    return {
        "id": str(response.get("id") or "msg_" + uuid.uuid4().hex).replace("resp_", "msg_"),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": _anthropic_stop_reason(response, None),
        "stop_sequence": None,
        "usage": final_usage,
    }


class AnthropicClientWriter:
    """把内部 Responses 事件流转成 Anthropic Messages SSE，喂给 Claude 客户端。

    用法：``emit`` 替换 Responses 通道的事件出口；每个 Responses 事件进来，
    零到多个 Anthropic 事件出去。块序号按出现顺序重新编排（Anthropic 的 index
    从 0 连续编号，与 Responses 的 output_index 语义不同，不能直接照抄）。
    """

    def __init__(self, model: str, emit):
        self.model = model
        self._emit = emit  # 接受一个完整 Anthropic 事件 dict
        self.message_id = "msg_" + uuid.uuid4().hex
        self.started = False
        self._blocks = {}       # responses output_index -> anthropic index
        self._block_kinds = {}  # anthropic index -> "text" | "tool_use"
        self._next_index = 0
        self._usage_in = 0
        self._usage_out = 0
        self._usage_cache_read = 0
        self._usage_cache_creation = 0
        self._saw_tool_call = False
        self._closed = False

    def _open_message(self):
        if self.started:
            return
        self.started = True
        self._emit({"type": "message_start", "message": {
            "id": self.message_id, "type": "message", "role": "assistant",
            "model": self.model, "content": [], "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }})

    def _open_block(self, output_index: int, content_block: dict) -> int:
        self._open_message()
        index = self._next_index
        self._next_index += 1
        self._blocks[output_index] = index
        self._block_kinds[index] = content_block["type"]
        self._emit({"type": "content_block_start", "index": index,
                    "content_block": content_block})
        return index

    def _close_block(self, output_index: int):
        index = self._blocks.pop(output_index, None)
        if index is not None:
            self._emit({"type": "content_block_stop", "index": index})

    def _delta(self, output_index: int, delta: dict):
        index = self._blocks.get(output_index)
        if index is not None:
            self._emit({"type": "content_block_delta", "index": index, "delta": delta})

    def feed(self, event: dict) -> None:
        """消费一个 Responses 事件；未知事件静默跳过，与透传通道同款宽容。"""
        if self._closed or not isinstance(event, dict):
            return
        kind = event.get("type")
        if kind == "response.created":
            self._open_message()
            return
        if kind == "response.output_item.added":
            item = event.get("item") or {}
            output_index = int(event.get("output_index") or 0)
            item_kind = item.get("type")
            if item_kind == "message":
                self._open_block(output_index, {"type": "text", "text": ""})
            elif item_kind in _TOOL_CALL_TYPES:
                self._saw_tool_call = True
                self._open_block(output_index, {
                    "type": "tool_use",
                    "id": str(item.get("call_id") or item.get("id") or ""),
                    "name": str(item.get("name") or ""),
                    "input": {},
                })
            # reasoning 项：见模块 docstring，不向 Claude 客户端回放。
            return
        if kind == "response.output_text.delta":
            self._delta(int(event.get("output_index") or 0),
                        {"type": "text_delta", "text": str(event.get("delta") or "")})
            return
        if kind == "response.function_call_arguments.delta":
            self._delta(int(event.get("output_index") or 0),
                        {"type": "input_json_delta",
                         "partial_json": str(event.get("delta") or "")})
            return
        if kind in {"response.output_item.done", "response.content_part.done"}:
            self._close_block(int(event.get("output_index") or 0))
            return
        if kind in {"response.completed", "response.incomplete", "response.failed"}:
            response = event.get("response") or {}
            usage = response.get("usage") or {}
            self._usage_in = int(usage.get("input_tokens") or 0)
            self._usage_out = int(usage.get("output_tokens") or 0)
            # 提示缓存读数透传给 Claude 客户端（Anthropic 口径）。
            self._usage_cache_read = int(usage.get("cache_read_input_tokens") or 0)
            self._usage_cache_creation = int(usage.get("cache_creation_input_tokens") or 0)
            self.finish(response)
            return

    def finish(self, response: dict) -> None:
        """收尾：关掉还开着的块，发 message_delta + message_stop。"""
        if self._closed:
            return
        self._closed = True
        self._open_message()
        for output_index in list(self._blocks):
            self._close_block(output_index)
        final_usage = {"input_tokens": self._usage_in,
                       "output_tokens": self._usage_out}
        # 缓存读数只在非零时带出：老客户端对未知 usage 字段宽容，
        # 但零值字段会让 Claude Code 的成本对账多出无意义的 0 行。
        if self._usage_cache_read:
            final_usage["cache_read_input_tokens"] = self._usage_cache_read
        if self._usage_cache_creation:
            final_usage["cache_creation_input_tokens"] = self._usage_cache_creation
        self._emit({"type": "message_delta", "delta": {
            "stop_reason": _anthropic_stop_reason(
                response, "length" if response.get("status") == "incomplete" else None),
            "stop_sequence": None,
        }, "usage": final_usage})
        self._emit({"type": "message_stop"})
