# 服务端调用渠道接收与部署验收

日期：2026-10-07（Asia/Shanghai）。统计时区仍为 UTC。

任务：MG-RELAY-TELEMETRY-SERVER-CHANNEL-001；后续部署依据新增 MG-RELAY-TELEMETRY-CONNECT-001 授权。

## 当前结果

源码及真实隔离 PostgreSQL 定向测试：PASS CANDIDATE，36 passed。
现有遥测环境的 005 迁移、API/admin 重建、内部 Caddy HTTPS 合成批次 ACK 和数据库验收：PASS。
公网客户端合成批次：已实际核验数据库和管理员汇总，精确清理通过。服务端结论 PASS CANDIDATE，STOP。本报告不代表真实用户上传验收，客户端自身退出流程最终验收由客户端会话负责。

## 修改与备份

- app/schemas.py：增加严格的可选 call_channel 枚举。
- app/repository.py：渠道入库维度、旧哈希兼容、新渠道汇总键。
- migrations/005_call_channel.sql：字段、约束及包含渠道的唯一维度索引。
- tests/test_call_channel.py：合约、ACK、Consent、哈希、幂等、迁移、汇总定向测试。
- docs/channel_deployment_probe.py：手动授权合成验证脚本，不在正常服务中运行、不定时执行。
- 本报告。

源码覆盖前备份：backups/channel-20261007/schemas.py、repository.py。
现有库部署前完整 pg_dump -Fc：backups/channel-20261007/before-channel.dump；pg_restore --list 检查成功。
工作区原有未提交修改保留；未修改客户端、Router、Provider、EXE 或其他项目。

## 接收契约

POST /v1/telemetry/batches，保持原有 JSON 批次结构、Schema 1/2、精确 Consent 版本校验和 ACK。
aggregated_rows 每行可选 call_channel，仅 official / relay / unknown；缺失按 unknown 存储。
null、空串、大小写变体及其他枚举拒绝；所有未知字段仍 extra=forbid。
不新增 URL、域名、IP、密钥、Prompt、Response 或逐请求记录字段。
schema_version=2 与 consent_version=v2.2026-09 没有提升。consent=true 与精确版本仍必需。

当前客户端源码已披露调用渠道，并增加本地上传重新确认标记；该标记不进入 wire 合约。
技术上这是可选汇总维度的向后兼容扩展，不是把旧同意自动扩展为新的披露授权。
仅服务端 consent=true 无法证明客户端已展示新说明；客户端需落实重新确认后才解除上传门槛。
客户端会话声明本地 upload_disclosure=channel-exit-upload-2026-10，旧同意仅能本地统计。
服务端不擅自决定提高 Consent 或 Schema 版本，也不代替客户端做同意证明。

## 聚合与幂等

usage_daily.call_channel VARCHAR(16) NOT NULL DEFAULT 'unknown'，数据库 CHECK 限制三个枚举。
历史数据仅新增 unknown，不按 Provider、模型名或国家来源猜测渠道。
唯一索引增加 call_channel，同日同版本同模型的各渠道独立累计。
现有 by_relay_version_model 等返回键继续合并渠道，避免破坏消费者。
新增 by_relay_version_model_channel，包含版本、模型、model_type、渠道、调用/成功/错误/输入/输出/总 Token、活跃分钟及去重安装数，继承日期过滤。
每行 active_minutes 是该行实际贡献，客户端不得给每渠道复制安装时长。服务端不做跨渠道乘法或联接扩增，也不能从已重复上传的时长推断真实贡献。
安装数量仍 HMAC 后 distinct，不把渠道数当安装数。

原来的 payload_hash 使用 Schema 展开后的规范 JSON。新增字段缺失时，仅在哈希输入中排除 call_channel，保留其他既有默认值，得到原算法相同摘要。
显式渠道值（含显式 unknown）参与哈希；缺失与显式 unknown 不是相同批次内容。
相同 batch_id/相同内容 ACK duplicate=true；内容变更返回 409。密封旧批次不得补字段后复用 ID。

## 迁移与回退

005 在事务内执行；新增字段使用 IF NOT EXISTS、约束通过 pg_constraint 检查，重建唯一索引。
隔离测试验证 001–005 顺序执行、005 重复执行、存在三渠道数据时再运行全部迁移，总量不变。
生产本次只执行 005，没有重放历史迁移或改写历史国家。
升级必须先备份，再迁移，再重建 API/admin，避免旧服务在新索引上继续写入。
回退不能直接删除列或恢复旧唯一索引：新渠道行会发生维度冲突。先停止本项目写入，保留升级后的库备份，再在独立库恢复 before-channel.dump 校验；若已接收新业务批次，必须另行授权做增量对账再切回。不得无条件恢复旧快照丢弃新数据。

