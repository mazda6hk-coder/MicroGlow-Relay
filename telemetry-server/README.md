# MicroGlow 遥测采集服务

分析后台的冻结统计定义见 [`STATISTICS_DEFINITIONS.md`](STATISTICS_DEFINITIONS.md)。

这是 MicroGlow API Router 的独立匿名遥测采集服务。

服务只接收用户明确同意后上传的每日汇总统计，不负责 API 中转、模型调用、推理、用户账户或付费功能，也不会接收或保存 Prompt、Response、对话内容、文件、代码、工具参数及原始请求/响应正文。管理员可通过内置决策面板查看匿名汇总结果。

## 核心隐私原则

- 遥测必须由用户明确选择加入（opt-in），默认关闭。
- 用户拒绝遥测不会影响 API Router 的正常功能。
- 客户端只上传按日聚合的匿名统计，不上传逐次请求记录。
- 服务端不保存原始遥测 JSON。
- 原始 `installation_id` 在入库前使用服务端密钥执行 HMAC-SHA-256 转换；数据库只保存 `installation_hash`。
- 服务日志不记录请求正文、完整 IP、Authorization Header、Token、密钥或 installation ID。
- 管理员 Token 与 installation ID 完全独立，二者不可互换。

schema v1 允许上传的汇总字段包括：

- `country_code`（仅兼容旧客户端的可选字段；服务端不会把它当作可信国别来源）
- `client_version`
- `operating_system`
- `provider`
- `model` 或 `model_family`
- `active_minutes`
- `api_call_count`
- `success_count`
- `error_count`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `aggregation_day`

所有未列入请求结构的字段都会被拒绝。

schema v2 在继续禁止原始内容的前提下，额外允许三类匿名汇总：固定延迟区间计数、固定错误类别计数和回退次数。schema v1/v2 必须分别精确匹配服务端配置的 `CONSENT_VERSION_V1` / `CONSENT_VERSION_V2`，不能只凭前缀通过。

## 服务组成

Docker Compose 会启动以下组件：

- `telemetry-api`：公开遥测采集接口。
- `telemetry-admin`：独立的管理员汇总接口。
- `postgres`：PostgreSQL 数据库，仅位于 Docker 内部网络。
- `migrate`：启动时执行数据库迁移，成功后退出。
- `gateway`：Caddy HTTPS 网关。
- `backup`：立即执行一次数据库备份，之后每 24 小时备份一次。
- `geoip-updater`：从 DB-IP 官方地址检查月度国家级 MMDB，校验后原子更新。

公开采集服务与管理员服务使用不同进程和端口。PostgreSQL、迁移服务及应用内部端口均不发布到宿主机。

## 快速启动

进入本目录后复制环境变量模板：

```sh
cp .env.example .env
```

编辑 `.env`，将所有占位值替换为独立生成的高强度随机值，尤其是：

- `POSTGRES_PASSWORD`
- `INSTALLATION_HMAC_SECRET`
- `ADMIN_TOKEN`

启动服务：

```sh
docker compose up --build -d
```

查看服务状态：

```sh
docker compose ps
```

停止服务：

```sh
docker compose down
```

不要在生产环境执行 `docker compose down -v`，因为 `-v` 会删除数据库和备份卷。

## 网络与 HTTPS

默认地址：

- 公开采集接口：`https://localhost:8443`
- 管理员接口：`https://localhost:9443`

管理员端口只绑定宿主机回环地址 `127.0.0.1`，不能直接从其他主机访问。
公开采集端口 `8443` 也只绑定宿主机回环地址，供同机运行的 MicroGlow Cloudflare Tunnel 接入。Caddy 启动时自动识别当前 Docker 网桥网关作为唯一可信的 Tunnel 对端，不依赖本机固定地址；迁移到同机部署 Tunnel 的 VPS 时无需复制开发机网桥地址。若 Tunnel 部署在另一主机或容器，需按实际网络边界显式设置 `TUNNEL_PEER_CIDR` 并调整入口连接方式。

本地部署使用 Caddy 内部 CA 签发证书。生产部署应使用受信任的正式证书，或在服务前部署受信任的 TLS 负载均衡器，同时确保内部 Python HTTP 端口不对公网开放。

