# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.4] - 2026-11-24

Slug stabilisation and sub-agent input adaptation.

### Fixed

- **Configuration slugs are now frozen at first assignment.** Previously the slug
  was recomputed on every catalog export (model name plus an id suffix on
  collisions), so adding or removing a duplicate-named profile, or splitting a
  parent model into channels, could rename an existing profile and make recorded
  sessions fail with "model not found". Slugs are now persisted in the settings
  file and never recomputed. Older settings files without a slug are backfilled
  once on load using the previous algorithm, so an upgrade does not break
  existing sessions.
- **`agent_message` input type** used by Codex multi-agent dispatch is now folded
  into a plain user message for Chat Completions and Anthropic upstreams instead
  of being rejected by the input-type allowlist. The two text segments
  (`input_text` and `encrypted_content`) are preserved and annotated with sender
  and recipient session ids. Native passthrough keeps the original payload
  untouched.
- Installer: `installer/TelemetryConsent.iss` used `;` comments in a Pascal
  include, which made Inno Setup fail with `'BEGIN' expected`; switched to `//`.

### Tests

- Added `test_slug_stability` (10) and `test_agent_message` (12); router,
  native-passthrough and friendly-name suites unchanged and green.

## [1.3] - 2026-11-23

Native model passthrough. When no configured profile matches a native Codex
model name, Relay forwards the request to Codex's own official backend
(`chatgpt.com/backend-api/codex/responses`), authenticating with the ChatGPT
login already present in `~/.codex/auth.json`.

### Added

- Native passthrough: a session can use a native model as the orchestrator and
  third-party models for worker turns, without quitting Relay or editing config.
- Reasoning chains stay intact for native turns: `encrypted_content` round-trips
  because the same account produces and consumes it.
- Native catalog snapshot (`src/native_catalog.json.gz`, 11 entries) captured from
  `codex debug models --bundled`, so instruction layer and reasoning levels match
  what Codex itself ships. Refresh with `tools/capture_native_catalog.py`.

### Changed

- Native entries with no usable path are no longer exported to the model catalog.
- A ChatGPT backend `200` without `Content-Type` is now treated as a healthy
  stream instead of being misread as `502 not_sse`.
- Native 401/403 messages now say the Codex login expired or the plan does not
  include the model, instead of pointing at API-key configuration.

### Security

- `~/.codex/auth.json` is read on every native request and never written back.
- The native token is applied only in the passthrough branch. Requests to
  third-party providers never receive it; forwarded client headers come from a
  fixed allowlist that excludes `Authorization`.

## [1.2] - 2026-11-22

### Changed

- Model catalog is grouped by provider: entries from one provider are contiguous,
  sorted by model name, and provider blocks follow first-appearance order.
- Unified naming: `Provider｜Model` (previously `Provider · Model`); native models
  use `Native｜`.
- Removed the global "follow Relay" catalog entry. Models are chosen per session;
  the exported default model falls back to the currently selected profile, then
  the first available one.
- Native models merged into the same list, re-checked against
  `codex debug models --bundled` (11 entries, including GPT-6.2 / GPT-6.1 / GPT-6
  families).
- Restored the feedback entry (mailto) in the About card.

## [1.1] - 2026-11-21

### Fixed

- Tool-shape compatibility in three layers before reaching upstream: known
  rewrites (`custom`/freeform to function, collapse top-level `oneOf`/`anyOf`,
  fill missing `parameters`), a fallback that drops unknown private carriers, and
  one reactive retry when an upstream 400/422 points at tool fields.
- Window masking on borderless frames.

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

[1.3]: https://github.com/mazda6hk-coder/MicroGlow-Relay/releases/tag/v1.3
[1.2]: https://github.com/mazda6hk-coder/MicroGlow-Relay/releases/tag/v1.2
[1.1]: https://github.com/mazda6hk-coder/MicroGlow-Relay/releases/tag/v1.1
[1.4]: https://github.com/mazda6hk-coder/MicroGlow-Relay/releases/tag/v1.4