## 实际命令与结果

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| docker version --format '{{.Server.Version}}' | 0 | Engine 29.6.1 可用 |
| docker-compose config --quiet | 0 | PASS |
| docker run -d --name mg-telemetry-test-channel-20261007 --label mg.task=MG-RELAY-TELEMETRY-SERVER-CHANNEL-001 -e POSTGRES_DB=channel_test -e POSTGRES_USER=channel_test -e POSTGRES_PASSWORD=synthetic-test-only -p 127.0.0.1::5432 postgres:16-alpine | 0 | 创建独立临时库，主机动态端口 51474 |
| .venv/Scripts/python.exe -m pytest -q tests/test_call_channel.py tests/test_api.py（未配测试库） | 1 | 首轮 1 failed / 33 passed / 1 skipped；新增夹具未启动 lifespan，随后修复 |
| TEST_DATABASE_URL 指向隔离库；.venv/Scripts/python.exe -m pytest -q tests/test_call_channel.py tests/test_api.py tests/test_postgres_integration.py | 0 | 首次 36 passed；补充约束/日期/迁移保留检查后再次 36 passed，2.33s |
| docker-compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/mg-channel-20261007.dump' | 0 | PASS |
| docker-compose cp postgres:/tmp/mg-channel-20261007.dump ./backups/channel-20261007/before-channel.dump | 0 | PASS |
| docker-compose exec -T postgres sh -c 'pg_restore --list /tmp/mg-channel-20261007.dump >/dev/null' | 0 | PASS |
| Get-Content migrations/005_call_channel.sql -Raw 通入 docker-compose exec -T postgres psql -U telemetry -d microglow_telemetry --set ON_ERROR_STOP=1 | 0 | 005 COMMIT |
| docker-compose up -d --no-deps --build telemetry-api telemetry-admin | 0 | 两个遥测服务部署成功；未重建其他服务 |
| probe 脚本通入 docker-compose exec -T -e CHANNEL_PROBE_URL=https://metrics.microglow.com.cn/v1/telemetry/batches telemetry-api python - | 1 | 容器公网 DNS 解析失败；没有入库，合成清理 PASS |
| probe 脚本通入 docker-compose exec -T telemetry-api python -（最初 gateway TLS 主机名） | 1 | SNI 不匹配；无入库 |
| 同一 probe（最初 localhost Host） | 1 | 实际 PUBLIC_HOST 为 metrics.microglow.com.cn，返回非 JSON；无入库 |
| 修正验证脚本 Host/SNI 为已核实 PUBLIC_HOST；Get-Content docs/channel_deployment_probe.py -Raw 通入 docker-compose exec -T telemetry-api python - | 0 | ACK200/重试200/冲突409/入库和admin PASS/精确清理 PASS |
| curl.exe --noproxy '*' --max-time 10 -s -o NUL -w '%{http_code}' https://metrics.microglow.com.cn/health | 0 | Windows 公网入口 200；此命令仅健康验证 |
| 数据库 information_schema 隐私字段查询 | 0 | 禁止列计数 0 |
| docker-compose logs --no-color --since 20m telemetry-api telemetry-admin，仅内存正则检查 | 0 | 敏感字段未发现；IPv4形状命中仅静态 Uvicorn 监听地址，不是上传来源地址 |
| docker stop mg-telemetry-test-channel-20261007；docker rm -v mg-telemetry-test-channel-20261007 | 0/0 | 仅清理本次独立容器及其匿名卷 |
| PowerShell Python here-string 通入 docker-compose exec -T telemetry-api python -，按客户端提供独有 batch_id 查询/验证/清理 | 0 | 公网客户端批次入库、管理员汇总、精确清理全部 PASS |

内部部署合成证明：3 个渠道、30 次调用、4,500 Token、20 分钟、单一合成安装；重复上传不增加总量；管理员新汇总键同样得到 30 次；finally 精确清理独有 batch_id 和 HMAC 安装标识。

## 隐私与隔离

独立测试容器：mg-telemetry-test-channel-20261007，独立库/用户 channel_test，Docker 新建匿名卷，已随该容器精确清理；未创建或清理共享网络。
现有遥测库只增加字段/索引，历史渠道 unknown；生产合成删除限定独有 hash、版本、provider/model 和独有 batch_id，无宽泛删除。
数据库没有新增 IP/URL/原始 installation_id 列；日志未输出身份、请求体、密钥或 Authorization。Uvicorn access log、proxy headers 配置保持关闭，Caddy discard 配置未变。
源码测试使用合成标识和计数，不代表真实用户上传；未触碰东方仪式资源，未全局清理 Docker。
日志检查窗口为本次部署约 20–25 分钟，不声称证明所有历史日志。静态监听地址不是用户来源 IP；未在报告抄录任何来源地址。

## 交接条件与 STOP

客户端解除 call_channel 拦截需：用户重新明确同意包含渠道的上传披露，保留旧密封批次原文、失败批次和 ACK 后完成语义；客户端执行其自己的最终退出流程验收。
服务端接收契约、内部部署合成验收、公网客户端合成入库核验均已就绪。当前 PASS CANDIDATE / STOP，不自动追加界面装修或其他开发。

### 公网客户端最终核验记录

客户端会话从 Windows 宿主通过固定公网 HTTPS 地址，使用当前 HttpTelemetryUploadClient 发出合成批次；该侧报告 HTTP 200 / ACK true、本地 acknowledged、sealed payload unchanged，原样重试 duplicate=true / accepted_rows=0。本会话独立核查数据库和管理员接口，没有把客户端口述 ACK 当成入库证明。

合成 batch_id：batch_8fd8e90325a040fea3a29f96c75ae2c2（仅批次标识，不是原始安装标识）。模型 synthetic-connect-20261007、版本 3.4、provider custom。

数据库实际：三行，official / relay / unknown 各一行；3 次调用、输入 21、输出 6、总 Token 27、活跃分钟 0。Schema 2、row_count 3。管理员 by_relay_version_model_channel 得到相同三渠道和总量。

清理前按 HMAC 安装标识确认 telemetry_batches 只关联本批次，usage_daily 只包含指定合成模型/provider/版本的三行；任何关联业务记录将拒绝清理。事务删除精确命中 DELETE 3 / DELETE 1；再次查询本合成 hash 和 batch_id 均无残留。未输出原始 installation_id、HMAC hash、来源 IP、请求正文或密钥。

输出：PUBLIC_CLIENT_DB=PASS、PUBLIC_CLIENT_ADMIN=PASS、PUBLIC_CLIENT_CLEANUP=PASS，命令退出码 0。容器公网 DNS 失败不影响 Windows 客户端公网合成上传成功，本任务未修改 DNS 或代理。
