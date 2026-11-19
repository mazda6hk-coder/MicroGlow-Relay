# MG-TELEMETRY-SERVER-002-C PostgreSQL 集成验收报告

## 1. 最终结论

**状态：PASS**

`BLOCKED-DOCKER-RUNTIME` 已解除。Docker Desktop Linux Engine 可用；全部迁移在本任务专用 PostgreSQL 16 实例中完成两轮执行，真实 PostgreSQL 集成测试与完整回归均通过。未连接生产数据库，未访问、启动、修改或迁移“东方仪式”数据库，未执行真实遥测上传，也未进入 `MG-RELAY-003-B`。

## 2. 隔离环境与资源

工作目录仅为：

```text
E:\微光智能科技中心成立\MicroGlow Relay\telemetry-server
```

本任务创建的隔离资源：

| 类型 | 名称/值 |
|---|---|
| Docker 项目标识 | `mg-telemetry-test-002c` |
| PostgreSQL 容器 | `mg-telemetry-test-002c-postgres` |
| PostgreSQL 镜像 | `postgres:16-alpine` |
| Docker 网络 | `mg-telemetry-test-002c-network` |
| Docker 数据卷 | `mg-telemetry-test-002c-pgdata` |
| 测试数据库 | `mg-telemetry-test-002c-db` |
| 旧数据升级临时库 | `mg-telemetry-test-002c-legacy` |
| 测试用户 | `mg-telemetry-test-002c-user` |
| 主机绑定 | `127.0.0.1:58490`（Docker 随机分配，仅本机） |

容器验收期间健康状态为 `healthy`。清理前核对到容器仅连接上述专用网络且仅挂载上述专用卷。

任务完成后精确执行：

```text
docker rm -f mg-telemetry-test-002c-postgres
docker volume rm mg-telemetry-test-002c-pgdata
docker network rm mg-telemetry-test-002c-network
```

三条命令退出码均为 0；随后按 `mg-telemetry-test-002c` 精确过滤容器、卷和网络，结果均为空。未使用 `docker compose down -v`，未删除任何其他项目资源。

## 3. 实际修改文件

- `tests/test_postgres_integration.py`
  - 增加合法 `NULL + COUNTRY-SOURCE-GAP` 的真实数据库写入验证；
  - 增加 `NULL + GEOIP` 拒绝验证；
  - 保留并验证无效国家代码、有效国家配缺口来源、长缺口标记写入 `country_code` 均被 PostgreSQL 拒绝；
  - 验证缺口记录的 installation_id 只以服务端 HMAC 结果出现。
- `MG_TELEMETRY_SERVER_002_POSTGRES_INTEGRATION_REPORT.md`
  - 本报告。

应用代码及迁移脚本无需为本轮验收修改；现有 `004_server_geoip.sql` 已通过真实数据库验证。

## 4. 迁移与旧数据兼容

在 `mg-telemetry-test-002c-db` 中依次执行：

```text
001_init.sql
002_quality_metrics.sql
003_batch_day_bounds.sql
004_server_geoip.sql
```

随后按相同顺序再次执行。两轮退出码均为 0；第二轮仅产生预期的 `already exists, skipping` / `does not exist, skipping` NOTICE，证明迁移可重复执行。

旧数据升级使用独立临时库 `mg-telemetry-test-002c-legacy`：先执行 001—003，写入相同聚合维度但客户端国别分别为 CN、US 的两行历史数据，再执行 004 两次。结果为：

```text
行数                 1
country_code         NULL
country_source       COUNTRY-SOURCE-GAP
active_minutes       12
api_call_count       20
success_count        16
error_count          4
input_tokens         2000
output_tokens        1000
total_tokens         3000
```

历史客户端国别被安全降级为缺口状态，发生维度合并时全部汇总值守恒。

## 5. 国别字段与约束

真实 PostgreSQL 元数据结果：

| 字段 | 数据库类型 | 可空 | 结果 |
|---|---|---:|---|
| `country_code` | `character(2)` | 是 | PASS |
| `country_source` | `character varying(32)` | 否 | PASS |

