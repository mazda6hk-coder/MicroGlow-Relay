"""End-to-end check of the packaged executable.

Starts a local mock supplier, points a temporary profile at it, integrates the
sandboxed Codex home, launches the selected EXE and verifies that a real
request travels through the frozen gateway.

Usage::

    python tools/verify_exe.py MicroGlow-Relay-0.6.exe
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]

for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

import httpx  # noqa: E402

from codex_config import integrate, restore  # noqa: E402
from storage import ROUTER_MODEL, Settings, VERSION  # noqa: E402


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class MockSupplier:
    """Minimal Chat Completions SSE supplier."""

    def __init__(self):
        outer = self
        self.requests = []

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                return

            def do_POST(self):
                size = int(self.headers.get("Content-Length") or 0)
                outer.requests.append(json.loads(self.rfile.read(size)))
                chunks = [
                    {"choices": [{"delta": {"content": "OK"}, "finish_reason": None}]},
                    {"choices": [{"delta": {}, "finish_reason": "stop"}],
                     "usage": {"prompt_tokens": 7, "completion_tokens": 2}},
                ]
                body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
                payload = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1/chat/completions"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def prepare(scratch: Path) -> tuple[Settings, int]:
    os.environ["CODEX_HOME"] = str(scratch / "codex")
    settings = Settings(scratch / "data")
    port = free_port()
    settings.set_port(port)
    return settings, port


def wait_until_ready(port: int, timeout: float = 60.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
            if response.status_code == 200:
                return True
        except Exception:  # noqa: BLE001 - the service simply is not up yet
            time.sleep(0.4)
    return False


def terminate_tree(process: subprocess.Popen) -> None:
    """Stop the launched process and every child it spawned.

    PyInstaller one-file builds run as a bootloader process that re-executes the
    real application as a child.  ``Popen.terminate()`` only signals the
    bootloader, leaving the actual gateway alive and holding the EXE file plus
    its listening port.  Kill the whole tree instead.
    """
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", nargs="?", type=Path,
                        default=ROOT / f"MicroGlow-Relay-{VERSION}.exe")
    args = parser.parse_args()
    executable = args.executable.resolve(strict=True)
    scratch = Path(tempfile.mkdtemp(prefix="relay-exe-e2e-", dir=ROOT / "work"))

    supplier = MockSupplier()
    settings, port = prepare(scratch)
    settings.upsert({
        "provider": "自定义 / 中转服务",
        "provider_name": "端到端模拟",
        "protocol": "chat",
        "base_url": supplier.url,
        "model": "mock-model",
        "input_tokens": 128000,
        "output_tokens": 1024,
        "tool_calls": False,
        "image_input": False,
        "thinking": False,
        "reasoning_effort": "中",
    }, "sk-e2e")
    integrate(settings)

    process = subprocess.Popen([str(executable), "--headless", "--data-dir", str(settings.directory)], cwd=str(ROOT))
    try:
        if not wait_until_ready(port):
            raise SystemExit("打包后的服务未在超时时间内启动。")
        print(f"服务已就绪 · 127.0.0.1:{port}")

        token = settings.local_token()
        response = httpx.post(
            f"http://127.0.0.1:{port}/v1/responses",
            headers={"Authorization": "Bearer " + token},
            json={"model": ROUTER_MODEL, "input": "ping", "stream": False,
                  "max_output_tokens": 64},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        text = "".join(
            part.get("text", "")
            for item in body.get("output", []) if item.get("type") == "message"
            for part in item.get("content", [])
        )
        if text != "OK":
            raise SystemExit(f"路由返回内容异常：{text!r}")
        usage = body.get("usage", {})
        print(f"路由返回 · 文本={text!r} 用量={usage}")
        print(f"上游收到请求 · model={supplier.requests[0]['model']} "
              f"stream={supplier.requests[0]['stream']}")

        unauthorized = httpx.post(
            f"http://127.0.0.1:{port}/v1/responses",
            json={"model": ROUTER_MODEL, "input": "ping"},
            timeout=10,
        )
        if unauthorized.status_code != 401:
            raise SystemExit(f"未携带令牌的请求未被拒绝：{unauthorized.status_code}")
        print("令牌校验 · 未授权请求已返回 401")
    finally:
        terminate_tree(process)
        supplier.close()
        try:
            restore(settings)
        except Exception:  # noqa: BLE001 - sandbox cleanup is best effort
            pass

    print(f"\n打包产物端到端验证通过。隔离记录：{scratch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
