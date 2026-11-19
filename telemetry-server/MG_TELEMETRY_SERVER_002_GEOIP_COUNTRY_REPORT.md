# MG-TELEMETRY-SERVER-002：本地 GeoIP 国别推断改造报告

## 1. 执行结论

- 服务端实现与本地自动化回归：**PASS**。
- 官方 DB-IP Lite 下载、格式校验、校验信息记录及真实 MMDB 查询：**PASS**。
- Docker Compose 静态配置解析：**PASS**。
- 隔离 PostgreSQL 真实迁移/集成测试：**BLOCKED-DOCKER-RUNTIME**。当前机器 Docker Desktop Linux Engine 未运行，且没有本机 PostgreSQL；未启动、重建、停止或清理任何容器，也未接触“东方仪式”或其他项目的数据。
- 真实遥测 HTTP 上传：**NOT-RUN（按任务要求）**。测试中的 POST 均为进程内 ASGI 自动化请求，不是对已部署服务的真实上传。
- `MG-RELAY-003-B`：**未执行**。

本任务只修改 `E:\微光智能科技中心成立\MicroGlow Relay\telemetry-server`。未修改 MicroGlow Relay、Router、Provider、客户端协议、客户端 EXE 或旧目录 `E:\API路由器`。

## 2. 实际修改文件清单

### 应用代码

- `app/config.py`：增加 MMDB 路径和可信代理 CIDR 配置及校验。
- `app/network.py`：新增可信 socket/代理来源解析器。
- `app/geoip.py`：新增可热重载的本地 MMDB 国家查询器和缺失回退。
- `app/geoip_update.py`：新增官方月度数据库下载、校验、元数据和原子替换。
- `app/main.py`：在遥测接入层完成来源解析与服务端权威国别覆盖。
- `app/security.py`：限流与 GeoIP 共用可信来源解析，不再直接信任任意 XFF。
- `app/repository.py`：只接受服务端国别结果，写入并汇总 `country_source`。
- `app/admin.html`：将 NULL 国别显示为“国别来源缺失”。
- `requirements.txt`：固定 `maxminddb==2.8.2`。

### 数据库与部署

- `migrations/004_server_geoip.sql`：增加可空 `country_code`、非空 `country_source`、来源一致性与 ISO 枚举约束、NULLS NOT DISTINCT 唯一索引；旧客户端国别改为缺失来源并在必要时合并重复维度，保留计数总量。
- `Dockerfile`：关闭 Uvicorn proxy-header 自动信任。
- `docker-compose.yml`：移除 `--forwarded-allow-ips *`，固定后端子网，配置可信代理 CIDR、只读 MMDB 挂载和独立更新服务。
- `.env.example`：增加 GeoIP、代理网段和更新参数。
- `.gitignore`、`.dockerignore`：阻止 MMDB/运行元数据进入 Git 和应用镜像。
- `data/geoip/.gitkeep`：服务端数据目录占位。
- `data/geoip/dbip-country-lite.mmdb`：已下载的服务端运行数据（Git/Docker build context 排除）。
- `data/geoip/dbip-country-lite.metadata.json`：实际来源、版本和校验信息（Git/Docker build context 排除）。

### 文档与测试

- `README.md`：补充权威国别、信任链、更新/回退、部署和许可说明。
- `DBIP_ATTRIBUTION.md`：记录 DB-IP 来源和 CC BY 4.0 归属。
- `tests/test_geoip.py`：新增下载、校验、回退、代理伪造、覆盖、隐私和字段约束测试。
- `tests/test_api.py`：更新国别缺失的预期。
- `tests/test_postgres_integration.py`：增加服务端国别、数据库约束和无 IP 列检查；需 PostgreSQL 环境运行。
- 本报告。

## 3. GeoIP 数据库

### 格式与加载

- 数据库：DB-IP Lite IP-to-Country。
- 格式：MMDB，`database_type=DBIP-Country-Lite`，`ip_version=6`（同时包含 IPv4/IPv6 网络）。
- 服务端路径：`data/geoip/dbip-country-lite.mmdb`；容器内只读路径 `/geoip/dbip-country-lite.mmdb`。
- 应用通过 `GEOIP_DATABASE_PATH` 加载；文件 mtime/size 改变后自动重新打开。
- 使用 `maxminddb.MODE_FILE`，兼容 Windows 非 ASCII 项目路径和 Linux 容器挂载。
- 数据库未复制到客户端、Relay、EXE 或应用镜像。

