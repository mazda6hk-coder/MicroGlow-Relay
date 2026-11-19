# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Render every 0.5 page under every theme so the visual pass is evidence, not memory.

001的验收物：七主题 × 四页面实际运行截图。脚本只读配置、
不发起任何上游请求；模型与用量都是合成数据，避免把真实地址或密钥写进图片。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SANDBOX = Path(tempfile.gettempdir()) / "microglow-relay-shots"
CODEX_HOME = SANDBOX / "codex"
CODEX_HOME.mkdir(parents=True, exist_ok=True)
os.environ["CODEX_HOME"] = str(CODEX_HOME)

from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication, QScrollArea  # noqa: E402

from server import Gateway  # noqa: E402
from storage import Settings  # noqa: E402

from app import theme  # noqa: E402
from app.bridge import Bridge  # noqa: E402
from app.i18n import set_language  # noqa: E402
from app.window import Shell  # noqa: E402


OUTPUT = ROOT / "work" / "ui-shots"
PAGES = ("dashboard", "models", "codex", "logs", "settings")
SIZE = (1549, 1007)
# 设置页的 Codex 接入区在首屏之下；只截首屏等于没验收它。
SCROLLS = {"settings": 620}


def sample_profiles() -> list[dict]:
    catalog = [
        ("deepseek-v4.1-flash", "官方 · DeepSeek"),
        ("kimi-k3-thinking", "中转 · 星野"),
        ("claude-opus-5", "官方 · Anthropic"),
        ("gpt-5.2-codex", "中转 · 云梯"),
        ("qwen3-max", "官方 · 阿里"),
    ]
    base = {"provider": "自定义 / 中转服务", "protocol": "chat",
            "base_url": "https://api.example.com/v1",
            "input_tokens": 128000, "output_tokens": 8192,
            "tool_calls": True, "image_input": True, "thinking": True,
            "reasoning_effort": "中"}
    return [dict(base, model=model, provider_name=provider) for model, provider in catalog]


def synthetic_records(gateway: Gateway) -> dict:
    """Deterministic today/yesterday totals so every theme shows the same state.

    错误类别必须用 telemetry.store.ERROR_CATEGORIES 里的真键，否则图表
    只能画出一排 0，看不出配色与排版是否正常。
    """
    from telemetry.store import ERROR_CATEGORIES

    today = date.today()
    models = {}
    plan = [("deepseek-v4.1-flash", 96, 4_182_233), ("kimi-k3-thinking", 41, 2_970_118),
            ("claude-opus-5", 18, 1_204_556), ("gpt-5.2-codex", 12, 903_471),
            ("qwen3-max", 6, 214_908)]
    for index, (name, requests, tokens) in enumerate(plan):
        models[name] = {"requests": requests, "tokens": tokens}
    errors = dict.fromkeys(ERROR_CATEGORIES, 0)
    errors.update({"unavailable": 3, "rate_limit": 2, "timeout": 1, "authentication": 1, "other": 1})
    return {"today": {"requests": 385, "success": 377, "failures": 8, "tokens": 132777122,
                      "input_tokens": 121_884_402, "output_tokens": 10_892_720,
                      "models": models, "errors": errors},
            "yesterday": {"requests": 341, "success": 336, "failures": 5, "tokens": 118_004_551,
                          "models": {name: {"requests": max(1, group["requests"] - 12),
                                            "tokens": max(1, group["tokens"] - 90_000)}
                                     for name, group in models.items()},
                          "errors": dict.fromkeys(ERROR_CATEGORIES, 0)},
            "span": (today - timedelta(days=30), today)}