生产环境需要在 `.env` 中设置对应 DNS 名称：

```dotenv
PUBLIC_HOST=telemetry.example.com
ADMIN_HOST=telemetry-admin.example.com
```

如果管理员接口需要远程访问，建议通过 VPN、SSH 隧道或受控内部网络访问，不要直接暴露到公网。

### 本地证书信任

本地 Caddy 使用内部 CA，浏览器第一次访问时可能显示 `ERR_CERT_AUTHORITY_INVALID`。如需在当前 Windows 用户下信任该本地 CA，可在服务启动后运行：

```powershell
.\scripts\trust-local-caddy-ca.ps1
```

该操作会修改当前用户的受信任根证书库，因此应只在可信开发机上执行。移除信任：

```powershell
.\scripts\trust-local-caddy-ca.ps1 -Remove
```

## 遥测批次接口

### `POST /v1/telemetry/batches`

请求必须包含：

- `schema_version`
- `batch_id`
- `installation_id`
- `consent_version`
- `consent: true`
- `client_version`
- `aggregated_rows`

示例请求：

```json
{
  "schema_version": 1,
  "batch_id": "batch_0123456789abcdef",
  "installation_id": "installation_0123456789abcdef",
  "consent_version": "2026-09",
  "consent": true,
  "client_version": "5.0.0",
  "aggregated_rows": [
    {
      "client_version": "5.0.0",
      "operating_system": "windows",
      "provider": "openai",
      "model": "gpt-5",
      "active_minutes": 20,
      "api_call_count": 10,
      "success_count": 8,
      "error_count": 2,
      "input_tokens": 1000,
      "output_tokens": 500,
      "total_tokens": 1500,
      "aggregation_day": "2026-09-21"
    }
  ]
}
```

正常接收后返回明确 ACK：

```json
{
  "ack": true,
  "batch_id": "batch_0123456789abcdef",
  "duplicate": false,
  "accepted_rows": 1
}
```

接口行为：

- 未提供 `consent: true` 时返回 HTTP 422。
- 未声明字段、字段类型错误、数值越界或汇总关系不一致时返回 HTTP 422。
- 默认请求体上限为 1 MiB。
- 默认每批最多包含 500 条汇总行。
- `success_count + error_count` 必须等于 `api_call_count`。
- `input_tokens + output_tokens` 必须等于 `total_tokens`。
- 新客户端不发送 `country_code`。旧客户端若仍发送，必须是大写 ISO 3166-1 alpha-2 国家代码；服务端会忽略该值，并以可信连接来源的本地 GeoIP 结果覆盖。
- 每行必须提供 `model` 或 `model_family`，且只能提供其中一个。
- `active_minutes` 必须是客户端本地累计并取整后的非负整数。

### Schema v2 质量汇总

schema v2 只接受固定结构的汇总计数，不接受单次请求记录：

```json
{
  "schema_version": 2,
  "consent_version": "v2.2026-09",
  "aggregated_rows": [
    {
      "latency_buckets": {
        "lt_1s": 80,
        "from_1s_to_3s": 30,
        "from_3s_to_10s": 8,
        "gte_10s": 2
      },
      "error_category_counts": {
        "authentication": 0,
        "rate_limit": 2,
        "timeout": 3,
        "unavailable": 1,
        "invalid_request": 0,
        "other": 0
      },
      "fallback_count": 4
    }
  ]
}
```

上述对象需与该行其他必填字段一起上传，并满足：

- 所有延迟区间计数之和等于 `api_call_count`。
- 所有错误类别计数之和等于 `error_count`。
- `fallback_count` 不得超过 `api_call_count`。
- schema v1 不得携带这些字段。
- 不接收原始延迟值、原始错误消息、完整 IP 或请求级记录。

### 批次幂等规则

`batch_id` 是批次的幂等键。