### 实际版本、来源与校验

- 官方产品页：`https://db-ip.com/db/download/ip-to-country-lite`
- 实际下载：`https://download.db-ip.com/free/dbip-country-lite-2026-09.mmdb.gz`
- 发布月份：`2026-09`
- HTTP Last-Modified / 发布日期：`Tue, 01 Sep 2026 06:27:01 GMT` / `2026-09-01`
- HTTP ETag：`"6a967035-3ed1a0"`
- 压缩文件 SHA-256：`cb0578ce59f569f2c933bb40feb820804a334855a60739011b0a89cab1d6e4ed`
- MMDB SHA-256：`d284ae2e7427fe33d83465e1506b2b21aae47eb8a9b099f8f4dac6a98c99f041`
- MMDB build epoch：`1788226365`
- 许可：Creative Commons Attribution 4.0 International（CC BY 4.0）。
- 归属：IP geolocation data by DB-IP.com。

DB-IP 官方下载端点没有提供可用的 `.sha256` sidecar，因此实现采用 HTTPS、ETag/Last-Modified 记录、本地压缩包 SHA-256、解压后 MMDB SHA-256、gzip 完整性和 MMDB 类型/元数据校验；运营方还可用 `DBIP_EXPECTED_SHA256` 固定当月可信压缩包哈希。

### 更新方式

独立 `geoip-updater` 每日检查一次当月版本；已存在同月文件且元数据哈希与本地 MMDB 一致时跳过下载，因此实现“按月版本、每日轻量检查”。新文件先写同目录临时文件，完成大小限制、gzip、可选固定哈希、MMDB 类型和双 SHA-256 校验后，以 `os.replace` 原子替换数据库，再替换元数据。任何下载或校验失败均清理临时文件并保留旧库；没有旧库时 API 继续启动并使用缺失来源回退。

## 4. 来源 IP 信任链

1. Uvicorn 使用 `--no-proxy-headers`，不再使用 `--forwarded-allow-ips *`。
2. 应用首先读取 socket 对端地址。
3. 对端不属于 `TRUSTED_PROXY_CIDRS`：只使用 socket 对端，忽略 XFF、X-Real-IP、Forwarded 和自定义 Header。
4. 对端属于明确可信代理 CIDR：只解析 `X-Forwarded-For`，从离应用最近的一端向外剥离可信代理，选择最近的非可信来源；非法、缺失或超长链回退为缺失。
5. Compose 默认将后端网段和可信代理网段同时固定为 `172.30.0.0/24`，只允许该私有后端网络中的 Caddy 提供来源链。生产网络变化时必须同步配置精确 CIDR，禁止 `*`。
6. Caddy 访问日志继续丢弃；Uvicorn access log 继续关闭。

## 5. 国家推断与回退

```text
可信 socket/代理来源（仅内存）
  -> 本地 MMDB 查询
  -> ISO alpha-2 + GEOIP，或 NULL + COUNTRY-SOURCE-GAP
  -> 写入匿名 usage_daily
  -> 不保留原始地址
```

- 服务端 GeoIP 结果是权威值；客户端 `country_code` 只为既有 schema 兼容而保留，入库时被忽略。
- 成功：`country_code CHAR(2)` 写有效大写 ISO 代码，`country_source='GEOIP'`。
- 失败：`country_code=NULL`，`country_source='COUNTRY-SOURCE-GAP'`。
- 不使用 `ZZ`、默认国家或将缺失标记塞入 `country_code`。
- 来源缺失、代理不可信/非法、数据库缺失/损坏/无匹配或查询异常均不拒绝合法批次。
- 相同 `batch_id` 仍严格幂等；首次成功写入的国别结果不会因后续重试而重复计数或改写。

## 6. 隐私边界验证

### 数据库

