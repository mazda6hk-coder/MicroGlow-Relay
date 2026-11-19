"""Restricted local Codex App Server transport. Never exposes raw responses."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import tomllib


class CompatibilityError(RuntimeError):
    """Only fixed, user-safe messages may cross the module boundary."""

class CodexRunningError(CompatibilityError):
    """Codex must be closed before changing its startup connection."""


def desktop_binary() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI" / "Codex" / "bin"
    candidates = list(root.glob("*/codex.exe")) if root.is_dir() else []
    if not candidates:
        raise CompatibilityError("未找到 Codex 桌面端核心，请指定 codex.exe 路径。")
    return max(candidates, key=lambda item: item.stat().st_mtime)


def ensure_codex_closed(allowed_pid: int | None = None) -> None:
    """Check process names only; never inspect process command lines or memory."""
    if os.name != "nt":
        raise CompatibilityError("首版会话兼容仅支持 Windows Codex 桌面端。")

    class ProcessEntry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise CompatibilityError("无法确认 Codex 是否已退出，未执行修改。")
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel.Process32FirstW(handle, ctypes.byref(entry))
        if not ok:
            raise CompatibilityError("无法确认 Codex 是否已退出，未执行修改。")
        while ok:
            if entry.szExeFile.casefold() in {"codex.exe", "codex-app.exe"} and entry.th32ProcessID != allowed_pid:
                raise CodexRunningError("请先正常退出 Codex 桌面端及 CLI，再进行会话兼容操作；不会强制关闭它们。")
            ok = kernel.Process32NextW(handle, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)


def thread_metadata(value: dict) -> dict:
    """Positive allowlist. preview/turns/items/extra/instructions never escape."""
    if not isinstance(value, dict):
        raise CompatibilityError("Codex 返回了不支持的会话格式。")
    clean = {key: value.get(key) for key in (
        "id", "name", "model", "modelProvider", "reasoningEffort", "updatedAt", "createdAt",
        "parentThreadId", "ephemeral")}
    for key in ("id", "model", "modelProvider", "reasoningEffort", "parentThreadId"):
        if clean[key] is not None and not isinstance(clean[key], str):
            raise CompatibilityError("Codex 返回了不支持的会话格式。")
    state = value.get("status")
    clean["status"] = state.get("type", "unknown") if isinstance(state, dict) else "unknown"
    # A title is metadata; never fall back to the first-message preview.
    clean["name"] = clean["name"] if isinstance(clean["name"], str) else "未命名会话"
    return clean


def filtered_result(method: str, value: dict) -> dict:
    if method == "thread/list":
        return {"data": [thread_metadata(row) for row in value.get("data", [])],
                "nextCursor": value.get("nextCursor")}
    if method in {"thread/read", "thread/resume"}:
        return {"thread": thread_metadata(value.get("thread", {})),
                "model": value.get("model"), "modelProvider": value.get("modelProvider")}
    if method == "account/read":
        return {"type": (value.get("account") or {}).get("type")}
    return {}


class CodexClient:
    """One short-lived local process, no HTTP implementation, no turn execution."""

    METHODS = {"initialize", "thread/list", "thread/read", "thread/resume",
               "thread/unsubscribe", "account/read"}

    def __init__(self, executable: Path, home: Path, workspace: Path, *, timeout=15.0,
                 guard=ensure_codex_closed, deadline=None, config_overrides=()):
        self.guard, self.timeout = guard, timeout
        self.deadline = deadline
        self.process = None
        self.sequence = 0
        self.pending = {}
        self.messages = queue.Queue(maxsize=16)
        self._write_lock = threading.Lock()
        guard()
        try:
            workspace.mkdir(parents=True, exist_ok=True)
            # Disable user MCP servers for this helper process only. Do not edit config.toml.
            source = home / "config.toml"
            config = tomllib.loads(source.read_text(encoding="utf-8-sig")) if source.exists() else {}
            overrides = ["analytics.enabled=false", "feedback.enabled=false", *config_overrides]
            if config.get("mcp_servers"):
                # CLI -c dotted paths do not decode TOML-quoted path segments:
                # mcp_servers."node_repl" creates a different, incomplete server.
                # Replace this helper's server table instead of inventing entries.
                overrides.append("mcp_servers={}")
            command = [str(executable), "app-server", "--stdio"]
            for override in overrides:
                command.extend(["-c", override])
            env = os.environ.copy()
            env["CODEX_HOME"] = str(home.resolve())
            env["RUST_LOG"] = "off"
            # Metadata helper never needs remote model/analytics services. No user proxy or
            # API credential is forwarded via the environment. Codex owns its account store.
            env = {k: v for k, v in env.items()
                   if not any(word in k.upper() for word in ("TOKEN", "SECRET", "API_KEY"))}
            env.update(HTTP_PROXY="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9",
                       ALL_PROXY="http://127.0.0.1:9", NO_PROXY="")
            guard()
            self.process = subprocess.Popen(command, cwd=workspace, env=env, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                            text=True, encoding="utf-8",
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.reader = threading.Thread(target=self._read, daemon=True)
            self.reader.start()
            self.call("initialize", {"clientInfo": {"name": "microglow_session_compat", "version": "1.0"},
                                     "capabilities": {"experimentalApi": True}})
            self._send({"method": "initialized", "params": {}})
        except CompatibilityError:
            self.close()
            raise
        except Exception:
            self.close()
            raise CompatibilityError("无法启动会话兼容接口；未回显底层信息。") from None

    def _remaining(self, maximum):
        remaining = maximum if self.deadline is None else min(maximum, self.deadline - time.monotonic())
        if remaining <= 0:
            raise CompatibilityError("本次操作时间已用尽，保留配置与备份，稍后可重新检查。")
        return remaining

    def _send(self, payload):
        with self._write_lock:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                    line = None
                    ident = message.get("id")
                    if "method" in message:
                        if ident is not None:
                            self._send({"id": ident, "error": {"code": -32601, "message": "Not supported"}})
                        continue  # Discard ALL notifications, including raw history events.
                    method = self.pending.get(ident)
                    if method:
                        result = None if "error" in message else filtered_result(method, message.get("result") or {})
                        self.messages.put_nowait((ident, result))
                finally:
                    # Raw payloads, previews and auth details never enter the queue or diagnostics.
                    message = None
                    line = None
        except Exception:
            pass
        finally:
            try:
                self.messages.put_nowait((None, None))
            except queue.Full:
                pass

    def call(self, method: str, params: dict) -> dict:
        if method not in self.METHODS:
            raise CompatibilityError("会话兼容接口不允许执行此操作。")
        if method == "thread/read" and params.get("includeTurns") is not False:
            raise CompatibilityError("禁止读取会话正文。")
        if method == "thread/resume" and (params.get("excludeTurns") is not True or
                                         set(params) - {"threadId", "modelProvider", "model", "excludeTurns"}):
            raise CompatibilityError("禁止读取或改写会话正文。")
        if method == "thread/list" and params.get("useStateDbOnly") is not True:
            raise CompatibilityError("禁止扫描会话正文。")
        if method == "account/read" and params != {"refreshToken": False}:
            raise CompatibilityError("禁止刷新或修改登录凭证。")
        self.guard(self.process.pid)
        self.sequence += 1
        ident = self.sequence
        self.pending[ident] = method
        try:
            deadline = time.monotonic() + self._remaining(self.timeout)
            self._send({"id": ident, "method": method, "params": params})
            while time.monotonic() < deadline:
                received, result = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
                if received is None:
                    raise CompatibilityError({
                        "initialize": "Codex 会话接口启动失败；尚未执行会话修改或生成本次备份。",
                        "thread/read": "Codex 会话接口读取失败；尚未执行本次切换。",
                    }.get(method, "Codex 接口未完成操作；请检查会话状态，不要重复执行。"))
                if received == ident and result is None:
                    reason = {
                        "initialize": "Codex 核心拒绝初始化；未读取或修改会话。",
                        "thread/read": "Codex 核心无法读取该会话配置；未修改会话。请刷新列表并确认会话仍可在 Codex 中打开。",
                        "account/read": "Codex 核心无法确认订阅登录状态；未修改会话。",
                        "thread/resume": "Codex 核心拒绝切换会话模式；原备份保留，未自动重试。",
                    }.get(method, "Codex 核心拒绝完成该操作；原备份保留。")
                    raise CompatibilityError(reason)
                if received == ident:
                    return result
            raise queue.Empty
        except CompatibilityError:
            raise
        except Exception:
            raise CompatibilityError("会话兼容操作超时或中断；保留已有备份，请重新检查配置状态。") from None
        finally:
            self.pending.pop(ident, None)

    def close(self):
        if self.process is None:
            return
        try:
            if self.process.poll() is None:
                self.process.stdin.close()
                try:
                    remaining = 1 if self.deadline is None else max(0, min(1, self.deadline - time.monotonic()))
                    self.process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    self.process.terminate()  # Only our own helper, never the user's Codex.
                    self.process.wait(timeout=0.5)
            if hasattr(self, "reader"):
                self.reader.join(timeout=0.2)
            self.process.stdout.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