- 首次提交成功后计入统计，并返回 `duplicate: false`。
- 使用相同 `batch_id` 和相同内容重复提交时不会重复计数，并返回 `duplicate: true`。
- 使用相同 `batch_id` 提交不同内容时返回 HTTP 409。
- 批次写入和每日统计更新位于同一个 PostgreSQL 事务中，不会出现批次已确认但统计只写入一部分的情况。

### 客户端 ACK 处理要求

客户端只有在收到 HTTP 2xx，且响应中包含匹配的 `ack: true` 和 `batch_id` 后，才能把本地批次标记为已完成。

遇到以下情况时，客户端必须保留本地批次：

- 网络不可用或连接超时。
- 服务端不可用。
- 返回非 2xx 状态码。
- ACK 缺失、格式错误或 `batch_id` 不匹配。

保留的批次应在下一次正常关闭时重试。遥测上传失败不得阻止 Router 启动或关闭，服务端也不会要求客户端在启动时上传。

## 服务端 GeoIP 国别推断

国别统计的权威来源是服务端本地的 **DB-IP Lite IP-to-Country MMDB**。遥测接入层只在内存中瞬时取得可信连接来源地址并查询国家；查询结束后不保存原始地址。客户端不需要、也不得读取、保存或上传完整 IP，不集成 GeoIP 库。

来源地址信任链如下：

1. socket 对端不在 `TRUSTED_PROXY_CIDRS` 时，只使用 socket 对端地址，忽略所有转发 Header；
2. socket 对端位于明确配置的可信代理网段时，只解析该代理追加的 `X-Forwarded-For` 链；
3. 不信任任意来源提交的 `X-Real-IP`、`Forwarded` 或自定义 IP Header；
4. 来源缺失、代理链非法、数据库缺失/损坏/无匹配或查询异常时，存储 `country_code = NULL` 和 `country_source = COUNTRY-SOURCE-GAP`，合法批次仍正常接收。

成功推断时只写入大写 ISO 3166-1 alpha-2 国家代码，并写入 `country_source = GEOIP`。`COUNTRY-SOURCE-GAP` 不会写进 `country_code`，也不会以 `ZZ` 或默认国家伪装。

Compose 固定后端子网为 `172.30.0.0/24`，并默认只信任该网段内的 Caddy。生产环境变更 Docker/代理网络后，必须同步设置精确的 `BACKEND_SUBNET` 与 `TRUSTED_PROXY_CIDRS`；不得配置 `*` 或不受控的大网段。Uvicorn 的通配转发信任已关闭。

### DB-IP 自动更新与校验

`geoip-updater` 每日检查一次当月官方文件（同一月份且本地 SHA-256 匹配时不会重复下载）。下载使用临时文件，依次执行 gzip 解压验证、MMDB 格式/国家库类型验证、压缩包与 MMDB SHA-256 计算，全部成功后才原子替换。更新失败会保留旧数据库；没有旧数据库时服务继续运行并使用 `COUNTRY-SOURCE-GAP`。

运行时元数据保存在 `data/geoip/dbip-country-lite.metadata.json`，记录实际下载地址、发布日期、许可、ETag、Last-Modified、两份 SHA-256 和 MMDB 构建版本。可选的 `DBIP_EXPECTED_SHA256` 可固定压缩包校验值。数据来源与许可归属见 [`DBIP_ATTRIBUTION.md`](DBIP_ATTRIBUTION.md)。数据库文件被 `.gitignore` 和 `.dockerignore` 排除，不会进入应用镜像或客户端。

## 健康检查

### `GET /health`

成功响应：

```json
{
  "status": "ok"
}
```

该接口只报告服务健康状态，不返回任何统计数据。

## 管理员汇总接口

### 图形化决策面板

浏览器访问：

```text
https://localhost:9443/admin/
```

输入 `.env` 中的 `ADMIN_TOKEN` 后，页面会通过同源 API 加载匿名汇总数据。面板提供：

- 活跃安装、API 调用、Token、成功率和错误数量核心指标。
- DAU、WAU、MAU、周增长率和 7/30 日留存。
- 日、周、月使用趋势及新增/回访安装数。
- 国家调用分布。
- Provider / Model 排名、消耗占比及月度份额趋势。
- 每活跃安装均值和 P50/P90/P99 使用强度。
- 使用时长、延迟区间、标准化错误和回退统计。
- 客户端版本、数据新鲜度、Schema/Consent 覆盖。
- 日期范围筛选、JSON/CSV 导出和打印/PDF。