- 迁移和模型中不存在 `ip_address`、`client_ip`、`source_ip`、`remote_addr` 等完整 IP 列。
- 只写 `country_code` 与 `country_source`；installation ID 仍先执行服务端 HMAC。
- 数据库 CHECK 同时约束来源枚举、来源/国家一致性和完整 ISO alpha-2 清单。
- 不存原始遥测 JSON。

### 日志、响应、后台与导出

- GeoIP 查询异常只记录固定通用消息，不拼接地址或异常文本。
- 应用日志不记录来源地址、请求正文、Authorization、Token、密钥或 installation ID。
- Uvicorn access log 关闭，Caddy access log 丢弃。
- ACK、管理摘要、图形后台和导出结构中没有完整 IP 字段；国别缺失只显示缺失状态。

### 客户端边界

- 未修改客户端；未增加 IP 读取、保存、上传、GeoIP 依赖或国家库。
- 未修改 Router、Provider、协议、业务逻辑或 EXE。

## 7. 测试与命令结果

| 命令/检查 | 退出码 | 结果 |
|---|---:|---|
| 安装 `requirements.txt` / `requirements-test.txt` | 0 | PASS，安装 `maxminddb 2.8.2` |
| `pytest -q tests/test_geoip.py tests/test_api.py` | 0 | PASS，39 passed |
| 修复非 ASCII Windows 路径后 `pytest -q tests/test_geoip.py` | 0 | PASS，先 8 passed，最终扩充后 9 passed |
| `python -m app.geoip_update --once` | 0 | PASS，下载并验证官方 2026-09 MMDB |
| 本地 MMDB 查询 `8.8.8.8` | 0 | PASS，得到 `US / GEOIP`；仅为本地数据库查询，不是第三方实时定位 API |
| `docker compose config --quiet`（使用测试占位密钥） | 0 | PASS |
| `python -m compileall -q app tests` | 0 | PASS |
| `python -m pytest -q`（唯一最终全量回归） | 0 | PASS，44 passed / 1 skipped / 0 failed |
| Docker/PostgreSQL 集成环境探测 | 1 | BLOCKED，Docker Desktop Linux Engine pipe 不存在 |

最终跳过项是 `tests/test_postgres_integration.py`，原因是未设置可用的隔离 `TEST_DATABASE_URL`。该测试已覆盖：迁移顺序与幂等、批次幂等、服务端国别入库、摘要、无完整 IP 列、非法 ISO 和来源不一致的数据库拒绝。应在 Docker/PostgreSQL 可用且明确指向隔离测试库时执行；绝不能指向生产库。

自动化覆盖的本任务规则包括：

- 直接连接与可信代理来源解析；
- 不可信/伪造 XFF 不被采信；
- 来源缺失回退；
- MMDB 缺失和查询异常不崩溃；
- 官方下载、双哈希、元数据和格式校验；
- 校验失败保留旧库并清除临时文件；
- 客户端伪造国别被服务端覆盖；
- 完整 IP 字段被 schema 拒绝；
- 国家只能是有效 ISO+GEOIP 或 NULL+GAP；
- 数据库结构、日志、响应、后台/导出无完整 IP；
- 原有 schema、ACK、幂等、consent、分析后台和隐私测试保持通过。

## 8. 已知限制与未完成事项

1. **BLOCKED-DOCKER-RUNTIME**：未在本机执行真实 PostgreSQL 迁移集成测试或 Compose 启动验收。解除条件是 Docker Desktop Linux Engine 或明确的隔离 PostgreSQL 测试库可用。不得使用现有生产/其他项目数据库代替。
2. 仓库只能给出 Compose 内 Caddy 的默认可信网段。若生产环境在 Caddy 前另有 CDN/负载均衡器，必须由部署方确认拓扑并只加入精确 CIDR；本实现不会猜测或自动信任。
3. 官方站点没有校验 sidecar；已采用并记录本报告第 3 节的多层校验，可由运营方配置外部获得的固定 SHA-256 进一步收紧。
4. GeoIP 是 IP 归属推断，不保证反映用户物理位置；VPN、企业出口和代理会影响国家结果。
5. 未执行真实 HTTP 遥测上传，符合停止条件。后续在本任务的隔离 PostgreSQL 集成验收通过前，不进入 `MG-RELAY-003-B`。

报告生成后停止，不扩展其他功能。
