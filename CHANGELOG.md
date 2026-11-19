# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0] - 2026-11-19

First public source release. The Windows build was previously distributed as a
binary only; this release publishes the source, documentation and license files.

### Added

- Local gateway on `127.0.0.1:4141` (configurable) serving both OpenAI Responses
  and Anthropic Messages inbound protocols, with adapters for OpenAI Chat
  Completions, OpenAI Responses and Anthropic Messages upstreams.
- Endpoints: `POST /v1/responses`, `POST /v1/messages`,
  `POST /v1/messages/count_tokens` (local estimate), `GET /v1/models`,
  `GET /health`.
- Streaming, tool calls (including parallel tool calls), reasoning/thinking
  blocks, image input and prompt-caching passthrough where the upstream supports
  them.
- Per-channel retry before the response starts, weighted random selection across
  channels, failure cooldown, and automatic failover to another channel when the
  response has not started.
- One-click integration and restore for `~/.codex/config.toml` and
  `~/.claude/settings.json`, with backups and drift detection.
- API key and local access token encryption with Windows DPAPI.
- Trip Token: two independent subtotals (A/B) scoped to All / Codex / Claude,
  with naming, a 10-second undo after reset, and automatic ledger entries.
- Eight interface languages: 简体中文, 繁體中文, English, Deutsch, 日本語, ไทย,
  Español, 한국어.
- Four seasonal skins with day and night palettes (eight combinations).
- Opt-in anonymous daily aggregate statistics; automatic update check.

### Known limitations

- Windows only in this release. A Linux copy exists in the internal tree but has
  not been regression-tested or released; this repository does not claim Linux
  support.
- The installer (`MicroGlow-Relay-1.0-Setup.exe`) is not code-signed. Windows
  SmartScreen may warn. Verify the published SHA-256.
- The Windows build is packaged with PyInstaller **onefile**. The LGPL-3.0
  obligations of the bundled Qt/PySide6 libraries are described in
  `THIRD_PARTY_NOTICES.md`; the replacement/relinking question is not yet
  confirmed with counsel.
- Reasoning text is cached locally for up to 7 days (max 2000 entries) to support
  multi-turn continuation. Request and response bodies themselves are not stored.
- Upstream errors are stored as a redacted, truncated excerpt (max 800
  characters) in the local usage log.
- Some builder-side tests (`test_ui3.py`) contain stale assertions and may stop
  the full `build-app.ps1` pipeline. The unit tests relevant to the gateway pass.
- Cross-model session continuation is planned, not implemented.

[1.0]: https://github.com/mazda6hk-coder/MicroGlow-Relay/releases/tag/v1.0