已验证以下合法组合：

- 有效 ISO 3166-1 alpha-2 代码 + `GEOIP`；
- `NULL + COUNTRY-SOURCE-GAP`。

已验证数据库拒绝：

- `ZZ + GEOIP`；
- `NULL + GEOIP`；
- `US + COUNTRY-SOURCE-GAP`；
- 将 `COUNTRY-SOURCE-GAP` 写入 `country_code`。

`usage_daily_country_source_check`、`usage_daily_country_iso_check`、`usage_daily_dimensions_key ... NULLS NOT DISTINCT` 和 `usage_daily_country_source_idx` 均存在并生效。数据库最终检查中非法组合数为 0，`ZZ` 伪装缺口数为 0。

## 6. GeoIP、代理与失败回退

本地文件 `data/geoip/dbip-country-lite.mmdb` 的 DB-IP 元数据：

- 数据库类型：`DBIP-Country-Lite`；
- 发布月份：`2026-09`；发布日期：`2026-09-01`；
- 下载地址：`https://download.db-ip.com/free/dbip-country-lite-2026-09.mmdb.gz`；
- 许可：Creative Commons Attribution 4.0 International；
- MMDB SHA-256：`d284ae2e7427fe33d83465e1506b2b21aae47eb8a9b099f8f4dac6a98c99f041`。

直接本地 MMDB 查询结果：

```text
8.8.8.8   -> US + GEOIP
192.0.2.1 -> NULL + COUNTRY-SOURCE-GAP
```

`tests/test_geoip.py` 验证了：数据库缺失/查询异常不崩溃；更新文件下载、格式/校验和检查和元数据记录；更新失败时保留旧库；可信代理链解析；不可信/伪造的 `X-Forwarded-For`、`X-Real-IP`、`Forwarded` 不被采信；客户端伪造 country_code 被服务端结果覆盖；缺口状态保持 NULL。测试使用模拟下载响应，不调用第三方实时 IP 定位 API。

部署配置使用明确的 `TRUSTED_PROXY_CIDRS`，默认值为 `172.30.0.0/24`；Dockerfile 和 Compose 均不存在 `--forwarded-allow-ips *`。Uvicorn 使用 `--no-access-log --no-proxy-headers`，由应用接入层按受信 CIDR 处理代理头。

## 7. 批次、Schema、Consent 与统计

真实 PostgreSQL 集成测试确认：

- 相同 `batch_id`、相同内容第二次提交返回 duplicate，不重复计数；
- 相同 `batch_id`、不同内容抛出批次冲突；
- schema v1/v2 均可按约束写入；
- schema v2 延迟桶、错误类别和 fallback_count 正确汇总；
- `country_source` 出现在国别聚合维度；
- API 调用数、Token、活跃安装、日/周/月统计保持不变量；
- ACK、Consent 缺失/错误/撤回、当前 Consent 版本校验由完整回归覆盖；
- installation_id 入库前继续执行服务端 HMAC，库中只出现 64 字符摘要。

## 8. 隐私边界与日志检查

数据库 `information_schema` 检索未发现以下字段：

```text
ip_address client_ip source_ip remote_addr installation_id
authorization api_key request_body response_body
```

对测试数据库 data-only dump 检索以下内容，均无匹配：测试用原始 installation_id、`8.8.8.8`、`192.0.2.1`、`203.0.113.42`、Authorization、Bearer 和 API Key 模式。`telemetry_batches.installation_hash` 的长度最小/最大均为 64，原始 installation_id 计数为 0。

应用/部署日志边界：

- Uvicorn access log 已关闭；
- Caddy `log default { output discard }`，访问日志不写持久存储；
- GeoIP 异常日志使用固定文本，不包含输入地址或可能携带地址的异常正文；
- PostgreSQL 容器日志未出现测试来源 IP、原始 installation_id、Authorization 或密钥。标准 PostgreSQL 启动日志含监听通配地址 `0.0.0.0`，该值不是客户端或遥测来源地址，也未进入数据库、API 响应或导出。
- API 响应和导出无完整 IP 由 `tests/test_geoip.py`、`tests/test_privacy.py` 和完整回归共同验证。