ADMIN_TOKEN 只保存在当前页面的 JavaScript 内存中，不写入 Cookie、LocalStorage 或 SessionStorage；刷新或关闭页面后需要重新输入。

### `GET /admin/usage/summary`

请求必须携带独立的管理员 Token：

```text
Authorization: Bearer <ADMIN_TOKEN>
```

未提供 Token 或 Token 不正确时返回 HTTP 401。`installation_id` 不能用于管理员鉴权。

接口返回：

- 按国家汇总的调用次数、Token 数量和活跃安装数量。
- 按 Provider、Model 或 Model Family 汇总的调用次数和 Token 数量。
- 按日、ISO 周和自然月汇总的 API 调用次数、Token 数量和活跃安装数量。
- 总活跃安装数量。
- 使用时长区间。
- 成功数量、错误数量及成功率。
- 通用错误类别统计。

schema v1 只能提供总体错误数量。schema v2 可提供认证、限流、超时、服务不可用、无效请求和其他六类固定计数。服务不会接收或保存原始错误消息及可能泄露敏感信息的详细错误内容。

## 数据库结构

迁移文件位于 `migrations/`，启动时按文件名顺序执行。`001_init.sql` 创建基础表，`002_quality_metrics.sql` 添加 schema v2 质量汇总列，`003_batch_day_bounds.sql` 添加批次日期范围，`004_server_geoip.sql` 冻结服务端国别来源约束。

### `telemetry_batches`

用于批次幂等检查，包含：

- `batch_id`
- `installation_hash`
- `schema_version`
- `consent_version`
- `received_at`
- `row_count`
- `payload_hash`

### `usage_daily`

用于保存匿名每日汇总，包含：

- 日期、可为空的国家代码、国别来源、操作系统
- Provider、Model、Model 类型
- 客户端版本
- HMAC 后的 installation hash
- 活跃分钟数
- API 调用、成功和错误数量
- 输入、输出和总 Token 数量
- 固定延迟区间、固定错误类别和回退次数汇总

日、周、月统计均由 `usage_daily` 动态生成，不要求客户端上传原始请求记录。

## 频率限制

默认限制：

- 公开采集接口：每个匿名客户端桶每分钟 60 次请求。
- 管理员接口：每个匿名客户端桶每分钟 30 次请求。

限流键由与 GeoIP 相同的可信来源解析结果经过内存中的 HMAC 计算产生。服务不会把完整 IP 写入数据库或日志，限流桶也不会作为遥测数据持久化。

可以通过环境变量调整限制：

```dotenv
PUBLIC_RATE_LIMIT_PER_MINUTE=60
ADMIN_RATE_LIMIT_PER_MINUTE=30
```

如果部署多个采集进程或多个节点，应在上游网关增加共享限流机制；应用内限流是单进程、短时限流。

## 数据库备份

`backup` 服务启动后会立即创建一次 PostgreSQL custom-format 备份，之后按配置间隔重复执行。

默认设置：

```dotenv
BACKUP_INTERVAL_SECONDS=86400
BACKUP_RETENTION_DAYS=14
```

备份保存在 `postgres-backups` Docker Volume 中。备份仅包含匿名汇总表，但仍应按照生产数据安全标准实施访问控制、异地复制、恢复演练和生命周期管理。

查看备份服务日志：

```sh
docker compose logs backup
```

## 日志安全

Uvicorn HTTP access log 已关闭。应用只记录以下不敏感运行信息：

- 已接受行数。
- 是否为重复批次。
- 服务启动及错误状态。

日志中不应出现：

- 请求正文
- 完整 IP
- API Key
- Authorization Header
- ADMIN_TOKEN
- installation ID
- Prompt、Response 或原始错误内容

生产环境还应确保外部反向代理、负载均衡器及云平台日志采用同等脱敏策略。

## 环境变量

完整示例见 `.env.example`。

