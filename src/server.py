# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Authenticated loopback gateway for MicroGlow Relay."""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import threading
import time
from urllib.parse import urlsplit

import httpx

from adapters import (AnthropicClientWriter, ProtocolFailure, ResponseBuilder,
                      adapt_reasoning_input, anthropic_error_body,
                      anthropic_message_from_response, anthropic_request_to_responses,
                      anthropic_terminal, compact_json, estimate_tokens_for_messages,
                      prepare_request, read_sse, repair_tools_from_error,
                      apply_lessons, lesson_actions_from_error)
from records import ActivityLog, ReasoningCache
from trip_ledger import TripLedger
from telemetry.store import error_category_for_status
from storage import (APP_NAME, ENDPOINT_SUFFIXES, ROUTER_MODEL, VERSION,
                    is_retired_router_model, redact)
from channels import ChannelRouter
from model_names import resolve_friendly
from native_models import is_native_slug, native_profile, resolve_native_target
from telemetry import (
    HttpTelemetryUploadClient,
    TelemetryRuntime,
    client_version as telemetry_client_version,
    classify_call_channel,
    model_dimension,
    provider_key,
)


def _as_count(value) -> int | None:
    """Non-negative integer, or `None` when the value is unusable."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def usage_detail_counts(usage) -> tuple[int | None, int | None]:
    """上游上报的「缓存命中的输入 token」与「推理 token」，没上报就返回 None。

    各家字段名不统一，一次认全（实测 api.deepseek.com 的 responses 通道确实会给
    ``input_tokens_details.cached_tokens``）：

    * responses：``input_tokens_details.cached_tokens`` / ``output_tokens_details.reasoning_tokens``
    * chat：``prompt_tokens_details.cached_tokens`` / ``completion_tokens_details.reasoning_tokens``
    * 深度探索原生 chat：``prompt_cache_hit_tokens``
    * Anthropic：``cache_read_input_tokens``

    ``None`` 与 ``0`` 语义不同：``0`` 表示上游明确说了「这一笔没有命中」，
    ``None`` 表示无从得知。统计口径据此把没上报的请求排除在分母之外。
    """
    if not isinstance(usage, dict):
        return None, None
    cached = None
    for name in ("input_tokens_details", "prompt_tokens_details"):
        block = usage.get(name)
        if isinstance(block, dict) and block.get("cached_tokens") is not None:
            cached = _as_count(block.get("cached_tokens"))
            if cached is not None:
                break
    for name in ("prompt_cache_hit_tokens", "cache_read_input_tokens"):
        if cached is None and usage.get(name) is not None:
            cached = _as_count(usage.get(name))
    reasoning = None
    for name in ("output_tokens_details", "completion_tokens_details"):
        block = usage.get(name)
        if isinstance(block, dict) and block.get("reasoning_tokens") is not None:
            reasoning = _as_count(block.get("reasoning_tokens"))
            if reasoning is not None:
                break
    return cached, reasoning


ERROR_HINTS = {
    400: "请求参数或协议与供应商不兼容",
    401: "API Key 无效",
    402: "供应商账户余额不足",
    403: "账户无权访问该模型",
    404: "接口地址或模型名称不存在",
    408: "供应商处理超时",
    409: "供应商拒绝当前请求状态",
    422: "供应商无法处理请求内容",
    429: "供应商限流",
    500: "供应商内部错误",
    502: "供应商网关错误",
    503: "供应商服务暂不可用",
    504: "供应商网关超时",
    520: "上游网关异常",
    521: "上游站点不可用",
    522: "上游连接超时",
    523: "上游地址不可达",
    524: "上游网关等待响应超时",
    525: "上游 TLS 握手失败",
    526: "上游 TLS 证书无效",
    527: "上游网关错误",
    530: "上游服务错误",
}

# 供应商把自己「临时故障」包在 400 里返回时的自述模板。
# 实测 mlxz.cc 在自家上游卡死/超时后，用一条顶层 400 兜底，正文却写着
# 「请求未能完成…请…重试」；这类 400 与真正的参数错必须分开处理。
# 只有命中这里的说法、且没有命中 PARAM_DEFECT_400_SIGNATURES，才允许窄口径重放。
# 表集中在这里，便于审计：想收紧或放宽只改这一处。
TRANSIENT_400_SIGNATURES = (
    # 英文
    re.compile(r"temporar", re.I),
    re.compile(r"try\s+again|please\s+retry|retry\s+(?:later|the\s+request|your\s+request)", re.I),
    re.compile(r"timed?\s*out|\btimeout\b", re.I),
    re.compile(r"rate\s*limit|too\s+many\s+requests", re.I),
    re.compile(r"overload", re.I),
    re.compile(r"service\s+(?:is\s+)?(?:busy|unavailable|temporary\w*|overload\w*)", re.I),
    re.compile(r"upstream\s+(?:error|failed|failure|timeout|unavailable|unreachable)", re.I),
    re.compile(r"internal\s+(?:server\s+)?error", re.I),
    re.compile(r"currently\s+unavailable", re.I),
    re.compile(r"\bgateway\b", re.I),
    # 中文
    re.compile(r"稍(?:后|候)(?:再)?重试|请(?:稍后|稍候|重新)?重试"),
    re.compile(r"繁忙|过载|拥塞"),
    re.compile(r"超时"),
    re.compile(r"限流|频率限制|请求过快"),
    re.compile(r"暂时(?:不可用|无法|故障|异常)|临时(?:故障|错误|不可用|异常)"),
    re.compile(r"服务(?:器)?(?:暂不可用|暂时不可用|不可用|异常|故障|错误)"),
    re.compile(r"上游(?:异常|错误|失败|超时|不可用|无响应)"),
    re.compile(r"网关(?:异常|错误|超时|无响应)"),
    re.compile(r"请求未能完成"),
)
# 明确指向「参数 / 模型 / 请求结构」缺陷的措辞。判定顺序固定为「先查本表」：
# 命中即直抛，任何瞬时模板都不得触发重放，普通参数错永远不会被重试。
PARAM_DEFECT_400_SIGNATURES = (
    re.compile(r"model\s+(?:not\s+found|does\s+not\s+exist|is\s+not\s+supported|unsupported)", re.I),
    re.compile(r"unknown\s+model|invalid\s+model", re.I),
    re.compile(r"无效(?:的)?模型|模型(?:不存在|未找到|无效|不支持)|不支持的模型"),
    re.compile(r"invalid[\s_-]?(?:api[\s_-]?key|token|authentication|credential)", re.I),
    re.compile(r"invalid[\s_-]?(?:parameter|argument|request|schema|field|type|value)", re.I),
    re.compile(r"(?:参数|字段|请求体|请求参数)(?:错误|无效|不合法|缺失|格式)|缺少(?:参数|字段)|必填"),
    re.compile(r"no\s+(?:tool\s+output|tool\s+call\s+output)\s+found", re.I),
    re.compile(r"reasoning_text|reasoning\s+(?:item|content|part)", re.I),
    re.compile(r"must\s+be\s+passed\s+back", re.I),
    re.compile(r"context\s+(?:length|window)|maximum\s+context|上下文(?:长度)?超限"),
    re.compile(r"content\s+(?:filter|policy)|内容(?:审核|不合规)"),
)
# 400 命中瞬时模板但重放仍失败时，不能再让用户去查「参数不兼容」。
TRANSIENT_400_HINT = "上游临时故障（供应商以 400 返回），请稍后重试"
# 400 窄口径重放的固定间隔；与状态重试共用次数预算。
SIGNED_400_RETRY_DELAY_SECONDS = 1.0

RETRYABLE_PRESTREAM_STATUSES = frozenset({429, 500, 502, 503, 504, 520, 521, 522, 523, 524})
MAX_UPSTREAM_ATTEMPTS = 2
# 连接层抖动（TLS 握手被重置、连接被拒等）单独给一份重试预算，
# 否则上游偶发抽风会被放大成客户端的硬失败。
RETRYABLE_TRANSPORT_ERRORS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
    httpx.ProxyError,
)
MAX_TRANSPORT_ATTEMPTS = 3
TRANSPORT_RETRY_BASE_SECONDS = 0.75
TRANSPORT_RETRY_CAP_SECONDS = 4.0
# Leave a margin below the 300-second idle limit advertised to Codex.
UPSTREAM_TOTAL_BUDGET_SECONDS = 285.0
MAX_RETRY_AFTER_SECONDS = 5.0
MIN_NEXT_ATTEMPT_SECONDS = 10.0
# 慢通道（K3 这类一次要跑 100s+ 才回错的）保护。取舍写在 docs 报告里：
#   * 总预算不抬高：285s 是给 Codex 侧 300s 空闲上限刻意留的余量；
#   * 第一次尝试封顶，把重放切片显式留出来——否则第一次拖到 200s+ 时重放只剩 <85s，
#     撞总时限会退化成比原错误更难解释的 504；
#   * 重放准入线从 MIN_NEXT_ATTEMPT_SECONDS(10s) 抬到 MIN_RETRY_SLICE_SECONDS：
#     低于这个切片宁可不开重放，也不打一场注定超时的仗。
MIN_RETRY_SLICE_SECONDS = 90.0
# 切出重放空间的固定余量：覆盖上游可能要求的 Retry-After 上限与调度抖动，
# 保证「第一次尝试打满封顶」后仍能留出完整的 MIN_RETRY_SLICE_SECONDS。
RETRY_RESERVE_SECONDS = MAX_RETRY_AFTER_SECONDS + 5.0
UPSTREAM_FIRST_ATTEMPT_SECONDS = (
    UPSTREAM_TOTAL_BUDGET_SECONDS - MIN_RETRY_SLICE_SECONDS - RETRY_RESERVE_SECONDS
)
# 瞬时签名类在坏窗口里会连着失败（实测 10-12 16:48:12 与 16:48:39 连续两次 400），
# 只多打一次不够：这一类给到 3 次尝试，其余可重试状态维持 2 次。
MAX_TRANSIENT_ATTEMPTS = 3
TRANSIENT_RETRY_STATUSES = frozenset({500})
MAX_REQUEST_BYTES = 32 * 1024 * 1024
# 提前拒绝时最多排空的请求体字节数，避免客户端拿到连接重置而不是错误响应。
MAX_DRAIN_BYTES = 64 * 1024 * 1024
# 图像生成入口：与 /v1/responses、/v1/messages 并列，但不是 SSE 流。
# 只做 JSON 透传，走独立 handler，绝不进入 prepare_request 的流式管道。
IMAGES_PATHS = frozenset({
    "/images/generations", "/v1/images/generations",
    "/images/edits", "/v1/images/edits",
})
# 图像生成通常比文本慢一个量级；仍留在 300s 客户端静默上限内。
IMAGE_UPSTREAM_TIMEOUT_SECONDS = 240.0
# 「完整生成端点 → 站根」的识别表，供 /models 发现用；图像端点也在内。
TEXT_AND_IMAGE_SUFFIXES = ("/chat/completions", "/responses", "/messages",
                           "/images/generations", "/images/edits")
# 原生直通要跟着 Codex 自己的请求头走：官方后端按这些头识别会话与功能开关，
# 换掉轻则降级，重则拒收。
NATIVE_PASSTHROUGH_HEADERS = (
    "x-codex-beta-features",
    "x-codex-window-id",
    "x-codex-turn-metadata",
    "x-openai-internal-codex-responses-lite",
    "x-client-request-id",
    "session-id",
    "thread-id",
    "originator",
    "user-agent",
)
# 上游并发上限：每条长流会占满一个槽位直到结束。
MAX_UPSTREAM_CONCURRENCY = 16
SLOT_WAIT_SECONDS = 30.0
REQUEST_READ_TIMEOUT_SECONDS = 30.0
RESPONSE_SOCKET_TIMEOUT_SECONDS = 300.0
# 退出时同步等待上传线程的时间；剩余预算交给非守护线程在解释器退出前跑完。
TELEMETRY_EXIT_JOIN_SECONDS = 1.5
# 停机时给在途流的时间上限；超过就强断，避免退出卡住。
STOP_DRAIN_SECONDS = 5.0
LOCAL_RESTART_MESSAGE = "本地服务正在停止，本次请求已中断。"


def _status_attempt_budget(status: int) -> int:
    """一次客户端请求内允许的上游尝试次数（含第一次）。"""
    return MAX_TRANSIENT_ATTEMPTS if status in TRANSIENT_RETRY_STATUSES else MAX_UPSTREAM_ATTEMPTS


def _retry_delay(status: int, headers, attempt: int) -> float | None:
    if status not in RETRYABLE_PRESTREAM_STATUSES or attempt >= _status_attempt_budget(status):
        return None
    retry_after = str(headers.get("Retry-After", "")).strip()
    if retry_after:
        # An HTTP-date or a long server-requested delay must not be ignored.
        try:
            delay = float(retry_after)
        except ValueError:
            return None
        if not 0 <= delay <= MAX_RETRY_AFTER_SECONDS:
            return None
        return delay
    return 1.0


def _transport_retry_delay(attempt: int, deadline: float) -> float | None:
    """Backoff for failures raised before any upstream response header arrives."""
    if attempt >= MAX_TRANSPORT_ATTEMPTS:
        return None
    delay = min(TRANSPORT_RETRY_BASE_SECONDS * (2 ** (attempt - 1)), TRANSPORT_RETRY_CAP_SECONDS)
    if deadline - time.monotonic() < delay + MIN_NEXT_ATTEMPT_SECONDS:
        return None
    return delay


def _transient_400_error(detail: str) -> bool:
    """上游是否用 400 自认「临时失败」（而不是指出请求哪里不对）。

    判定顺序固定：先排除明确指向参数/模型/结构的正文，再看是否命中瞬时模板。
    普通参数错必须直抛，绝不能因为正文里带「重试」二字就被误判成瞬时故障。
    """
    text = detail or ""
    if not text:
        return False
    if any(pattern.search(text) for pattern in PARAM_DEFECT_400_SIGNATURES):
        return False
    return any(pattern.search(text) for pattern in TRANSIENT_400_SIGNATURES)


def _signed_400_retry_delay(attempt: int, deadline: float) -> float | None:
    """400 命中瞬时模板时的窄口径重放预算。

    次数上限与 500 一致（``MAX_TRANSIENT_ATTEMPTS``）；并且必须在总时限内留出
    完整的 ``MIN_RETRY_SLICE_SECONDS`` 重放切片，否则不重放。
    """
    if attempt >= MAX_TRANSIENT_ATTEMPTS:
        return None
    if deadline - time.monotonic() < SIGNED_400_RETRY_DELAY_SECONDS + MIN_RETRY_SLICE_SECONDS:
        return None
    return SIGNED_400_RETRY_DELAY_SECONDS


def _upstream_error_detail(response: httpx.Response) -> str:
    """Read and parse an error body once, for both retry decisions and reporting."""
    try:
        raw = response.read()
    except Exception:
        return ""
    try:
        body = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return ""
    if not isinstance(body, dict):
        return ""
    error = body.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or "")
    if isinstance(error, str):
        return error
    if isinstance(body.get("message"), str):
        return body["message"]
    return ""


def _event_error_text(event: dict) -> str:
    """Provider wording from either error shape seen in the wild.

    The Responses spec carries it as ``{"type": "error", "message": ...}``, but a
    number of relays wrap it as ``{"type": "error", "error": {"message": ...}}``.
    Reading only the flat field silently downgraded the provider's own sentence to
    a generic one, which is exactly the detail a user needs to fix their setup.
    """
    error = event.get("error")
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])
    if isinstance(error, str) and error:
        return error
    return str(event.get("message") or "")


def _block_error_text(payload) -> str:
    """Error wording hidden in a stream block that carries no event type.

    Relays report mid-stream failures as a bare ``data: {"error": {...}}``. That
    block is not a Responses event, so there is no ``type`` to dispatch on; the
    payload itself is the only signal, and dropping it turned a precise provider
    complaint into an unexplainable 502.
    """
    if isinstance(payload, dict):
        if "error" in payload or "message" in payload:
            return _event_error_text(payload)
    return ""


def _unresolved_profile(model: str) -> dict:
    """Accounting stand-in for a request rejected before any provider was picked.

    The attempt still belongs in the local usage totals, otherwise it is missing
    from the success-rate denominator. It carries no provider and no model, so it
    never shows up as a provider share and is never sent to telemetry.
    """
    return {"id": "", "provider_name": "", "provider": "", "model": "",
            "requested_model": model}


# ---------------------------------------------------------------------------
# 推理项形态自修复的判定表
#
# 上游用一句人话告诉我们“上一轮的推理项形态不对”。旧实现靠两条英文短语做
# 子串匹配：上游换一种说法就静默失效——用户直接吃到原始 400，relay 一个字
# 都不记。这里把判定收成一个配置点，并放宽到语义级措辞。
#
# 两条硬约束：
#   * 只在 400 上判定，且只在建流前，所以重放永远安全；
#   * summary 方向会剥离 reasoning_text，误判代价高，所以只认明确的否定语义。
# ---------------------------------------------------------------------------
REASONING_SHAPE_RULES = (
    ("text", re.compile(
        r"must be passed back"
        r"|must be sent back"
        r"|needs? to be (?:passed|sent) back"
        r"|must be passed (?:to|into) the"
        r"|(?:reasoning|thinking)[\w\- ]{0,24}?(?:content|text|field|item|part)"
        r"[\w\- ]{0,24}?(?:is\s+)?(?:required|missing|absent|empty)"
        r"|required\s+(?:for|in|by)\s+thinking"
        r"|thinking\s+mode\s+require"
        r"|requires?\s+the\s+reasoning"
        r"|reasoning\s+(?:content|text)\s+to\s+be\s+returned"
        r"|必须(?:回传|传回|返回|带上)"
        r"|缺少\s*推理", re.I)),
    ("summary", re.compile(
        r"unsupported\s+content\s+type"
        r"|(?:content\s+type|type)\s+(?:is\s+)?not\s+supported"
        r"|(?:does\s+not|doesn't|do\s+not)\s+support\s+reasoning"
        r"|reasoning_text\s+is\s+not\s+(?:a\s+)?supported"
        r"|(?:不支持的|非法)(?:内容类型|的?\s*reasoning)"
        r"|不支持[\w\s]{0,12}(?:reasoning_text|推理文本)", re.I)),
)
# 只有描述里出现推理/思考语境才进入判定，避免误伤无关的 400。
REASONING_SHAPE_CONTEXT = re.compile(
    r"reasoning[_\- ]?(?:text|content|item|part)|thinking\s*mode|推理|思考模式", re.I)


def _reasoning_fix_mode(detail: str) -> str:
    """Resolve the repair direction implied by an upstream 400 body."""
    text = detail or ""
    if not REASONING_SHAPE_CONTEXT.search(text):
        return ""
    for mode, pattern in REASONING_SHAPE_RULES:
        if pattern.search(text):
            return mode
    return ""


# SSE 首事件预取开关：关掉就回到「上游一返 2xx 就提交客户端响应头」的旧行为。
PREFETCH_SSE_FIRST_EVENT = True


def _prefetch_first_event(lines) -> list:
    """Read lines up to the end of the first real SSE event.

    ``lines`` is the response's one and only line iterator: httpx refuses to
    hand out a second one, so it must be consumed here and then handed back to
    the caller for ``read_sse`` to finish. Returns the buffered lines. Raises
    the underlying transport error when the connection dies before any payload
    line arrives, so the retry logic sees it exactly like a failure that
    happened before any response header.
    """
    buffered = []
    for raw in lines:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
        buffered.append(line)
        if not line.strip() and any(entry.startswith("data:") for entry in buffered):
            return buffered
    if any(entry.startswith("data:") for entry in buffered):
        return buffered
    raise httpx.RemoteProtocolError("上游在返回任何事件数据前就关闭了连接。")


def _replay(primed, lines):
    """Yield the pre-read lines before the live stream so nothing is lost."""
    for line in primed:
        yield line
    for line in lines:
        yield line


@contextmanager
def _upstream_stream(client, profile: dict, payload: dict, deadline: float, on_retry,
                     on_note=None, prefetch=None):
    """Retry rejected response headers or pre-response connection failures.

    Retries are allowed only before a response has been committed to the
    client. Once the caller has started streaming, all errors belong to the
    caller and are never replayed. A retry may still repeat upstream
    computation/cost.

    ``prefetch`` 把「提交客户端响应头」这一步推迟到上游真的吐出第一个 SSE
    事件之后：上游在 2xx 之后立刻断流时，客户端拿到的是一个可重试的干净
    错误，而不是一个已经写了一半的 200 流。代价是客户端看到响应头的时刻
    会晚到上游首个事件为止（慢思考上游的 TTFB 会抬高）。

    A 400 that complains about the reasoning-item shape is repaired once and
    replayed: it is rejected before any byte is streamed, so replay is safe, and
    it lets already-damaged histories recover without manual repair.
    """
    if prefetch is None:
        prefetch = PREFETCH_SSE_FIRST_EVENT
    status_attempt = 0
    transport_attempt = 0
    delivered = False
    reasoning_repaired = False
    tools_repaired = False
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProtocolFailure("上游请求总时限已用尽。", 504, "upstream_timeout")
        status_attempt += 1
        # 第一次尝试封顶，把重放切片留给后面；后续尝试用掉剩余的全部时间。
        # deadline 本身不动，所以客户端侧的总静默时长照样封在 285s 内。
        attempt_budget = min(remaining, UPSTREAM_FIRST_ATTEMPT_SECONDS) if status_attempt == 1 else remaining
        timeout = httpx.Timeout(attempt_budget, connect=min(20.0, attempt_budget))
        try:
            with client.stream(
                "POST", profile["base_url"], headers=upstream_headers(profile),
                json=payload, timeout=timeout,
            ) as upstream:
                if 200 <= upstream.status_code < 300:
                    # 非 SSE 的 200 必须在预取之前排除：它的 body 不是事件流，
                    # 预取只会读到 EOF 并把一个干净的 502 退化成传输层重试。
                    # ChatGPT 官方后端不回 Content-Type（实测 200 + 裸 SSE），
                    # 原生直通不能拿这个头做判据。
                    content_type = upstream.headers.get("Content-Type", "").lower()
                    if ("text/event-stream" not in content_type
                            and not profile.get("_native_passthrough")):
                        upstream.read()
                        raise ProtocolFailure("上游 HTTP 200，但没有返回 SSE 流。", 502, "not_sse")
                    lines = upstream.iter_lines()
                    primed = _prefetch_first_event(lines) if prefetch else []
                    delivered = True
                    yield upstream, status_attempt, primed, lines
                    return
                status_code = int(upstream.status_code)
                # 400 的正文既用于推理项形态判定，也用于瞬时签名判定；只读一次。
                detail = _upstream_error_detail(upstream) if status_code in (400, 422) else ""
                # 第 1 层反应式兼容：上游 400/422 指向工具字段时，读错误定点降级重试一次。
                # 不预判 Codex 新字段，未知妖蛾子靠上游报错自修复，保活不炸。
                if not tools_repaired and status_code in (400, 422) and detail:
                    adapted, tchanged = repair_tools_from_error(payload, detail)
                    if tchanged:
                        payload = adapted
                        tools_repaired = True
                        status_attempt -= 1
                        # 记住教训：下次同供应商×模型 预洗，不再白打。
                        acts = lesson_actions_from_error(detail)
                        if acts:
                            try:
                                self_settings = getattr(getattr(self, "server", None), "gateway", None)
                                if self_settings is not None:
                                    self_settings.settings.record_shape_lesson(
                                        profile.get("provider_name") or profile.get("provider") or "",
                                        profile.get("model") or "", acts)
                            except Exception:
                                pass
                        on_retry(status_code, 0, 0.0, None,
                                 "工具形状已按上游报错自适应降级 · 立即重试")
                        continue
                transient_400 = status_code == 400 and _transient_400_error(detail)
                if not reasoning_repaired and status_code == 400:
                    shaping = _reasoning_fix_mode(detail)
                    if shaping:
                        adapted, changed = adapt_reasoning_input(payload, profile, force=shaping)
                        if changed:
                            payload = adapted
                            reasoning_repaired = True
                            status_attempt -= 1
                            on_retry(400, 0, 0.0, None,
                                     "推理项形态已按供应商适配（%s）· 立即重试" % shaping)
                            continue
                        if on_note is not None:
                            # 以前这里什么都不记：上游换一句说法，用户直接吃 400。
                            # 实时日志只留分类结论：上游正文只能进脱敏后的活动记录，
                            # 不得进实时事件通道（tests/test_ui_polish_006.py 守着这条）。
                            on_note("上游 400 命中推理项形态提示（%s），但请求里没有可适配的推理项，"
                                    "未重放" % shaping)
                    elif on_note is not None and not transient_400:
                        on_note("上游 400 未命中推理项形态提示，未重放%s"
                                % ("（正文含推理相关字样）"
                                   if REASONING_SHAPE_CONTEXT.search(detail or "") else ""))
                if transient_400:
                    # 窄口径签名重放：只有上游正文自认「瞬时失败」才重放（最多 3 次尝试），
                    # 明确指向参数/模型/结构的 400 一律直抛（PARAM_DEFECT_400_SIGNATURES）。
                    delay = _signed_400_retry_delay(status_attempt, deadline)
                    if delay is not None:
                        on_retry(400, status_attempt, delay, None,
                                 "上游 400 自认瞬时失败 · 发送客户端响应前重放一次")
                    # 注意：实时日志只留分类结论，绝不带上游正文。
                    elif on_note is not None:
                        on_note("上游 400 自认瞬时失败，但重放预算已用尽，未重放")
                elif status_code == 400:
                    delay = None
                else:
                    delay = _retry_delay(status_code, upstream.headers, status_attempt)
                    # 准入线用重放切片，而不是 10s 的「够发一次请求」下限：
                    # 慢通道下 10s 切片等于白打一次。
                    if delay is not None and deadline - time.monotonic() < delay + MIN_RETRY_SLICE_SECONDS:
                        delay = None
                    if delay is not None:
                        on_retry(status_code, status_attempt, delay, None)
                if delay is None:
                    upstream.read()
                    raise upstream_error(upstream, profile)
        except RETRYABLE_TRANSPORT_ERRORS as error:
            # 还没有任何一个字节交给客户端，重放是安全的；已经 yield 过就绝不重放。
            if delivered:
                raise
            status_attempt -= 1
            transport_attempt += 1
            delay = _transport_retry_delay(transport_attempt, deadline)
            if delay is None:
                raise
            on_retry(None, transport_attempt, delay, error)
            time.sleep(delay)
            continue
        time.sleep(delay)


def upstream_headers(profile: dict) -> dict:
    if profile.get("_native_passthrough"):
        # 认证用本机 Codex 的登录态；客户端头原样带上，让官方后端看到的
        # 就是 Codex 自己发的请求。Relay 只换出口，不改会话身份。
        auth = profile.get("_native_auth") or {}
        client = profile.get("_client_headers") or {}
        headers = {"Accept": "text/event-stream", "Content-Type": "application/json"}
        for name in NATIVE_PASSTHROUGH_HEADERS:
            value = client.get(name)
            if value:
                headers[name] = value
        headers["Authorization"] = "Bearer " + str(auth.get("access_token") or "")
        headers["chatgpt-account-id"] = str(auth.get("account_id") or "")
        return headers
    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
        "User-Agent": f"MicroGlowRelay/{VERSION}",
    }
    key = profile.get("api_key", "")
    if profile["protocol"] == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
        if key:
            headers["x-api-key"] = key
    elif key:
        headers["Authorization"] = "Bearer " + key
    return headers


def upstream_error(response: httpx.Response, profile: dict) -> ProtocolFailure:
    status = int(response.status_code)
    detail = ""
    try:
        body = response.json()
        error = body.get("error")
        if isinstance(error, dict):
            detail = str(error.get("message") or "")
        elif isinstance(error, str):
            detail = error
        elif isinstance(body.get("message"), str):
            detail = body["message"]
    except Exception:
        pass
    title = ERROR_HINTS.get(status, "供应商拒绝请求")
    if profile.get("_native_passthrough"):
        # 直通没有 API Key 可改：401/403 只能是登录态问题，别把用户引向配置页。
        if status == 401:
            title = "Codex 登录态已失效，请在 Codex 中重新登录"
        elif status == 403:
            title = "Codex 登录态无权访问该原生模型（可能套餐未包含）"
    if status == 400 and _transient_400_error(detail):
        # 上游把自己「临时故障」包成 400：别再用「参数不兼容」把用户赶去改配置。
        title = TRANSIENT_400_HINT
    message = title + (f"：{detail[:500]}" if detail else "")
    return ProtocolFailure(redact(message, profile.get("api_key", "")), status, "upstream_error")


class Handler(BaseHTTPRequestHandler):
    # 本连接当前请求的客户端协议："responses"（默认）| "anthropic"。
    # 决定错误信封与流事件的形状；每个 do_POST 开头都会重设。
    client_protocol = "responses"

    protocol_version = "HTTP/1.1"
    server_version = f"MicroGlowRelay/{VERSION}"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(REQUEST_READ_TIMEOUT_SECONDS)
        self.streaming_started = False

    def log_message(self, *args):
        return

    def _declared_length(self):
        raw = self.headers.get("Content-Length")
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _is_chunked(self):
        return "chunked" in str(self.headers.get("Transfer-Encoding", "")).lower()

    def _read_chunked_body(self, limit):
        """Read a chunked request body; ``None`` when it exceeds ``limit``.

        A client or a local proxy that streams the body sends no
        Content-Length. Rejecting those outright with "Content-Length 无效"
        blamed the caller for a request this self.server.gateway simply refused to read.
        """
        total = bytearray()
        while True:
            line = self.rfile.readline(128)
            if not line:
                raise ProtocolFailure("请求体读取不完整。")
            try:
                size = int(line.split(b";", 1)[0].strip() or b"0", 16)
            except ValueError:
                raise ProtocolFailure("分块请求体格式无效。") from None
            if size <= 0:
                # 结束块之后可能还有 trailer，读到空行为止再返回。
                while True:
                    trailer = self.rfile.readline(1024)
                    if not trailer or trailer in (b"\r\n", b"\n"):
                        break
                return bytes(total)
            if limit is not None and len(total) + size > limit:
                return None
            chunk = self.rfile.read(size)
            if len(chunk) != size:
                raise ProtocolFailure("请求体读取不完整。")
            total += chunk
            self.rfile.readline(2)  # 分块数据之后的 CRLF

    def _discard_request_body(self, length):
        """Drain a declared body before an early return.

        Closing the socket while the client is still uploading surfaces as a
        connection reset on the client instead of the real error response.
        """
        if self._is_chunked():
            try:
                self._read_chunked_body(MAX_DRAIN_BYTES)
            except (ProtocolFailure, OSError, ValueError):
                pass
            return
        if not isinstance(length, int) or length <= 0:
            return
        remaining = min(length, MAX_DRAIN_BYTES)
        while remaining > 0:
            try:
                chunk = self.rfile.read(min(remaining, 1 << 20))
            except (OSError, ValueError):
                break
            if not chunk:
                break
            remaining -= len(chunk)

    def _read_bounded_body(self, chunked: bool, length):
        """给不入主流程的小端点（count_tokens）读请求体；出错时已回复，返回 None。"""
        try:
            if chunked:
                raw = self._read_chunked_body(MAX_REQUEST_BYTES)
                if raw is None:
                    self._discard_request_body(None)
                    self._error(ProtocolFailure("请求体超过 32 MB 上限。", 413, "body_too_large"))
                    return None
                return raw
            if length is None:
                self._error(ProtocolFailure("Content-Length 无效。"))
                return None
            if length <= 0:
                self._error(ProtocolFailure("请求体为空。", 400, "empty_body"))
                return None
            if length > MAX_REQUEST_BYTES:
                self._discard_request_body(length)
                self._error(ProtocolFailure("请求体超过 32 MB 上限。", 413, "body_too_large"))
                return None
            raw = self.rfile.read(length)
            if len(raw) != length:
                self._error(ProtocolFailure("请求体读取不完整。"))
                return None
            return raw
        except (ProtocolFailure, OSError, ValueError):
            return None

    def _write_json(self, status: int, body: dict):
        payload = compact_json(body).encode("utf-8")
        with self.server.gateway.lock:
            self.server.gateway.output_bytes += len(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        self.wfile.write(payload)

    def _error(self, failure: ProtocolFailure):
        if self.client_protocol == "anthropic":
            self._write_json(failure.status, anthropic_error_body(failure))
            return
        self._write_json(failure.status, {
            "error": {
                "message": str(failure),
                "type": "microglow_relay_error",
                "code": failure.code,
            }
        })

    def _write_raw(self, status: int, payload: bytes, content_type: str):
        """原样回传上游响应体（图像 base64 不再解码重编码）。"""
        with self.server.gateway.lock:
            self.server.gateway.output_bytes += len(payload)
        self.send_response(status)
        self.send_header("Content-Type", content_type or "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        self.wfile.write(payload)

    def _authorized(self):
        if self.headers.get("Origin"):
            self._error(ProtocolFailure("拒绝浏览器跨站请求。", 403, "origin_rejected"))
            return False
        expected = "Bearer " + self.server.token
        if not hmac.compare_digest(self.headers.get("Authorization", ""), expected):
            self._error(ProtocolFailure("本地访问令牌无效。", 401, "local_auth_failed"))
            return False
        return True

    # ── 图像生成 ────────────────────────────────────────────────────────────
    # Images API 返回的是普通 JSON（base64 / url），不是 SSE。复用文本管道会
    # 被 prepare_request 强制改成 stream=True 并按事件流解析，所以这里单开一条
    # 透传路径：本机鉴权、模型解析、端点候选、原样回传，其余一概不碰。
    def _image_profile(self, requested: str) -> dict:
        """解析图像目标：精确匹配 → 任意 images 配置 → 当前选中模型 → 404。

        协议为 ``images`` 的配置是权威目标：调用方常带着自己的模型名
        （gpt-image-1 / gpt-image-2.5 …），而真正可用的出图模型由配置决定，
        所以只要存在 images 配置就优先用它，不被请求里的名字带偏。
        没有 images 配置时才复用文本配置的主机——聚合站常在同一主机上同时
        提供两类端点，这样用户不必为出图再建一份配置。
        """
        settings = self.server.gateway.settings
        profile = None
        if requested:
            try:
                profile = self._profile_for(requested)
            except ProtocolFailure:
                profile = None
        explicit = None
        try:
            for item in settings.profiles():
                if item.get("protocol") == "images":
                    explicit = settings.profile(item["id"], include_key=True)
                    break
        except ValueError:
            explicit = None
        # 请求命中的不是图像配置时，显式图像配置优先；否则才复用文本主机。
        if explicit is not None and (profile is None or profile.get("protocol") != "images"):
            return explicit
        if profile is not None:
            return profile
        try:
            return settings.selected(include_key=True)
        except ValueError:
            raise ProtocolFailure(
                "尚未配置可用的图像模型。请在 Relay 中添加一个图像供应商。",
                404, "image_model_not_configured") from None

    @staticmethod
    def _image_candidates(profile: dict, path: str) -> list[str]:
        """该配置下可尝试的图像端点，按优先级排列（404 才换下一个）。"""
        action = "edits" if path.endswith("/edits") else "generations"
        base = str(profile.get("base_url") or "").rstrip("/")
        candidates: list[str] = []

        def add(url: str) -> None:
            if url and url not in candidates:
                candidates.append(url)

        if profile.get("protocol") == "images":
            if base.endswith("/generations") and action == "edits":
                add(base[: -len("/generations")] + "/edits")
                add(base)
            elif base.endswith("/edits") and action == "generations":
                add(base[: -len("/edits")] + "/generations")
                add(base)
            else:
                add(base)
            return candidates
        root = base
        for suffix in ("/chat/completions", "/responses", "/messages", "/models"):
            if root.endswith(suffix):
                root = root[: -len(suffix)]
                break
        if root.endswith("/v1"):
            add(f"{root}/images/{action}")
            # 有些聚合站把 images 挂在站根而不是 /v1 下；404 时再试一次。
            add(f"{root[: -len('/v1')]}/images/{action}")
        else:
            add(f"{root}/v1/images/{action}")
            add(f"{root}/images/{action}")
        return candidates

    def _handle_images(self, path: str, chunked: bool, length):
        if not self._authorized():
            self._discard_request_body(length)
            return
        raw = self._read_bounded_body(chunked, length)
        if raw is None:
            return  # 具体错误已由 _read_bounded_body 回过
        began = time.monotonic()
        status = 500
        profile = None
        body = None
        failure_message = ""
        try:
            try:
                body = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ProtocolFailure("请求体不是有效 JSON。") from error
            if not isinstance(body, dict):
                raise ProtocolFailure("请求体必须是 JSON 对象。")
            requested = body.get("model") if isinstance(body.get("model"), str) else ""
            profile = self._image_profile(requested)
            payload_body = dict(body)
            # 显式图像配置以配置里的出口名为准；复用文本主机时保留调用方
            # 指定的图像模型名（聚合站靠它区分能力）。
            payload_body["model"] = (profile["model"] if profile.get("protocol") == "images"
                                     else requested or profile["model"])
            payload = compact_json(payload_body).encode("utf-8")
            headers = upstream_headers(profile)
            headers["Accept"] = "application/json"
            response = None
            content_type = "application/json"
            with self.server.gateway.http_client() as client:
                for url in self._image_candidates(profile, path):
                    response = client.post(
                        url, headers=headers, content=payload,
                        timeout=IMAGE_UPSTREAM_TIMEOUT_SECONDS,
                    )
                    # 404/405 只说明这个候选路径不存在；换下一个。其余状态都是
                    # 上游真实回应，立即停下（不对 401/429/5xx 重复计费）。
                    if response.status_code in (404, 405):
                        continue
                    break
                if response is None:
                    raise ProtocolFailure("没有可用的图像端点。", 404, "image_endpoint_missing")
                status = int(response.status_code)
                if status >= 400:
                    raise upstream_error(response, profile)
                data = response.read()
                content_type = response.headers.get("Content-Type", "application/json")
            self._write_raw(status, data, content_type)
        except ProtocolFailure as error:
            status = error.status
            failure_message = str(error)
            try:
                self._deliver_failure(error)
            except OSError:
                pass
        except httpx.TimeoutException:
            status = 504
            failure_message = ERROR_HINTS[504]
            try:
                self._deliver_failure(ProtocolFailure(failure_message, 504, "upstream_timeout"))
            except OSError:
                pass
        except httpx.TransportError as error:
            status = 503
            failure_message = "无法连接供应商：" + redact(
                str(error), (profile or {}).get("api_key", ""))
            try:
                self._deliver_failure(ProtocolFailure(failure_message, 503, "upstream_unavailable"))
            except OSError:
                pass
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            status = 499
            failure_message = LOCAL_RESTART_MESSAGE
        except Exception as error:  # noqa: BLE001 - 图像路径不能把请求线程打挂
            status = 500
            failure_message = "图像路由内部错误：" + redact(
                str(error), (profile or {}).get("api_key", ""))
            try:
                self._deliver_failure(ProtocolFailure(failure_message, 500, "router_internal_error"))
            except OSError:
                pass
        finally:
            try:
                requested_model = body.get("model") if isinstance(body, dict) else None
                record = profile or _unresolved_profile(str(requested_model or ""))
                self.server.gateway.activity.add(
                    profile=record,
                    elapsed=time.monotonic() - began,
                    status=status,
                    message="" if 200 <= status < 300 else failure_message,
                    request_model=requested_model,
                    client="images",
                )
            except Exception:  # noqa: BLE001 - 统计失败不影响已完成的响应
                pass
            self.server.gateway.log_request_result(
                status, time.monotonic() - began, {},
                (profile or {}).get("model"))

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            self._write_json(200, {"app": APP_NAME, "version": VERSION, "status": "running"})
            return
        if not self._authorized():
            return
        if path in {"/models", "/v1/models"}:
            models = [{"id": ROUTER_MODEL, "object": "model", "owned_by": "microglow-relay"}]
            models.extend({"id": item["id"], "object": "model", "owned_by": "microglow-relay"} for item in self.server.gateway.settings.profiles())
            self._write_json(200, {"object": "list", "data": models})
            return
        self._error(ProtocolFailure("接口不存在。", 404, "not_found"))

    def _start_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        self.streaming_started = True

    def _emit(self, event: dict):
        raw = f"event: {event['type']}\ndata: {compact_json(event)}\n\n".encode("utf-8")
        with self.server.gateway.lock:
            self.server.gateway.output_bytes += len(raw)
        self.wfile.write(raw)
        self.wfile.flush()

    def _deliver_failure(self, failure: ProtocolFailure):
        if self.streaming_started:
            if self.client_protocol == "anthropic":
                self._emit(anthropic_error_body(failure))
                return
            self._emit({
                "type": "response.failed",
                "response": {
                    "id": "resp_failed",
                    "object": "response",
                    "status": "failed",
                    "output": [],
                    "error": {"code": failure.code, "message": str(failure)},
                },
            })
        else:
            self._error(failure)

    def _profile_for(self, model: str):
        if is_retired_router_model(model):
            raise ProtocolFailure("旧路由模型已停用，请在 Relay 中重新接入。", 404, "model_retired")
        if model == ROUTER_MODEL:
            override = self.server.gateway.selected_override
            if override is not None:
                return dict(override)
            try:
                selected = self.server.gateway.settings.selected(include_key=True)
                peers = [p for p in self.server.gateway.settings.profiles()
                         if p["model"] == selected["model"] and p["id"] != selected["id"]]
                if peers:
                    selected["_group_members"] = [dict(selected)] + [
                        self.server.gateway.settings.profile(p["id"], include_key=True) for p in peers]
                return selected
            except ValueError:
                # 「还没选模型」是配置状态，不是本程序故障：不能冒充 500。
                raise ProtocolFailure("尚未选择模型，请在 Relay 中选择一个模型。",
                                      404, "model_not_selected") from None
        try:
            return self.server.gateway.settings.profile(model, include_key=True)
        except ValueError:
            pass
        # 友好名别名：Codex 目录与 Claude /model 共用（model_names.py）。
        # id 永远优先，友好名只在 id 不命中时接管。
        friendly = resolve_friendly(self.server.gateway.settings.profiles(), model)
        if friendly is not None:
            try:
                return self.server.gateway.settings.profile(
                    str(friendly["id"]), include_key=True)
            except ValueError:
                pass      # 刚解析到就被删了，按未配置继续往下走
        # 宽松 B′：原生 slug 透传。顺序是「profile ID → 原生 slug → 404」——
        # 同名配置永远优先，原生 slug 只在没有同名配置时才接管。
        if is_native_slug(model):
            profile = None
            target = resolve_native_target(self.server.gateway.settings.profiles(), model)
            if target is not None:
                try:
                    profile = self.server.gateway.settings.profile(
                        str(target["id"]), include_key=True)
                except ValueError:
                    profile = None      # 刚查到就被删了，按未配置处理
            if profile is not None:
                # 出口模型名按请求覆盖：三路协议都从 profile["model"] 取名
                # （adapters.py:238 / 295 / 665），所以不用改 adapters。
                profile["model"] = model
                return profile
            # 没有同名配置时走官方直通：认证用本机 Codex 登录态，
            # 请求头跟着客户端走（会话/线程/功能开关都在里面）。
            direct = native_profile(model)
            if direct is not None:
                incoming = getattr(self, "headers", None)
                if incoming is not None:
                    direct["_client_headers"] = {
                        name: incoming.get(name)
                        for name in NATIVE_PASSTHROUGH_HEADERS
                        if incoming.get(name)
                    }
                return direct
            raise ProtocolFailure(
                "Codex 原生模型 %s 不可用：本机没有 ChatGPT 登录态，也没有同名 Relay 配置。"
                "请先在 Codex 登录，或在 Relay 中添加一条模型名为 %s 的配置。"
                % (str(model)[:120], str(model)[:120]),
                404, "native_model_unconfigured") from None
        # 已删除/未知的模型 id 同样属于请求侧错误，按 404 归类，
        # 否则会落进「服务内部错误」并污染日志页的错误分类。
        raise ProtocolFailure(
            "模型不存在：%s。请在 Relay 中重新选择模型。" % str(model)[:120],
            404, "model_not_found") from None

    def _consume_upstream(self, body: dict, names, protocol: str,
                          primed: list, upstream_lines) -> dict:
        """消费上游流直到终态，返回 final response（供主路径与渠道重试共用）。"""
        client_streaming = bool(body.get("stream"))
        # responses 分支把「提交客户端响应头」推迟到第一个可识别的事件：
        # 上游用保活块或错误块开场时，客户端应该拿到一个可重试的干净错误，
        # 而不是一个已经写了一半的 200 流。
        if client_streaming and protocol != "responses":
            self._start_sse()
        if self.client_protocol == "anthropic":
            emit = AnthropicClientWriter(body["model"], self._emit).feed
        else:
            emit = self._emit
        final = None
        if protocol == "responses":
            terminal = False
            unrecognized = 0
            for event in read_sse(_replay(primed, upstream_lines)):
                if event == "[DONE]":
                    continue
                if not isinstance(event, dict) or not event.get("type"):
                    detail = _block_error_text(event)
                    if detail:
                        # 上游把真实原因藏在这个没有事件类型的块里，
                        # 必须原样带出来，否则用户无从定位。
                        raise ProtocolFailure(
                            redact(detail, self._current_key()),
                            502, "upstream_stream_error")
                    # 空保活块或未知写法不构成失败：跳过继续读，
                    # 不能因为它把一条本来健康的流整条判死。
                    unrecognized += 1
                    if unrecognized == 1:
                        self.server.gateway.log("warning", "上游流出现无法识别的事件，已跳过。")
                    continue
                if event["type"] == "error":
                    # 判定必须在转发之前：上游用错误事件开场时，
                    # 客户端应该拿到干净的 502，而不是一个转发过去的
                    # error 事件再加一条 response.failed。
                    raise ProtocolFailure(
                        redact(_event_error_text(event) or "上游返回错误事件。",
                               self._current_key()),
                        502, "upstream_stream_error")
                if client_streaming:
                    if not self.streaming_started:
                        self._start_sse()
                    emit(event)
                if event["type"] in {"response.completed", "response.incomplete", "response.failed"}:
                    final = event.get("response")
                    if isinstance(final, dict):
                        self._log_usage.update(final.get("usage") or {})
                    terminal = True
                    break
            if not terminal or not isinstance(final, dict):
                if unrecognized:
                    raise ProtocolFailure(
                        "上游流没有返回可识别的 Responses 事件（已跳过 %d 个）。"
                        % unrecognized, 502, "bad_upstream_stream")
                raise ProtocolFailure("上游流提前结束。", 502, "truncated_stream")
        else:
            builder = ResponseBuilder(body["model"], names, emit if client_streaming else lambda event: None, self.server.gateway.reasoning)
            builder.start()
            ended = False
            for event in read_sse(_replay(primed, upstream_lines)):
                if protocol == "chat":
                    if event == "[DONE]":
                        ended = True
                        break
                    if isinstance(event, dict):
                        reported = event.get("usage")
                        if isinstance(reported, dict):
                            for target, source in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens")):
                                if source in reported or target in reported:
                                    self._log_usage[target] = reported.get(source, reported.get(target))
                            # 缓存/推理明细随 usage 一起带出来，否则统计口径会永远缺这一块。
                            for block in ("prompt_tokens_details", "completion_tokens_details"):
                                if isinstance(reported.get(block), dict):
                                    self._log_usage[block] = reported[block]
                            if reported.get("prompt_cache_hit_tokens") is not None:
                                self._log_usage["prompt_cache_hit_tokens"] = reported["prompt_cache_hit_tokens"]
                        builder.feed_chat(event)
                else:
                    if event == "[DONE]":
                        continue
                    if isinstance(event, dict):
                        reported = ((event.get("message") or {}).get("usage")
                                    if event.get("type") == "message_start" else event.get("usage"))
                        if isinstance(reported, dict):
                            for name in ("input_tokens", "output_tokens"):
                                if name in reported:
                                    self._log_usage[name] = reported[name]
                            if reported.get("cache_read_input_tokens") is not None:
                                self._log_usage["cache_read_input_tokens"] = reported["cache_read_input_tokens"]
                        builder.feed_anthropic(event)
                        if anthropic_terminal(event):
                            ended = True
                            break
            if not ended:
                raise ProtocolFailure("上游流提前结束。", 502, "truncated_stream")
            final = builder.finish()
        return final

    def _current_key(self) -> str:
        return (getattr(self, "_channel_profile", None) or {}).get("api_key", "")

    def do_POST(self):
        path = urlsplit(self.path).path
        self.client_protocol = "anthropic" if path in {"/messages", "/v1/messages"} else "responses"
        chunked = self._is_chunked()
        length = None if chunked else self._declared_length()
        # 图像生成：与文本协议共用本机鉴权与配置，但不走 SSE 管道。
        if path in IMAGES_PATHS:
            self._handle_images(path, chunked, length)
            return
        if path in {"/messages/count_tokens", "/v1/messages/count_tokens"}:
            # Claude Code 的本地 token 估算：不进上游、不记日志，给个量级读数即可。
            self.client_protocol = "anthropic"
            if not self._authorized():
                self._discard_request_body(length)
                return
            raw = self._read_bounded_body(chunked, length)
            if raw is None:
                return  # 读取失败的具体错误已在 _read_bounded_body 里回了
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                self._error(ProtocolFailure("请求体不是有效 JSON。"))
                return
            self._write_json(200, {"input_tokens": estimate_tokens_for_messages(
                body if isinstance(body, dict) else {})})
            return
        if path not in {"/responses", "/v1/responses", "/messages", "/v1/messages"}:
            self._discard_request_body(length)
            self._error(ProtocolFailure("仅支持 /v1/responses 与 /v1/messages。", 404, "not_found"))
            return
        if not self._authorized():
            self._discard_request_body(length)
            return
        if not chunked:
            if length is None:
                self._error(ProtocolFailure("Content-Length 无效。"))
                return
            if length <= 0:
                self._discard_request_body(length)
                self._error(ProtocolFailure("请求体为空。", 400, "empty_body"))
                return
            if length > MAX_REQUEST_BYTES:
                self._discard_request_body(length)
                self._error(ProtocolFailure("请求体超过 32 MB 上限。", 413, "body_too_large"))
                return
        profile = None
        body = None
        local_interrupted = False
        channel_index = -1
        self._channel_profile = None
        # 化解波动：首次失败原因（口径 2026-11-10）。成功且非空 = 被救活。
        first_failure_reason = ""
        first_failure_box = [first_failure_reason]
        with self.server.gateway.lock:
            self.server.gateway._inflight += 1
        began = time.monotonic()
        status = 500
        usage = {}
        log_usage = {}
        failure_message = ""
        acquired = False
        try:
            if chunked:
                raw = self._read_chunked_body(MAX_REQUEST_BYTES)
                if raw is None:
                    # 超限后再排空一次，客户端才拿得到 413 而不是连接重置。
                    self._discard_request_body(None)
                    raise ProtocolFailure("请求体超过 32 MB 上限。", 413, "body_too_large")
            else:
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ProtocolFailure("请求体读取不完整。")
            # 请求体已经读完，接下来只写响应流；放宽写超时以免长流被 30 秒掐断。
            self.connection.settimeout(RESPONSE_SOCKET_TIMEOUT_SECONDS)
            with self.server.gateway.lock:
                self.server.gateway.input_bytes += len(raw)
            if not raw:
                raise ProtocolFailure("请求体为空。", 400, "empty_body")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ProtocolFailure("请求体不是有效 JSON。") from error
            if not isinstance(body, dict) or not isinstance(body.get("model"), str):
                raise ProtocolFailure("请求必须包含 model 字符串。")
            if self.client_protocol == "anthropic":
                # Claude 客户端讲 Messages：折成内部统一的 Responses 形状，
                # 之后的解析、路由、上游适配与 Codex 走同一套管道。
                body = anthropic_request_to_responses(body)
            profile = self._profile_for(body["model"])
            route_profile = profile
            # 多渠道：解析出的 profile 挂了渠道组时，先选一家健康渠道；
            # 选出来的副本替换 profile 参与后续所有上游交互（含日志脱敏）。
            router = self.server.gateway.channel_router
            channel_count = sum(c.get("enabled", True) for c in router.channels_of(profile))
            if profile.get("channels") or profile.get("_group_members"):
                try:
                    profile, channel_index = router.select(profile)
                except ValueError as error:
                    raise ProtocolFailure(str(error), 503, "no_enabled_channel") from error
            else:
                channel_index = -1
            self._channel_profile = profile
            self._log_usage = log_usage
            suffix, payload, names, protocol = prepare_request(body, profile, self.server.gateway.reasoning)
            # 形状教训预洗：同供应商×模型 已验证有效的降级动作，直接套用，避免白打 400。
            _lesson_key = f"{profile.get('provider_name') or profile.get('provider') or ''}|{profile.get('model') or ''}"
            _lessons = self.server.gateway.settings.shape_lessons().get(_lesson_key, {}).get("actions", [])
            if _lessons:
                payload, _lc = apply_lessons(payload, _lessons)
            # 并发上限见 MAX_UPSTREAM_CONCURRENCY；满了先排队，只有排到超时才回 429。
            wait = min(
                SLOT_WAIT_SECONDS,
                max(0.0, began + UPSTREAM_TOTAL_BUDGET_SECONDS
                    - time.monotonic() - MIN_NEXT_ATTEMPT_SECONDS),
            )
            acquired = (self.server.gateway.slots.acquire(timeout=wait) if wait > 0
                        else self.server.gateway.slots.acquire(blocking=False))
            if not acquired:
                raise ProtocolFailure("本地并发已满，请稍后重试。", 429, "local_busy")
            with self.server.gateway.lock:
                self.server.gateway.active_requests += 1
            def _on_upstream_retry(code, attempt, delay, error, note=""):
                if not first_failure_box[0]:
                    if code is None:
                        first_failure_box[0] = "timeout" if isinstance(error, httpx.TimeoutException) else "unavailable"
                    elif code == 429:
                        first_failure_box[0] = "rate_limit"
                    elif code == 400:
                        first_failure_box[0] = "transient_400"
                    else:
                        first_failure_box[0] = "unavailable"
                self.server.gateway.log(
                    "warning", note or (
                        ("上游状态 {0}".format(code) if code is not None else "上游连接失败")
                        + f" · 发送客户端响应前重试 {attempt} 次 · 等待 {delay:g}s"))

            attempted_channels = set()
            request_deadline = began + UPSTREAM_TOTAL_BUDGET_SECONDS
            while True:
                if channel_index >= 0:
                    attempted_channels.add((profile.get("id", ""), channel_index))
                remaining_channels = max(0, channel_count - len(attempted_channels)) if channel_index >= 0 else 0
                # 多渠道平分剩余预响应等待预算，避免首家慢超时吃掉备用的机会。
                # 单渠道仍沿用原有完整预算和渠道内重试。
                now = time.monotonic()
                channel_deadline = now + max(0.0, request_deadline - now) / (remaining_channels + 1)
                try:
                    with self.server.gateway.http_client() as client:
                        with _upstream_stream(
                            client, profile, payload, channel_deadline, _on_upstream_retry,
                            lambda message: self.server.gateway.log("warning", message),
                        ) as (upstream, attempt, primed, upstream_lines):
                            final = self._consume_upstream(body, names, protocol, primed, upstream_lines)
                            usage = final.get("usage") if isinstance(final, dict) else {}
                            if not bool(body.get("stream")):
                                if self.client_protocol == "anthropic":
                                    self._write_json(200, anthropic_message_from_response(final, body["model"]))
                                else:
                                    self._write_json(200, final)
                    status = 200
                    if channel_index >= 0:
                        router.mark_success(channel_index, profile.get("id", ""))
                    break
                except (ProtocolFailure, httpx.TransportError) as error:
                    upstream_status = error.status if isinstance(error, ProtocolFailure) else None
                    recoverable = (
                        upstream_status == 429
                        or (upstream_status is not None and upstream_status >= 500)
                        or isinstance(error, httpx.TransportError))
                    if not recoverable or self.server.gateway._stopping:
                        raise
                    if channel_index >= 0:
                        cooldown = router.mark_failure(channel_index, profile.get("id", ""))
                    if (self.streaming_started or not remaining_channels
                            or time.monotonic() >= request_deadline):
                        raise
                    try:
                        next_profile, next_index = router.select(route_profile, exclude=attempted_channels)
                    except ValueError:
                        raise error
                    if not first_failure_box[0]:
                        first_failure_box[0] = ("rate_limit" if upstream_status == 429 else
                            "timeout" if isinstance(error, httpx.TimeoutException) or upstream_status == 504 else "unavailable")
                    self.server.gateway.log("warning", f"渠道故障已冷却 {cooldown:g}s · 自动切换备用渠道重试")
                    profile, channel_index = next_profile, next_index
                    self._channel_profile = profile
                    log_usage.clear()
                    # 固定本轮最初解析的同模型渠道组，不随默认模型切换而改投其他模型。
                    suffix, payload, names, protocol = prepare_request(body, profile, self.server.gateway.reasoning)
        except ProtocolFailure as error:
            status = error.status
            failure_message = str(error)
            try:
                self._deliver_failure(error)
            except OSError:
                pass
        except httpx.ConnectTimeout as error:
            # 连接从未建立：按“供应商不可达”处理，而不是网关超时。
            status = 503
            failure_message = "无法连接供应商：" + redact(error, profile.get("api_key", "") if profile else "")
            try:
                self._deliver_failure(ProtocolFailure(failure_message, 503, "upstream_unavailable"))
            except OSError:
                pass
        except httpx.TimeoutException:
            status = 504
            failure_message = ERROR_HINTS[504]
            try:
                self._deliver_failure(ProtocolFailure(failure_message, 504, "upstream_timeout"))
            except OSError:
                pass
        except httpx.TransportError as error:
            status = 503
            if self.server.gateway._stopping:
                # 本地停机把在途的上游连接掐断了；这不是供应商的故障。
                local_interrupted = True
                failure_message = LOCAL_RESTART_MESSAGE
                code = "local_restart"
            else:
                failure_message = "无法连接供应商：" + redact(error, profile.get("api_key", "") if profile else "")
                code = "upstream_unavailable"
            try:
                self._deliver_failure(ProtocolFailure(failure_message, 503, code))
            except OSError:
                pass
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            status = 499
            failure_message = "客户端已取消请求"
        except Exception as error:
            status = 500
            failure_message = "路由器内部错误：" + redact(error, profile.get("api_key", "") if profile else "")
            try:
                self._deliver_failure(ProtocolFailure(failure_message, 500, "router_internal_error"))
            except OSError:
                pass
        finally:
            if acquired:
                with self.server.gateway.lock:
                    self.server.gateway.active_requests -= 1
                self.server.gateway.slots.release()
            resolved = profile is not None
            if (not resolved and status != 499 and isinstance(body, dict)
                    and isinstance(body.get("model"), str)):
                # 供应商还没解析出来就失败了（例如模型已被删除）：本地统计仍要记
                # 这一笔，否则成功率的分母会漏掉一次真实尝试。
                # 占位 profile 不带供应商与模型，因此不进模型占比、也不上遥测。
                profile = _unresolved_profile(body["model"])
            if profile:
                usage = usage if isinstance(usage, dict) else {}
                # 只保留分类 + 脱敏后的上游正文：分类字段口径不变，正文用于复盘。
                category = error_category_for_status(status)
                detail = redact(failure_message, profile.get("api_key", "")).strip()
                # 本地停机掐断的请求不是上游故障，不能记进上游错误口径。
                if local_interrupted:
                    summary = LOCAL_RESTART_MESSAGE
                elif 200 <= status < 300:
                    summary = ""
                else:
                    summary = f"{category}：{detail}" if detail else category
                # 缓存/推理明细优先取 log_usage（三条协议通道都会把上游 usage 汇进去），
                # 取不到再看构造出来的 usage，仍然没有就按「未上报」处理。
                cached_tokens, reasoning_tokens = usage_detail_counts(log_usage)
                if cached_tokens is None and reasoning_tokens is None:
                    cached_tokens, reasoning_tokens = usage_detail_counts(usage)
                self.server.gateway.activity.add(
                    profile=profile,
                    elapsed=time.monotonic() - began,
                    status=status,
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    cached_tokens=cached_tokens,
                    cache_creation_input_tokens=(log_usage or usage or {}).get("cache_creation_input_tokens"),
                    channel_index=channel_index,
                    reasoning_tokens=reasoning_tokens,
                    message=summary,
                    # 记下请求侧 model：profile 的 model 是出口名，两者不是一回事。
                    request_model=body.get("model"),
                    client=self.client_protocol,
                    # 化解波动：成功且非空 = 这次请求被重试/换渠道救活了。
                    mitigated=first_failure_box[0] if 200 <= status < 300 else "",
                )
                if resolved:
                    self.server.gateway.record_telemetry(
                        profile,
                        status=status,
                        elapsed_seconds=time.monotonic() - began,
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                    )
            self.server.gateway.log_request_result(
                status, time.monotonic() - began, log_usage,
                (profile or {}).get("model") or (
                    body.get("model") if isinstance(body, dict)
                    and isinstance(body.get("model"), str) else None),
                mitigated=first_failure_box[0] if 200 <= status < 300 else "")
            with self.server.gateway.lock:
                self.server.gateway._inflight -= 1


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def handle_error(self, request, client_address):
        self.server.gateway.log("warning", "本地客户端连接已关闭。")


class Gateway:
    def __init__(self, settings, *, with_telemetry: bool = True, load_activity: bool = True):
        self.settings = settings
        # 连接测试只需要往 usage 追加一行，不需要把整份历史读进内存。
        self.activity = ActivityLog(settings.directory, load=load_activity)
        # Trip 清零快照账本（任务书第 5 节）：仅存本机数据目录。
        self.trip_ledger = TripLedger(settings.directory)
        self.reasoning = ReasoningCache(settings.directory)
        # 连接测试等短命网关不需要遥测运行时，避免每次探活泄漏线程与 SQLite 句柄。
        self.telemetry = self._create_telemetry(settings) if with_telemetry else None
        self.selected_override = None
        self.httpd = None
        self.thread = None
        self.lock = threading.RLock()
        self._http = None
        self._shutdown_started = False
        self._stopping = False
        self._inflight = 0
        self.slots = threading.BoundedSemaphore(MAX_UPSTREAM_CONCURRENCY)
        # 多渠道路由：冷却状态随网关同生命周期（重启即视为全部健康）。
        self.channel_router = ChannelRouter()
        self.events = deque(maxlen=300)
        self.active_requests = 0
        self.input_bytes = 0
        self.output_bytes = 0
        self._subscribers = []

    def _client(self) -> httpx.Client:
        """One keep-alive pool per process; avoids a fresh TLS handshake per request."""
        client = self._http
        if client is not None:
            return client
        with self.lock:
            if self._http is None:
                self._http = httpx.Client(
                    timeout=httpx.Timeout(300, connect=20),
                    follow_redirects=False,
                    trust_env=False,
                    limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
                )
            return self._http

    @contextmanager
    def http_client(self):
        """Borrow the shared upstream client for one request."""
        yield self._client()

    def _close_client(self):
        with self.lock:
            client, self._http = self._http, None
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

    # 匿名遥测：生产入口硬编码在 src/telemetry/endpoint.py；这里只做接线。

    @staticmethod
    def _create_telemetry(settings):
        """Build the isolated telemetry runtime; never block or break startup."""
        try:
            version = telemetry_client_version(VERSION)
            uploader = HttpTelemetryUploadClient(version)
            return TelemetryRuntime.create_isolated(
                settings.directory,
                version,
                uploader=uploader,
            )
        except Exception:
            try:
                return TelemetryRuntime.create_isolated(settings.directory, telemetry_client_version(VERSION))
            except Exception:
                return None

    def record_telemetry(self, profile, *, status, elapsed_seconds, input_tokens=0, output_tokens=0):
        """Queue allow-listed counters only: no request/response text, never raises."""
        runtime = getattr(self, "telemetry", None)
        if runtime is None:
            return
        try:
            if not runtime.enabled():
                return
            name = profile.get("provider_name") or profile.get("provider")
            model, family = model_dimension(profile.get("model"), name)
            runtime.record_request(
                provider=provider_key(name),
                model=model,
                model_family=family,
                status=int(status),
                elapsed_seconds=float(elapsed_seconds),
                input_tokens=int(input_tokens or 0),
                output_tokens=int(output_tokens or 0),
                call_channel=classify_call_channel(profile.get("base_url")),
            )
        except Exception:
            pass

    @property
    def running(self):
        return self.httpd is not None

    @property
    def port(self):
        return self.httpd.server_port if self.httpd else int(self.settings.snapshot()["port"])

    def subscribe(self, callback):
        self._subscribers.append(callback)

    def log(self, level: str, message: str, *, request_result: dict | None = None):
        event = {"time": time.strftime("%H:%M:%S"), "level": level, "message": redact(message)}
        if request_result is not None:
            event["request_result"] = request_result
        with self.lock:
            self.events.append(event)
        for callback in list(self._subscribers):
            try:
                callback(event)
            except Exception:
                pass

    def log_request_result(self, status: int, elapsed: float, usage: dict | None,
                           model: str | None = None, *, mitigated: str = ""):
        """Only outcome, duration, known token totals and the routed model name.

        0.6 的核心价值就是「一条会话内按 /model 切模型」，因此实时日志必须能看出
        这一笔走了哪条配置；模型名是本地已存配置的标识，不是请求正文，仍然不落盘
        任何请求／响应内容。
        """
        usage = usage if isinstance(usage, dict) else {}
        counts = [usage.get("input_tokens"), usage.get("output_tokens")]
        tokens = sum(counts) if all(type(n) is int and n >= 0 for n in counts) else None
        cached, reasoning = usage_detail_counts(usage)
        ok = 200 <= status < 300
        result = {"ok": ok, "elapsed": elapsed, "tokens": tokens,
                  "cached": cached, "reasoning": reasoning, "model": model or "",
                  "status": int(status), "mitigated": mitigated if ok else ""}
        token_text = f"{tokens:,}" if tokens is not None else "未知"
        self.log("success" if ok else "error",
                 f'{"成功" if ok else "失败"} · {elapsed:.1f} 秒 · Token {token_text}',
                 request_result=result)

    def recent_events(self):
        with self.lock:
            return list(self.events)

    def start(self, port=None):
        if self.httpd:
            return
        token = self.settings.local_token()

        configured_port = int(self.settings.snapshot()["port"] if port is None else port)
        self._stopping = False
        httpd = LocalServer(("127.0.0.1", configured_port), Handler)
        httpd.gateway = self
        httpd.token = token
        self.httpd = httpd
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True, name="microglow-relay-gateway")
        self.thread.start()
        self.log("success", f"服务已启动 · 127.0.0.1:{self.port}")

    def stop(self, drain=None):
        """Stop the local service without uploading telemetry.

        先停止接收新连接，再给在途请求一个 drain 上限，超时才强断。否则
        用户在流式会话进行中点「停止服务」，会把已经吐了一半的流拦腰砍断，
        客户端只看到一个 response.failed。
        """
        if not self.httpd:
            return
        server = self.httpd
        self.httpd = None
        self._stopping = True
        server.shutdown()
        limit = STOP_DRAIN_SECONDS if drain is None else max(0.0, float(drain))
        deadline = time.monotonic() + limit
        pending = 0
        while True:
            with self.lock:
                pending = self._inflight
            if pending <= 0 or time.monotonic() >= deadline:
                break
            time.sleep(0.02)
        if pending > 0:
            self.log("warning", f"停机等待 {limit:g}s 后仍有 {pending} 个请求未结束，已强制中断。")
        server.server_close()
        self._close_client()
        self.log("warning", "服务已停止")

    def close(self):
        """彻底释放：停服务 + 停本地聚合线程（不做上传）。

        与 ``shutdown()`` 的分工：shutdown 是"正常退出"，会尝试一次有预算的
        遥测上传；close 是"对象即将被丢弃"，只要把线程和文件句柄还回去。
        """
        try:
            self.stop()
        except Exception:  # noqa: BLE001 - 释放路径不能被单个步骤拖住
            pass
        runtime = getattr(self, "telemetry", None)
        if runtime is not None:
            try:
                runtime.stop()
            except Exception:  # noqa: BLE001
                pass

    def shutdown(self):
        """One telemetry upload pass per normal application exit."""
        with self.lock:
            if self._shutdown_started:
                return
            self._shutdown_started = True
        self.stop()
        # 小计的落盘有节流，退出时补最后一次；不补也不丢数据（下次启动会从
        # 日志重扫补回），但会让用户下次打开时看到落后几秒的读数。
        try:
            self.activity.trips.flush()
        except Exception:  # noqa: BLE001 - 退出路径不能被统计模块拖住
            pass
        runtime = getattr(self, "telemetry", None)
        if runtime is not None:
            # 退出时做一次有上限的上传尝试；失败静默，批次保留待下次重试。
            try:
                def flush_exit():
                    try:
                        runtime.flush()
                    except Exception:
                        pass
                # 线程必须是非守护的：守护线程会被解释器退出直接掐断，
                # 批次只传到一半就没了，后面的积压批次永远轮不到。
                worker = threading.Thread(
                    target=flush_exit,
                    daemon=False,
                    name="microglow-telemetry-exit-upload",
                )
                worker.start()
                # 只同步等一小段，界面不会卡住；剩下的预算留给退出阶段跑完。
                worker.join(timeout=TELEMETRY_EXIT_JOIN_SECONDS)
            except Exception:
                pass
            # 上传线程跑完后回收本地聚合线程：退出路径上一条都不该留。
            try:
                runtime.stop()
            except Exception:  # noqa: BLE001
                pass

def models_url(profile: dict) -> str:
    """Derive the standard discovery endpoint without changing the stored generation URL."""
    endpoint = profile["base_url"].rstrip("/")
    for suffix in TEXT_AND_IMAGE_SUFFIXES:
        if endpoint.endswith(suffix):
            return endpoint[:-len(suffix)] + "/models"
    return endpoint + "/models"


def fetch_models(profile: dict) -> list[str]:
    profile = dict(profile)
    # 裸地址（站根或带 /v1 的基地址）按协议试候选：/v1/models 优先，
    # 不行再退 /models。完整端点只有一个候选，行为与旧版一致。
    base = profile["base_url"].rstrip("/")
    if any(base.endswith(suffix) for suffix in TEXT_AND_IMAGE_SUFFIXES):
        candidates = [models_url(profile)]
    elif base.endswith("/models"):
        candidates = [base]
    elif base.endswith("/v1"):
        candidates = [base + "/models"]
    else:
        candidates = [base + "/v1/models", base + "/models"]
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
        response = None
        for index, url in enumerate(candidates):
            response = client.get(url, headers=upstream_headers(profile))
            if response.is_success:
                break
            # 404/405 只说明「这个路径没有 /models」，换下一个候选；
            # 其它状态码（401/403/429/5xx…）是服务端真实回应，直接报。
            if response.status_code not in (404, 405):
                break
        if response is None or not response.is_success:
            if response is not None and response.status_code not in (404, 405):
                raise upstream_error(response, profile)
            raise ProtocolFailure("供应商未返回模型列表，请手动填写模型名称。", 404, "models_unavailable")
        try:
            body = response.json()
        except json.JSONDecodeError as error:
            raise ProtocolFailure("模型列表不是有效 JSON。", 502, "bad_models_response") from error
        values = sorted({
            str(item.get("id"))
            for item in body.get("data", [])
            if isinstance(item, dict) and item.get("id")
        })
        if not values:
            raise ProtocolFailure("供应商未返回模型列表，请手动填写模型名称。", 404, "models_unavailable")
        return values


def probe_profile(settings, profile: dict, api_key: str = "") -> str:
    """Test an unsaved form draft without creating or changing a stored profile."""
    test_profile = dict(profile)
    test_profile["id"] = str(test_profile.get("id") or "")
    test_profile["api_key"] = api_key or test_profile.get("api_key", "")
    # 只借本机回环网关跑一次探活：不启动遥测运行时，也不改共享的 settings 对象。
    # load_activity=False：探活的开销与 usage 日志体量彻底解耦。
    gateway = Gateway(settings, with_telemetry=False, load_activity=False)
    gateway.start(0)
    gateway.selected_override = test_profile
    try:
        url = f"http://127.0.0.1:{gateway.port}/v1/responses"
        headers = {"Authorization": "Bearer " + settings.local_token()}
        body = {
            "model": ROUTER_MODEL,
            "input": "Reply with only OK.",
            "stream": False,
            "max_output_tokens": 128,
        }
        with httpx.Client(timeout=120, trust_env=False) as client:
            response = client.post(url, headers=headers, json=body)
            data = response.json()
        if not response.is_success:
            raise ProtocolFailure(data.get("error", {}).get("message", "连接测试失败。"), response.status_code, "probe_failed")
        texts = [
            part.get("text", "")
            for item in data.get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
        ]
        if not any(texts):
            raise ProtocolFailure("供应商已响应，但模型没有返回文本。", 502, "empty_probe")
        return "连接成功 · " + "".join(texts)[:80]
    finally:
        gateway.selected_override = None
        gateway.stop()


Router = Gateway
