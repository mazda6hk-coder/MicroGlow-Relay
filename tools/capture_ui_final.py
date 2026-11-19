# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Reproducible final-design captures using only isolated, synthetic local data.

No real client configuration, upstream request or telemetry upload is used.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def build_fixture(directory):
    from storage import Settings
    from trips import TripStore
    from records import LOG_NAME
    from server import Gateway
    from app.bridge import Bridge
    from app.i18n import set_language
    settings = Settings(directory)
    settings.data.update(language="zh-CN", theme="winter-day", day_night="day", motion="full")
    settings.save(); set_language("zh-CN")
    profiles = []
    for model, provider, count in (("deepseek-v4.1-flash", "深度探索", 3), ("glm-5.3", "智谱", 2),
        ("kimi-k3", "月之暗面", 2), ("qwen3.8-max", "千问", 1), ("qwen3.8-flash", "千问", 1),
        ("MiniMax-M3.1-flash", "MiniMax", 1), ("claude-opus-5-5", "Anthropic", 1), ("deepseek-flash", "深度探索", 1)):
        channels = [{"label": name, "base_url": "https://fixture.invalid/v1", "weight": 3 - i, "enabled": True}
                    for i, name in enumerate(("能出没", "鸡出没", "星思云")[:count])] if count > 1 else []
        profiles.append(settings.upsert(dict(provider="自定义 / 中转服务", provider_name=provider,
            base_url="https://fixture.invalid/v1", protocol="chat", model=model, channels=channels),
            "synthetic-not-real-a3f9", channel_keys=["synthetic-not-real-a3f9"] * count))
    settings.select(profiles[1]["id"])
    now = datetime.now(); midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = []
    for day in range(46, 0, -1):
        for i in range(3):
            moment = midnight - timedelta(days=day) + timedelta(hours=9 + i * 4)
            p = profiles[(day + i) % len(profiles)]
            rows.append(dict(timestamp=moment.timestamp(), time=moment.strftime("%Y-%m-%d %H:%M:%S"),
                profile_id=p["id"], provider=p["provider_name"], model=p["model"],
                client="anthropic" if i % 2 else "responses", status=200, ok=True, elapsed=2.8,
                input_tokens=50_000_000 + day * 1753, output_tokens=350_000,
                cached_tokens=20_000_000, cache_creation_input_tokens=100_000, channel_index=0,
                **({"mitigated": "timeout"} if day % 5 == 0 and i == 0 else {})))
    for i in range(187):
        moment = midnight + timedelta(seconds=(now - midnight).total_seconds() * (i + 1) / 188)
        p = profiles[2] if i < 115 else profiles[1] if i < 183 else profiles[0]
        tokens = 46_985_655 // 187 + (i < 46_985_655 % 187)
        rows.append(dict(timestamp=moment.timestamp(), time=moment.strftime("%Y-%m-%d %H:%M:%S"),
            profile_id=p["id"], provider=p["provider_name"], model=p["model"], client="responses",
            status=400 if i in (170,172,174,176,178,180,186) else 200, ok=i not in (170,172,174,176,178,180,186),
            elapsed=2.8 if i % 4 else 3.7, input_tokens=tokens - 1024, output_tokens=1024,
            cached_tokens=50_000, cache_creation_input_tokens=0, channel_index=i % max(1, len(p["channels"])),
            **({"mitigated": {0:"rate_limit",185:"timeout",2:"unavailable"}[i]} if i in (0,185,2) else {})))
    (directory / LOG_NAME).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    store = TripStore(directory, log_name=LOG_NAME)
    store._state["trips"]["A"]["reset_at"] = (midnight - timedelta(days=7)).timestamp()
    store._state["trips"]["A"]["scope"] = "anthropic"
    store._state["trips"]["B"]["reset_at"] = (midnight - timedelta(days=3)).timestamp()
    store._dirty = True; store.flush()
    gateway = Gateway(settings, with_telemetry=True)
    gateway.telemetry.uploader = None
    bridge = Bridge(settings, gateway)
    # Feed historical segments through the same Trip folding/snapshot code.
    for index, name in enumerate(("周报脚本", "", "接口联调", "文档翻译", "", "重写解析器", "性能优化", "单元测试补全")):
        segment = TripStore(directory / f"segment-{index}", log_name="fixture.jsonl")
        for key in ("A", "B"): segment._state["trips"][key]["reset_at"] = 0
        chosen = rows[index * 12:(index + 1) * 12]
        for row in chosen: segment._fold(row)
        key = "A" if index % 2 == 0 else "B"
        segment.rename(key, name)
        segment.set_scope(key, ("responses", "all", "anthropic")[index % 3])
        entry = gateway.trip_ledger.snapshot(key, segment.summary())
        entry["to"] = chosen[-1]["timestamp"]
        entry["elapsed"] = entry["to"] - entry["from"] if entry["from"] else 0
    gateway.trip_ledger._save()
    bridge.set_telemetry_consent(True)
    gateway.telemetry.record_request(provider="custom", model="glm-5.3", status=200, elapsed_seconds=2.8,
        input_tokens=1024, output_tokens=128, call_channel="relay")
    bridge.events.clear()
    messages = [
        ("22:16:52", "error", "glm-5.3 · 失败 400 · 64.7s"),
        ("22:16:52", "warning", "上游 400，未命中推理项形态提示，未重放"),
        ("22:16:40", "warning", "上游连接失败，已重试 2 次 · 等待 1.5s"),
        ("22:16:06", "warning", "上游连接失败，已重试 1 次 · 等待 0.75s"),
        ("22:14:14", "info", "Codex 已重新指向本路由器"),
        ("22:14:12", "success", "Codex 已接入"),
        ("22:14:10", "success", "服务已启动 · 127.0.0.1:4141"),
        ("22:13:14", "info", "MicroGlow Relay 已启动"),
        ("22:12:49", "success", "glm-5.3 · 重试后成功 · 71.5s"),
        ("21:24:28", "success", "claude-opus-5-5 · 成功 · 55.9s"),
        ("21:23:32", "success", "glm-5.3 · 成功 · 29.0s"),
        ("21:20:11", "success", "kimi-k3 · 成功 · 12.4s"),
        ("21:18:03", "success", "kimi-k3 · 成功 · 9.8s"),
        ("21:15:40", "success", "glm-5.3 · 成功 · 14.2s"),
        ("21:12:09", "success", "glm-5.3 · 成功 · 11.7s"),
        ("21:08:55", "success", "kimi-k3 · 成功 · 8.6s"),
    ]
    for stamp, level, message in reversed(messages):
        bridge.events.append(dict(time=stamp, level=level, message=message))
    return settings, gateway, bridge


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "docs/UI-FINAL-IMPLEMENT/screenshots")
    parser.add_argument("--size", default="2010x1350"); parser.add_argument("--themes", default="winter-day,winter-night,spring-day")
    parser.add_argument("--interactions", action="store_true")
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.gettempdir())/"relay-ui-final"; temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="capture-", dir=temp_root) as temporary:
        directory = Path(temporary); os.environ["CODEX_HOME"] = str(directory / "codex"); os.environ["CLAUDE_CONFIG_DIR"] = str(directory / "claude")
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtWidgets import QApplication
        from app import theme
        from app.window import Shell
        app = QApplication.instance() or QApplication([])
        theme.apply_palette("winter-day"); app.setStyleSheet(theme.stylesheet())
        settings, gateway, bridge = build_fixture(directory)
        # Connection status is a visual fixture; no real client file is touched.
        with patch.object(bridge, "status", return_value="active"), patch.object(bridge, "claude_status", return_value="none"):
            gateway.start(0)
            shell = Shell(bridge); shell.resize(*map(int, args.size.split("x"))); shell.show()
            written = []
            for theme_key in args.themes.split(","):
                bridge.set_day_night_mode(theme_key.rpartition("-")[2])
                shell.apply_theme(theme_key)
                for key, tab, number in (("dashboard", None, "01"), ("models", None, "02"), ("logs", "usage", "03"), ("logs", "trips", "04"), ("settings", None, "05")):
                    shell.navigate(key)
                    if tab: shell.pages["logs"].show_tab(tab)
                    if key == "models":
                        shell.pages["models"].selected_model = "deepseek-v4.1-flash"
                        shell.pages["models"].rebuild()
                    if tab == "trips":
                        records = bridge.trip_ledger_entries()
                        shell.pages["logs"]._selected_trip = records[-1]["id"]
                        shell.pages["logs"]._refresh_trips()
                    for _ in range(5): app.processEvents()
                    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                    path = args.output / f"{theme_key}-{number}-{tab or key}.png"
                    shell.grab().save(str(path)); written.append(path.name)
            if args.interactions:
                from PySide6.QtCore import Qt
                from PySide6.QtTest import QTest
                bridge.set_day_night_mode("day"); shell.apply_theme("winter-day"); shell.navigate("dashboard")
                page = shell.pages["dashboard"]; page._scope("A", "responses")
                title = page.trip_slots["A"]["name"]
                states = args.output / "interactions"; states.mkdir(exist_ok=True)
                def save_state(name):
                    for _ in range(5): app.processEvents()
                    path = states / (name + ".png"); shell.grab().save(str(path))
                    written.append("interactions/" + path.name)
                title.enterEvent(None); save_state("01-hover")
                title.pencil.click(); title.editor.setText("周报脚本"); save_state("02-editing")
                QTest.keyClick(title.editor, Qt.Key_Return); title.leaveEvent(None); save_state("03-named")
                page.trip_slots["A"]["reset"].click(); save_state("04-reset-undo")
            shell.hide(); shell.deleteLater(); app.processEvents(); gateway.close()
        (args.output / "index.json").write_text(json.dumps(dict(files=written, size=args.size,
            data="isolated synthetic fixture; no real client configuration or upstream traffic"), ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(dict(count=len(written), output=str(args.output)), ensure_ascii=False))


if __name__ == "__main__": main()