| 变量 | 用途 |
| --- | --- |
| `POSTGRES_DB` | PostgreSQL 数据库名称 |
| `POSTGRES_USER` | PostgreSQL 用户名 |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 |
| `INSTALLATION_HMAC_SECRET` | installation ID HMAC 密钥，至少 32 个字符 |
| `ADMIN_TOKEN` | 独立管理员 Token，至少 32 个字符 |
| `CONSENT_VERSION_V1` | schema v1 精确允许的 Consent 版本 |
| `CONSENT_VERSION_V2` | schema v2 精确允许的 Consent 版本 |
| `PUBLIC_HOST` | 公开采集接口 DNS 名称 |
| `ADMIN_HOST` | 管理员接口 DNS 名称 |
| `MAX_BODY_BYTES` | 请求体大小上限 |
| `MAX_AGGREGATED_ROWS` | 每批最大行数，不能超过 500 |
| `PUBLIC_RATE_LIMIT_PER_MINUTE` | 公开接口每分钟请求上限 |
| `ADMIN_RATE_LIMIT_PER_MINUTE` | 管理接口每分钟请求上限 |
| `GEOIP_DATABASE_PATH` | API 容器内只读 MMDB 路径 |
| `TRUSTED_PROXY_CIDRS` | 可传递 X-Forwarded-For 的明确代理 CIDR 列表 |
| `TUNNEL_PEER_CIDR` | 可选；同宿主机 Tunnel 默认自动识别 Docker 网关，其他拓扑填写明确可信来源 CIDR |
| `BACKEND_SUBNET` | Compose 后端网络的固定 CIDR |
| `DBIP_UPDATE_CHECK_INTERVAL_SECONDS` | DB-IP 月度版本检查间隔，最小 3600 秒 |
| `DBIP_EXPECTED_SHA256` | 可选的当月压缩包固定 SHA-256 |
| `BACKUP_INTERVAL_SECONDS` | 备份间隔秒数 |
| `BACKUP_RETENTION_DAYS` | 备份保留天数 |

所有敏感配置必须通过环境变量提供，不要把 `.env`、密钥或生产 Token 提交到 Git。

## 测试

### 本地定向测试

```sh
python -m pip install -r requirements-test.txt
python -m pytest -q
```

未设置 `TEST_DATABASE_URL` 时，真实 PostgreSQL 集成测试会跳过。

### Docker Compose 完整测试

推荐在隔离的测试数据库上运行完整测试：

```sh
docker compose --profile test run --rm tests
```

测试范围包括：

- 正常批次接收和 ACK。
- 重复批次不重复计数。
- 同一批次 ID 的内容冲突。
- consent 缺失或为 false 时拒绝。
- 未声明字段和敏感字段拒绝。
- 请求体、行数、类型和数值限制。
- HMAC 匿名化。
- 管理员 Token 鉴权。
- 日、周、月汇总。
- DAU/WAU/MAU、增长、留存和使用强度分位数。
- schema v2 延迟、错误类别和回退汇总。
- 日期筛选及版本、Schema/Consent 覆盖。
- 公开接口与管理员接口隔离。
- 日志与数据库隐私约束。
- DB-IP 下载校验、原子替换、旧库保留和缺失回退。
- 可信代理链、伪造 Header 拒绝及客户端国别覆盖。

集成测试会清空测试数据库中的遥测表，`TEST_DATABASE_URL` 绝不能指向生产数据库。

## 生产部署检查清单

- 为数据库密码、HMAC 密钥和管理员 Token 分别生成高强度随机值。
- 使用正式、可信任的 TLS 证书。
- 只开放公开 HTTPS 端口；管理员入口仅允许受控网络访问。
- 不发布 PostgreSQL 和 Python 应用内部端口。
- 为外部代理和平台日志配置敏感信息脱敏。
- 验证每日备份并定期执行恢复演练。
- 监控磁盘容量、数据库连接、备份失败和 HTTP 5xx。
- 定期轮换管理员 Token；轮换 HMAC 密钥前应评估活跃安装统计连续性。
- 不在本服务中增加 Prompt、Response、账户、付费、模型中转或原始请求记录功能。
