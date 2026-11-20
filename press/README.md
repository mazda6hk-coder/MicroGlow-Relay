# MicroGlow Relay — Press / 媒体资料包

用于评测与内容合作。所有描述以仓库 README、`CLAIMS.md` 与 Release 说明为准；请以软件实际行为独立验证。

## 产品

Windows 本地 AI 网关。监听 `127.0.0.1:4141`，让 Codex（OpenAI Responses）与 Claude Code（Anthropic Messages）通过同一个本地入口使用第三方模型。

- 仓库：https://github.com/mazda6hk-coder/MicroGlow-Relay
- Release：https://github.com/mazda6hk-coder/MicroGlow-Relay/releases/tag/v1.0
- 官网：https://www.microglow.com.cn/relay

## 安装

**Windows x64（当前正式包）**

- `MicroGlow-Relay-1.0-Setup.exe`，安装到 `C:\Program Files\MicroGlow Relay`，需要管理员权限。
- 未代码签名，Windows 可能提示 SmartScreen；请核对 Release 中的 SHA-256。
- 数据目录：`%LOCALAPPDATA%\MicroGlow Relay\data`。

**Linux（预览包，未宣称正式支持）**

- `microglow-relay_1.0_amd64.deb`，`sudo apt install ./microglow-relay_1.0_amd64.deb`。
- 构建于 Debian 12 / glibc 2.36，要求 glibc ≥ 2.34；尚未完成完整回归。
- 密钥使用系统密钥库（Secret Service）。

## 已交付（可独立验证）

- 双协议入站：`/v1/responses`、`/v1/messages`、`/v1/messages/count_tokens`、`/v1/models`、`/health`。
- 上游：Chat Completions / Responses / Anthropic Messages。
- 客户端接入：写入 `~/.codex/config.toml`、`~/.claude/settings.json`，带备份、漂移检测、退出恢复。
- 多渠道：权重、60 秒冷却、响应开始前切换；已开始的流不重放。
- Trip Token：A/B 两段、全局/Codex/Claude 口径、10 秒撤销、清零入账、总里程永不清零。
- 8 种界面语言；四季 × 昼夜 8 组皮肤。
- 隐私：正文不保存；推理文本缓存 7 天/2000 条；上游错误脱敏截断 800 字符；匿名统计默认关闭；更新检查默认开启、每自然日最多一次。

## 规划中（未交付）

- 跨模型会话续接。
- Linux 正式支持（需回归通过）。
- 安装包代码签名。
- Qt/PySide6 LGPL 打包方式的最终结论。

## 素材

| 用途 | 路径 |
|---|---|
| 社交预览 1280×640 | `../docs/images/social-preview-1280x640.png` |
| 循环 GIF（8.8 秒） | `../docs/images/trip-token-loop.gif` |
| 工作台 / 模型 / 设置截图 | `../docs/images/screenshots/` |
| 四季主题图 | `../assets/ui-final/` |
| 30 秒演示（无声、字幕已烧录） | `relay-30s.mp4` |
| 封面 | `cover-1280x720.png` |

## 联系

- 产品与评测支持：relay@microglow.com.cn
- 问题反馈：GitHub Issues（请使用模板，并删除密钥与对话内容）

## 披露

如为付费合作，请明确标注广告或赞助关系。产品方不干预评测结论。
