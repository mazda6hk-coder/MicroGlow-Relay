"""缓存命中 / 推理 token 的采集口径、落盘字段与统计分母。

背景（2026-10-13）：上游一直在 usage 里返回 input_tokens_details.cached_tokens，
中继只取了 input/output 两个数，把缓存明细整个丢掉，于是「日均 6.9 亿 token」
只有原始口径、没有可用口径。这里锁住修好之后的口径。
"""
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

import httpx  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from records import ActivityLog, cache_hit_rate  # noqa: E402
from server import Gateway, usage_detail_counts  # noqa: E402
from storage import ROUTER_MODEL, Settings  # noqa: E402


class UsageDetailTests(unittest.TestCase):
    """上游字段名各家不一，四种形态都要认得。"""

    def test_every_supported_upstream_shape(self):
        cases = [
            ({"input_tokens": 2796, "input_tokens_details": {"cached_tokens": 2560},
              "output_tokens": 16, "output_tokens_details": {"reasoning_tokens": 16}},
             (2560, 16)),
            ({"prompt_tokens_details": {"cached_tokens": 128},
              "completion_tokens_details": {"reasoning_tokens": 8}}, (128, 8)),
            ({"prompt_cache_hit_tokens": 64}, (64, None)),
            ({"cache_read_input_tokens": 32}, (32, None)),
        ]
        for usage, expected in cases:
            with self.subTest(usage=usage):
                self.assertEqual(usage_detail_counts(usage), expected)

    def test_missing_detail_is_none_but_explicit_zero_is_an_answer(self):
        self.assertEqual(usage_detail_counts(None), (None, None))
        self.assertEqual(usage_detail_counts({}), (None, None))
        self.assertEqual(usage_detail_counts({"input_tokens": 10}), (None, None))
        self.assertEqual(usage_detail_counts({"input_tokens_details": {"cached_tokens": 0}}),
                         (0, None))
        self.assertEqual(usage_detail_counts({"input_tokens_details": {"cached_tokens": -5}}),
                         (None, None))
        self.assertEqual(usage_detail_counts({"input_tokens_details": "nonsense"}), (None, None))

    def test_hit_rate_helper_refuses_to_invent_a_number(self):
        self.assertAlmostEqual(cache_hit_rate(25, 100, 3), 25.0)
        self.assertIsNone(cache_hit_rate(0, 0, 0))
        self.assertIsNone(cache_hit_rate(10, 100, 0))
        self.assertIsNone(cache_hit_rate(10, 0, 5))


