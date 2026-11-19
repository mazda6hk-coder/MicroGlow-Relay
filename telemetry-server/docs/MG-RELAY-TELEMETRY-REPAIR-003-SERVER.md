# 遥测服务端 operating_system 可缺省修复（REPAIR-003-SERVER）

任务：MG-RELAY-TELEMETRY-REPAIR-003-SERVER
日期：2026-10-07（Asia/Shanghai），统计时区仍为 UTC
范围：仅 `telemetry-server` 源码、兼容处理、现有遥测 Compose 项目部署与端到端核验
结论：**PASS CANDIDATE，STOP**

## 一、线上状态核验（改动前）

未发送任何批次，直接读取运行中容器代码确认真实线上契约：

- 镜像 `telemetry-server-telemetry-api` 的 `/service/app/schemas.py`：`operating_system: Literal["windows", "macos", "linux", "other"]`，**必填、无默认值**。
- 同一镜像已含 `call_channel` 渠道字段，说明线上是“渠道已上线、OS 仍必填”的状态。
- 运行容器启动时间 `2026-10-07T10:16:29Z`，与任务前提一致。

补充事实：工作区中已存在一处**未提交**的 `operating_system` 可选化改动与 `tests/test_remove_os.py`。本任务据此核对正确性、补齐验证并部署，未回退或重写他人改动。

## 二、改动内容

1. `app/schemas.py`

   `operating_system: Literal["windows", "macos", "linux", "other"] | None = None`

   新客户端可整行省略该字段；旧批次仍可携带原枚举值。

2. `app/repository.py`

   - `payload_hash()`：当某行未显式设置 `operating_system`（或 `call_channel`）时，从哈希输入中剔除该键，保证**旧密封批次哈希不变**、且“显式取值”与“缺失”得到不同摘要。
   - `collapsed_rows()`：缺失 OS 时写入空字符串作为既有 NOT NULL 列/索引的占位槽（`row.operating_system or ""`），**不推断、不猜测**系统。

3. 数据库

   **无需迁移**。`usage_daily.operating_system` 定义为 `varchar(16) NOT NULL`、参与主键/唯一索引，且无枚举 CHECK；空字符串满足约束。改动仅涉及应用层，历史行不受影响。

保持不变：Schema 1/2、`consent_version` 精确匹配、`consent=true`、严格未知字段拒绝（`extra=forbid`）、`call_channel` 三值枚举、ACK 语义、GeoIP 国家来源与隐私边界。

## 三、文件与备份

改动文件：

- `telemetry-server/app/schemas.py`
- `telemetry-server/app/repository.py`
- `telemetry-server/tests/test_remove_os.py`（定向测试）
- `telemetry-server/docs/repair003_deployment_probe.py`（人工授权的合成验证脚本，不在服务内运行、不定时执行）
- 本报告

备份（覆盖/迁移前）：

- 源码：`backups/repair003-20261007/schemas.py`、`backups/repair003-20261007/repository.py`
- 数据库：`backups/repair003-20261007/before-repair003.dump`（`pg_dump -Fc`，`pg_restore --list` 通过）

## 四、定向测试

隔离 PostgreSQL：容器 `mg-telemetry-test-repair003-20261007`（独立库/用户、临时匿名卷，验收后精确清理）。

```
TEST_DATABASE_URL=postgresql://<isolated>/repair003_test
.venv/Scripts/python.exe -m pytest -q ^
  tests/test_remove_os.py tests/test_call_channel.py ^
  tests/test_api.py tests/test_postgres_integration.py
```

结果：**37 passed in 2.20s**（退出码 0）。覆盖：无 OS 新批次、带 OS 旧批次、重复 ACK、同 ID 异内容冲突、`consent=false` 拒收、未知字段拒绝、旧哈希保持、渠道与 OS 维度、迁移重入。

## 五、部署

```
docker-compose up -d --no-deps --build telemetry-api telemetry-admin
```

退出码 0，仅重建本遥测 Compose 的两个服务，未动 `postgres`、`gateway`、`geoip-updater`、`backup`，未触碰官网、8081、Resonance 或其他项目资源。

部署后校验运行中容器：`/service/app/schemas.py:52` 为
`operating_system: Literal["windows", "macos", "linux", "other"] | None = None`。

## 六、端到端合成验收

经本机遥测入口（Caddy → telemetry-api），使用**唯一合成安装标识**与合成批次 ID：

| 检查 | 结果 |
| --- | --- |
| 无 OS 新批次 | `200`，ACK true，accepted_rows=1 |
| 带 OS 旧批次 | `200`，ACK true |
| 两者原样重发 | `200`，duplicate=true，accepted_rows=0 |
| 同 batch_id 增加 OS（内容变化） | `409` |
| `consent=false` | `422` |
| 数据库 | 2 行，`operating_system ∈ {"", "windows"}`，调用 10、Token 80 |
| 管理员汇总 | 同版本调用 10、Token 80，与数据库一致 |
| 清理 | 该合成身份仅 2 个批次，精确 `DELETE 2` 行 / `DELETE 2` 批次 |

输出：`NEW_NO_OS_ACK=200`、`LEGACY_OS_ACK=200`、`REPEAT_ACK=200 duplicate=true`、`CONFLICT_SAME_ID_DIFF_CONTENT=409`、`CONSENT_FALSE=422`、`DB=2_rows`、`ADMIN=200`、`SYNTHETIC_CLEANUP=PASS`，退出码 0。

失败记录（已修复，未产生数据）：首轮探针未放宽内部 Caddy 自签证书校验，抛出 `CERTIFICATE_VERIFY_FAILED`，随后清理断言 `DELETE 0`；因请求未到达服务端，**无任何入库**。仅对网络内合成校验放宽验证后重跑通过，公网入口验证不使用该放宽。

## 七、既有数据完整性与隐私

- 事前备份库与线上库聚合一致：`telemetry_batches=25`、`SUM(api_call_count)=5985`、`SUM(total_tokens)=1702949802`，证明既有数据未被清空或改写。
- 合成残留检查：`provider='synthetic' OR model LIKE 'synthetic%'` 为 0；`batch_id LIKE 'synthetic%'` 为 0。
- 日志检查（本次部署窗口）：无安装标识明文、无 `Authorization`、无 `api_key`、无合成标识；IPv4 仅 `0.0.0.0` 静态监听地址，无上传来源地址。
- 未记录请求正文、来源 IP、安装标识明文或密钥；未上传任何真实用户数据。

## 八、资源清理

仅清理本任务创建的隔离 PostgreSQL 容器 `mg-telemetry-test-repair003-20261007` 及其匿名卷；未执行 `docker-compose down -v`，未删除共享网络或其他项目资源。现遥测 Compose 六个服务均处于运行状态。

## 九、停止条件与交接

服务端契约、部署、入库、管理员汇总、隐私与清理证据齐备，判定 **PASS CANDIDATE**，任务 **STOP**。
客户端/安装器由客户端会话负责，本会话未修改客户端文件，也未向其发送消息；客户端侧最终验收由其自行只读核对。
