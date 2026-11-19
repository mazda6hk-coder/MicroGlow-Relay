# MicroGlow Relay

**一个路由入口，更多模型选择。**

MicroGlow Relay 是一个面向 Windows 的本地 AI 模型路由器，帮助你将 AI 编程工具连接到多个模型服务商。在一个地方完成 API 配置、路由和模型切换。

![MicroGlow Relay](https://www.microglow.com.cn/assets/screenshots/relay-main-en.png)

## 核心功能

### 会话修复
针对意外中断或配置切换导致的会话不可用，尝试重建连接。适用于部分兼容场景，不保证恢复所有数据。

### 多模型路由
连接不同的模型服务商（OpenAI、Anthropic、Google 等），在一个界面中配置、测试和切换。减少重复操作，让选择更灵活。

### 统一管理
在一个位置查看请求状态、管理 API 密钥、监控使用情况。操作直观，减少在不同工具间切换。

### 桌面体验
原生 Windows 桌面应用，支持多语言界面（8+ 种语言）和主题切换。直接运行，无需浏览器或额外依赖。

## 安装

### 下载
- **当前版本**: 3.4
- **Windows 要求**: Windows 10 或更高版本
- **下载地址**: 正式发布后请访问 [www.microglow.com.cn](https://www.microglow.com.cn/)

### 安装步骤
1. 从官网下载 Windows 安装包
2. 运行安装程序
3. 按照安装向导完成安装

安装程序将应用放置在 `%LOCALAPPDATA%\Programs\MicroGlow Relay`，数据目录为 `%LOCALAPPDATA%\MicroGlow Relay\data`。卸载不会删除用户数据。

## 快速上手

1. **下载并安装**
   从官网下载 Windows 安装包，运行安装程序完成部署。

2. **配置 API 服务**
   在设置中添加你的模型服务商 API 密钥，配置连接参数。

3. **连接工具并使用**
   将 AI 编程工具指向 Relay 提供的本地端点（`http://127.0.0.1:4141`），开始使用不同模型。

## 支持的服务商

MicroGlow Relay 通过兼容协议支持以下模型服务商：
- OpenAI（Chat Completions 与 Responses API）
- Anthropic（Messages API）
- Google（Gemini API）
- 其他 OpenAI 兼容服务商

## 数据与隐私

- 本地服务默认仅监听 `127.0.0.1:4141`
- API 密钥与访问令牌使用 Windows DPAPI 加密
- 请求正文不会写入磁盘
- 活动记录只保留状态、耗时和 Token 统计
- 遥测为选择性功能，仅在用户明确同意后向 `https://metrics.microglow.com.cn/v1/telemetry/batches` 上传 UTC 每日汇总

## 开发

### 从源码运行

```powershell
python -m venv work\venv
work\venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-app.txt
work\venv\Scripts\python.exe runapp.py
```

### 冒烟测试

```powershell
work\venv\Scripts\python.exe runapp.py --smoke-test --data-dir work\smoke-data
```

### 构建

```powershell
work\venv\Scripts\python.exe -m unittest discover -s tests -v
.\build-app.ps1
```

## 文档

- **官方网站**: [www.microglow.com.cn/relay](https://www.microglow.com.cn/relay)
- **English Documentation**: See [README-EN.md](README-EN.md)

## 问题反馈

如需报告问题、提出功能建议或反馈意见，请访问：
- GitHub Issues：（仓库公开后提供）
- 官方网站：[www.microglow.com.cn](https://www.microglow.com.cn/)

## 许可证

许可证信息将在正式发布后提供。

---

© 2026 MicroGlow. 保留所有权利。
