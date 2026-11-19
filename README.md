# MicroGlow Relay

MicroGlow Relay 是一个面向 Windows 的本地 AI Model Router。桌面端使用 PySide6，核心网关使用 Python 标准库 HTTP 服务，并通过适配器连接 OpenAI Responses、OpenAI Chat Completions 与 Anthropic Messages 兼容上游。本地接口同时接受 OpenAI Responses 与 Anthropic Messages 两种入站协议——Codex 与 Claude Code 可以同时接入，各自独立选择「指定模型配置」或「跟随 Relay 选择」。

## 从源码运行

```powershell
python -m venv work\venv
work\venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-app.txt
work\venv\Scripts\python.exe runapp.py
```

仅验证启动：

```powershell
work\venv\Scripts\python.exe runapp.py --smoke-test --data-dir work\smoke-data
```

## 测试与构建

```powershell
work\venv\Scripts\python.exe -m unittest discover -s tests -v
.\build-app.ps1
```

当前版本见 `src/storage.py` 的 `VERSION`（唯一版本源），桌面程序文件名随版本号为 `MicroGlow-Relay-<VERSION>.exe`。

## 安装与更新（发布准备）

安装包配方在 `installer/MicroGlowRelay.iss`。正式发布时，先构建当前版本 EXE，再安装 Inno Setup 6 并运行 `./build-installer.ps1`。安装包按用户安装到 `%LOCALAPPDATA%\Programs\MicroGlow Relay`，升级使用同一个 AppId 与程序路径；卸载不会删除用户数据。当前尚未构建或验证安装包。

安装版的数据固定在 `%LOCALAPPDATA%\MicroGlow Relay\data`，不再跟随 EXE 所在目录。源码运行仍使用项目内 `data`，`--data-dir` 仍可显式指定位置。若直接用新 EXE 替换同一便携目录中的旧 EXE，首次启动会将旧 `data` 复制到用户目录，保留旧目录且不覆盖已有新数据。若从任意便携目录改用安装包，安装器无法得知旧目录位置：退出 Relay，确认目标数据目录尚不存在后，将旧 EXE 同级的 `data` 复制到上述用户目录，再启动安装版；若目标目录已存在，不要合并或覆盖，应先核对两处数据。旧目录中的 Codex 接入路径可能仍指向旧模型目录，确认新数据与接入正常前不要删除旧目录。

设置页有手动“检查更新”：仅在点击时读取 `mazda6hk-coder/MicroGlow-Relay` 的最新正式 GitHub Release；发现新版后由用户决定是否打开下载页，不在程序内自动下载或安装。该公开发布仓库已建立，但尚未发布 Release，此时按钮提示“暂无可用的正式更新”，不误报为“已是最新版本”。仓库地址已硬编码在 `app/updates.py`。每款 MicroGlow 软件独立使用自己的发布仓库与更新接口。自动检查、后台下载及官网备用源属于后续工作，本轮未实现。上架前仍需发布与安装包版本一致的正式 Release，并对安装、升级、卸载保留数据及旧数据迁移做实机验收。

匿名遥测仅在用户明确同意后使用 `https://metrics.microglow.com.cn/v1/telemetry/batches` 上传 UTC 每日汇总；国家只由服务端推断，客户端不发送 `country_code`。

## 数据与隐私

- 本地服务默认仅监听 `127.0.0.1:4141`。
- API Key 与本地访问令牌使用 Windows DPAPI 加密。
- 请求正文不会写入磁盘；活动记录只保留状态、耗时和 Token 统计。
- 默认主题为 MicroGlow 官网色，设置页可切换 MicroGlow、黑色、白色、赛博朋克、金碧辉煌和 iOS 风格六套主题。

## 本阶段说明

“会话兼容”可对所选会话在 Codex 官方订阅与 Relay 之间切换模型接入配置，自动核对、备份和校验；不会读取或改写历史正文。切换到 Codex 时，以最近一条其它官方会话的模型标识为参考；找不到可靠参考时不写入。工作台有电源式总开关（控制 Codex 接入与本地服务启停），Claude Code 的开关在「客户端接入」页。

「客户端接入」页并列管理 Codex 与 Claude Code：Codex 接入改动 `~/.codex/config.toml`（TOML），Claude Code 接入改动 `~/.claude/settings.json`（写入 `env.ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN`，并把默认模型设为默认入口）。两者都可逆、有备份、退出时自动还原；Claude Code 的接入在重启会话后生效。Token 小计（A/B 两段）的计时从清零后第一笔调用起算，清零后无调用显示“尚未开始计时”。详见 `docs/reports/MG-RELAY-CLAUDE-ACCESS-001.md` 与 `MG-RELAY-TRIPTOKEN-002.md`。

上游在尚未向本地客户端发送响应时返回 429、502–504、520–524，Relay 在总预响应预算内最多重试一次；已经开始的流绝不重放。重试可能造成第二次上游计算或计费，详见 `docs/reports/MG_RELAY_524_RETRY_REPORT.md`。