def main() -> int:
    app = QApplication.instance() or QApplication([])
    font = Path("C:/Windows/Fonts/msyh.ttc")
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
        app.setFont(QFont("Microsoft YaHei", 9))

    SANDBOX.mkdir(parents=True, exist_ok=True)
    # 配置目录必须是干净的：Settings 会往里累积，重复跑就多出几份同名模型，
    # 截图里出现 36 条「配置」正是这个原因。
    profile_dir = SANDBOX / "profile"
    if profile_dir.exists():
        shutil.rmtree(profile_dir, ignore_errors=True)
    settings = Settings(profile_dir)
    settings.data["language"] = "zh-CN"
    set_language("zh-CN")
    gateway = Gateway(settings)
    bridge = Bridge(settings, gateway)

    # TRIP A/B：走真实写入路径攒出两段不同读数，截图才有内容可验收。
    # A 清零后重新计（文案落在"刚刚"），B 从三天前计（文案落在"天"这一档）。
    trip_profile = {"id": "synthetic", "provider": "自定义 / 中转服务",
                    "provider_name": "示例中转", "model": "deepseek-v4.1-flash"}
    for _ in range(40):
        gateway.activity.add(profile=trip_profile, elapsed=2.4, status=200,
                             input_tokens=18_640, output_tokens=1_208)
    gateway.activity.reset_trip("A")
    for _ in range(11):
        gateway.activity.add(profile=trip_profile, elapsed=1.9, status=200,
                             input_tokens=21_330, output_tokens=1_450)
    gateway.activity.trips._state["trips"]["B"]["reset_at"] -= 3 * 86400
    for index, profile in enumerate(sample_profiles()):
        saved = bridge.save_profile(profile, "synthetic-private-key")
        if index == 0:
            bridge.select_profile(saved["id"])

    fixtures = synthetic_records(gateway)
    span = fixtures["span"]

    def range_summary(start, end, **_kwargs):
        # 页面查询范围落在今天时给今天的数字；落在更早区间时给昨天的数字，
        # 这样环比箭头、环形图、条形图都有稳定可复现的内容。
        source = fixtures["today"] if end >= span[1] else fixtures["yesterday"]
        return dict(source, start=start, end=end)

    gateway.activity.range_summary = range_summary

    activity = gateway.activity

    def recent(limit=100):
        rows = []
        for index, (name, group) in enumerate(fixtures["today"]["models"].items()):
            tokens = group["tokens"]
            rows.append({"model": name, "provider": "示例中转",
                         "ok": index != 2, "status": 200 if index != 2 else 503,
                         "elapsed": 1.4 + index * 0.7,
                         "input_tokens": tokens // 3, "output_tokens": tokens // 3,
                         "timestamp": 1.0 + index})
        return rows[:int(limit)]

    activity.recent = recent

    events = [
        ("07:41:02", "success", "服务已启动 · 127.0.0.1:4141"),
        ("07:41:18", "info", "Codex 模型目录已写入（5 条配置）"),
        ("07:52:33", "success", "成功 · 2.1 秒 · Token 18,204"),
        ("08:03:11", "warning", "本地并发已满，请稍后重试。"),
        ("08:14:47", "error", "失败 · 30.0 秒 · Token 未知"),
    ]
    bridge.events.clear()
    for time_text, level, message in events:
        bridge.events.append({"time": time_text, "level": level, "message": message})
    bridge.events.append({"time": "08:15:02", "level": "success", "message": "成功 · 1.8 秒 · Token 9,120",
                          "request_result": {"ok": True, "elapsed": 1.8, "tokens": 9120,
                                             "cached": 1024, "reasoning": 512,
                                             "model": "kimi-k3-thinking"}})

    shell = Shell(bridge)
    shell.resize(*SIZE)
    shell.show()
    app.processEvents()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    written = []
    for theme_key in theme.THEME_LABELS:
        theme.apply_palette(theme_key)
        app.setStyleSheet(theme.stylesheet())
        shell.apply_theme(theme_key)
        for page_key in PAGES:
            shell.navigate(page_key)
            for _ in range(10):
                app.processEvents()
            scroller = shell.pages[page_key].findChild(QScrollArea)
            offsets = ((0, SCROLLS[page_key], ""), (0, SCROLLS[page_key], "-scrolled")) \
                if page_key in SCROLLS else ((0, 0, ""),)
            for _, offset, suffix in offsets:
                if scroller is not None and offset:
                    scroller.verticalScrollBar().setValue(offset)
                for _ in range(6):
                    app.processEvents()
                path = OUTPUT / f"{theme_key}-{page_key}{suffix}.png"
                shell.grab().save(str(path))
                written.append(path.name)
            if scroller is not None:
                scroller.verticalScrollBar().setValue(0)
                for _ in range(4):
                    app.processEvents()

    summary = {"output": str(OUTPUT), "count": len(written), "files": written,
               "themes": list(theme.THEME_LABELS)}
    (OUTPUT / "index.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    gateway.stop()
    print(json.dumps({"count": len(written), "output": str(OUTPUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())