## 9. 命令与结果

| 验收项 | 实际命令（敏感测试密码不在报告展开） | 退出码 | 状态 | 对最终结论影响 |
|---|---|---:|---|---|
| Docker Engine | `docker version` | 0 | PASS | Linux Engine 可用，解除运行时阻塞 |
| Docker 资源预检 | `docker compose ls --all`、`docker ps -a`、`docker network ls`、`docker volume ls` | 0 | PASS | 仅识别现有资源；未操作其他项目 |
| Compose 配置 | `docker compose -p mg-telemetry-test-002c config --quiet` | 0 | PASS | 配置有效 |
| 隔离 PostgreSQL | 精确 `docker network create`、`docker volume create`、`docker run ... postgres:16-alpine` | 0 | PASS | 专用环境创建成功 |
| 健康检查 | `docker inspect --format '{{.State.Health.Status}}' mg-telemetry-test-002c-postgres` | 0 | PASS | 输出 `healthy` |
| 全部迁移两轮 | 将排序后的 `migrations/*.sql` 逐个送入隔离容器内 `psql -X -v ON_ERROR_STOP=1`，共两轮 | 0 | PASS | 004 与全量迁移均幂等 |
| 旧数据兼容 | 临时库执行 001—003、写入历史行、执行 004 两轮并查询汇总 | 0 | PASS | 降级与聚合守恒 |
| PostgreSQL 集成 | `.venv\Scripts\python.exe -m pytest -q tests\test_postgres_integration.py` | 0 | PASS | `1 passed` |
| GeoIP/代理/API 定向测试 | `.venv\Scripts\python.exe -m pytest -q tests\test_geoip.py tests\test_api.py` | 0 | PASS | `40 passed` |
| 本地 MMDB 查询 | `.venv\Scripts\python.exe -c "... GeoIPCountryResolver ..."` | 0 | PASS | US 与缺口回退符合预期 |
| 最终完整回归 | 设置隔离 `TEST_DATABASE_URL` 后执行 `.venv\Scripts\python.exe -m pytest -q` | 0 | PASS | `45 passed` |
| 数据库字段/内容检查 | 隔离库 `information_schema`、约束、索引、国别组合与 HMAC 长度查询 | 0 | PASS | 无禁止字段或非法数据 |
| 数据转储隐私检索 | 隔离库 `pg_dump --data-only` 后对原始 ID、IP、Authorization、密钥模式检索 | 0 | PASS | 无敏感值匹配 |
| 日志检索 | 对专用 PostgreSQL 容器日志检索来源 IP、原始 ID、Token/密钥模式 | 0 | PASS | 无客户端/遥测敏感值 |
| 精确清理 | `docker rm`、`docker volume rm`、`docker network rm`（仅专用名称） | 0 | PASS | 本任务资源已全部删除 |

补充透明记录：首次手工 MMDB 查询命令误用了不存在的类名 `GeoIPResolver`，退出码 1；这是验收命令拼写错误，不是服务故障。改用实际类 `GeoIPCountryResolver` 后退出码 0，结果如上。另一次尝试运行 `git status` 返回“不是 Git 仓库”（退出码 128/组合命令表现为 1）；本目录本身未配置 Git 元数据，不影响代码或集成验收。

## 10. 未完成事项与边界

- 未完成事项：无。
- 已知边界：本任务未验证生产反向代理或生产网络；仅验证仓库配置和自动化可信代理场景。
- 未连接生产数据库，未接触其他项目数据。
- 未启动 MicroGlow Relay 客户端，未修改 Router、Provider、协议或 EXE。
- 未执行任何真实生产遥测 HTTP 上传。
- 下一阶段 `MG-RELAY-003-B` 必须等待单独授权。