class ActivityLogCacheTests(unittest.TestCase):
    PROFILE = {"id": "model-demo", "provider_name": "深度探索", "model": "deepseek-flash"}

    def _row(self, **fields):
        base = {"timestamp": datetime(2026, 10, 13, 12).timestamp(), "ok": True, "status": 200,
                "input_tokens": 400, "output_tokens": 20}
        base.update(fields)
        return base

    def _write(self, log, rows):
        log.path.parent.mkdir(parents=True, exist_ok=True)
        log.path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def _summary(self, log):
        return log.range_summary(date(2026, 10, 13), date(2026, 10, 13))

    def test_rows_without_cache_data_stay_out_of_the_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(Path(directory))
            self._write(log, [self._row(cached_tokens=100), self._row()])
            stats = self._summary(log)
            self.assertEqual(stats["requests"], 2)
            self.assertEqual(stats["cache_reported"], 1)
            self.assertEqual(stats["cache_input_tokens"], 400)
            self.assertEqual(stats["cached_tokens"], 100)
            self.assertAlmostEqual(stats["cache_rate"], 25.0)

    def test_legacy_history_reports_no_rate_instead_of_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(Path(directory))
            self._write(log, [self._row(), self._row()])
            stats = self._summary(log)
            self.assertEqual(stats["cache_reported"], 0)
            self.assertIsNone(stats["cache_rate"])

    def test_cached_never_exceeds_the_input_it_belongs_to(self):
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(Path(directory))
            self._write(log, [self._row(cached_tokens=9999)])
            stats = self._summary(log)
            self.assertEqual(stats["cached_tokens"], 400)
            self.assertAlmostEqual(stats["cache_rate"], 100.0)

    def test_reasoning_tokens_are_totalled(self):
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(Path(directory))
            self._write(log, [self._row(reasoning_tokens=7, cached_tokens=0),
                              self._row(reasoning_tokens=5)])
            stats = self._summary(log)
            self.assertEqual(stats["reasoning_tokens"], 12)
            self.assertEqual(stats["cache_reported"], 1)
            self.assertAlmostEqual(stats["cache_rate"], 0.0)

    def test_add_writes_the_fields_only_when_the_upstream_reported_them(self):
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(Path(directory))
            log.add(profile=self.PROFILE, elapsed=1.0, status=200,
                    input_tokens=400, output_tokens=20, cached_tokens=256, reasoning_tokens=9)
            log.add(profile=self.PROFILE, elapsed=1.0, status=200,
                    input_tokens=400, output_tokens=20)
            lines = [json.loads(line) for line in
                     log.path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(lines[0]["cached_tokens"], 256)
            self.assertEqual(lines[0]["reasoning_tokens"], 9)
            self.assertNotIn("cached_tokens", lines[1])
            self.assertNotIn("reasoning_tokens", lines[1])

    def test_today_exposes_the_same_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(Path(directory))
            log.add(profile=self.PROFILE, elapsed=2.0, status=200,
                    input_tokens=1000, output_tokens=50, cached_tokens=900, reasoning_tokens=10)
            log.add(profile=self.PROFILE, elapsed=2.0, status=500, input_tokens=200, output_tokens=0)
            stats = log.today()
            self.assertEqual((stats["input_tokens"], stats["output_tokens"]), (1200, 50))
            self.assertEqual(stats["cache_reported"], 1)
            self.assertEqual(stats["cached_tokens"], 900)
            self.assertEqual(stats["reasoning_tokens"], 10)
            self.assertAlmostEqual(stats["cache_rate"], 90.0)

    def test_index_from_before_this_change_still_loads(self):
        from records import _empty_bucket, _validate_bucket

        clean = _validate_bucket({"requests": 3, "tokens": 90, "models": {}, "errors": {}})
        self.assertEqual(clean["cache_reported"], 0)
        self.assertEqual(clean["cached_tokens"], 0)
        self.assertEqual(clean["cache_input_tokens"], 0)
        self.assertEqual(set(_empty_bucket()) - set(clean), set())


class ChatUsagePathTests(unittest.TestCase):
    """chat 通道的明细也要落盘 —— 这条路径最容易在缩进上失手，锁一条端到端。"""

    def setUp(self):
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                return

            def do_POST(self):
                size = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(size)
                chunks = [
                    {"choices": [{"delta": {"content": "O"}, "finish_reason": None}]},
                    {"choices": [{"delta": {"content": "K"}, "finish_reason": "stop"}]},
                    {"choices": [], "usage": {
                        "prompt_tokens": 1000, "completion_tokens": 20,
                        "prompt_tokens_details": {"cached_tokens": 768},
                        "completion_tokens_details": {"reasoning_tokens": 12}}},
                ]
                body = "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
                raw = (body + "data: [DONE]\n\n").encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(Path(self.temp.name))
        saved = self.settings.upsert({
            "provider": "自定义 / 中转服务",
            "provider_name": "测试供应商",
            "base_url": "http://127.0.0.1:%d/v1/chat/completions" % self.server.server_port,
            "protocol": "chat",
            "model": "demo-model",
            "input_tokens": 128000,
            "output_tokens": 8192,
            "tool_calls": True,
            "image_input": True,
            "thinking": False,
            "reasoning_effort": "中",
        }, "sk-test")
        self.settings.select(saved["id"])
        self.gateway = Gateway(self.settings, with_telemetry=False, load_activity=False)
        self.gateway.start(0)

    def tearDown(self):
        self.gateway.stop()
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def test_chat_usage_details_reach_the_log_file(self):
        response = httpx.post(
            "http://127.0.0.1:%d/v1/responses" % self.gateway.port,
            headers={"Authorization": "Bearer " + self.settings.local_token()},
            json={"model": ROUTER_MODEL, "input": "hello", "stream": False},
            timeout=20)
        self.assertEqual(response.status_code, 200)
        log = Path(self.temp.name) / "microglow-relay-usage.jsonl"
        # 响应是在落盘之前写回客户端的，所以这里要稍等一下，不能刚 POST 完就读文件。
        deadline = time.monotonic() + 5
        while not log.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["input_tokens"], 1000)
        self.assertEqual(rows[0]["cached_tokens"], 768)
        self.assertEqual(rows[0]["reasoning_tokens"], 12)


if __name__ == "__main__":
    unittest.main()
