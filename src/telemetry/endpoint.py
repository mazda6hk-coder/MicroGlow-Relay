# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""生产遥测服务地址（唯一硬编码位置）。

协议实现见 ``transport.py``：POST ``/v1/telemetry/batches``。
这里的地址是交付方固定的生产入口，不做运行时改写、不接受用户输入覆盖；
本地调试如确需指向别处，只应通过测试内的依赖注入完成，而不是改这里。
"""
from __future__ import annotations

# 生产遥测入口（Cloudflare Tunnel -> 本机 telemetry-server / Caddy 8443）
TELEMETRY_HOST = "metrics.microglow.com.cn"
TELEMETRY_PATH = "/v1/telemetry/batches"
TELEMETRY_ENDPOINT_URL = "https://" + TELEMETRY_HOST + TELEMETRY_PATH

# 上传超时（秒）。失败一律静默，批次保留待重试，绝不阻塞 UI 或 Router。
TELEMETRY_TIMEOUT_SECONDS = 15.0

# 上行只发送聚合计数，不含任何请求/响应正文、密钥或标识。
TELEMETRY_CONTENT_TYPE = "application/json"

# 国别只由服务端依据可信连接来源瞬时推断；客户端不提供 country_code。
