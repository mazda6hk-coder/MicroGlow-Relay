# MicroGlow Relay

**One Router. More Freedom.**

MicroGlow Relay is a local AI model router for Windows that lets you connect your AI coding tools to multiple model providers. Switch, route, and manage your API connections in one place.

![MicroGlow Relay](https://www.microglow.com.cn/assets/screenshots/relay-main-en.png)

## Features

### Session Repair
Attempt to rebuild connections for sessions disrupted by interruptions or configuration changes. Works in compatible scenarios, no guarantee of full data recovery.

### Multi-Model Routing
Connect to different model providers (OpenAI, Anthropic, Google, and more), configure, test, and switch in one interface. Reduce repetitive operations, increase flexibility.

### Unified Management
View request status, manage API keys, monitor usage in one place. Intuitive operations, less tool switching.

### Desktop Experience
Native Windows desktop app with multi-language UI (8+ languages supported) and theme switching. Runs directly, no browser or extra dependencies needed.

## Installation

### Download
- **Current Version**: 3.4
- **Windows Requirements**: Windows 10 or later
- **Download**: Visit [www.microglow.com.cn](https://www.microglow.com.cn/) after official release

### Install
1. Download the Windows installer from the official website
2. Run the setup program
3. Follow the installation wizard

The installer will place the app in `%LOCALAPPDATA%\Programs\MicroGlow Relay` and data in `%LOCALAPPDATA%\MicroGlow Relay\data`. Uninstallation preserves user data.

## Quick Start

1. **Download and Install**
   Download the Windows installer from the official website and run the setup program.

2. **Configure API Services**
   Add your model provider API keys in settings and configure connection parameters.

3. **Connect Tools and Start**
   Point your AI coding tools to Relay's local endpoint (`http://127.0.0.1:4141`) and start using different models.

## Supported Providers

MicroGlow Relay supports the following model providers through compatible protocols:
- OpenAI (Chat Completions & Responses API)
- Anthropic (Messages API)
- Google (Gemini API)
- Other OpenAI-compatible providers

## Data & Privacy

- Local service listens on `127.0.0.1:4141` by default
- API keys and access tokens are encrypted using Windows DPAPI
- Request bodies are not written to disk
- Activity logs retain only status, timing, and token statistics
- Telemetry is opt-in and uploads daily UTC aggregates to `https://metrics.microglow.com.cn/v1/telemetry/batches` only after explicit user consent

## Development

### Run from Source

```powershell
python -m venv work\venv
work\venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-app.txt
work\venv\Scripts\python.exe runapp.py
```

### Smoke Test

```powershell
work\venv\Scripts\python.exe runapp.py --smoke-test --data-dir work\smoke-data
```

### Build

```powershell
work\venv\Scripts\python.exe -m unittest discover -s tests -v
.\build-app.ps1
```

## Documentation

- **Official Website**: [www.microglow.com.cn/relay](https://www.microglow.com.cn/relay)
- **中文文档**: See [README.zh-CN.md](README.zh-CN.md)

## Issues & Feedback

For bug reports, feature requests, or general feedback, please visit:
- GitHub Issues: (will be available after repository publication)
- Official Website: [www.microglow.com.cn](https://www.microglow.com.cn/)

## License

License information will be available after official release.

---

© 2026 MicroGlow. All rights reserved.
