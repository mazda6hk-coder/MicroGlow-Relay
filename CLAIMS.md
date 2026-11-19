# Claims ledger

Every factual statement in `README.md`, `README.zh-CN.md` and `CHANGELOG.md` is
listed here with its source in the code. If a statement could not be grounded,
it was removed or rewritten rather than kept.

- Repository: `F:\relay\release-repo` (clean snapshot of `relay2` working tree)
- Code state: commit `Initial public source snapshot` + release-prep edits
- Verification date: 2026-11-19
- Core test command and result (run from `tests/`):
  `python -m unittest test_router test_channels test_trip test_trip_ledger test_trip_scope test_trip_undo test_updates test_auto_updates test_claude_config test_native_restore test_telemetry_transport test_anthropic_shape test_claude_inbound test_request_model_trace test_server_sse_hardening`
  → **219 tests, OK (1 skipped)**.
- Full-suite note: the complete `discover -s tests` run terminates inside Qt in a
  headless session; UI tests need a desktop. This is the basis for the README
  wording.

Line numbers refer to this snapshot and will drift if files are edited; the
symbol names next to them are the stable anchors.

## README — positioning and architecture

| ID | Statement | Evidence | Status |
|---|---|---|---|
| R1 | Local gateway for Windows, listens on `127.0.0.1:4141` | `src/server.py:1606` (`LocalServer(("127.0.0.1", configured_port)`); `src/storage.py:286` (`"port": 4141`) | Verified |
| R2 | Codex uses OpenAI Responses, Claude Code uses Anthropic Messages | `src/server.py:1148` (protocol by path); `src/server.py:1172` (allowed inbound paths) | Verified |
| R3 | Translates to third-party providers through adapters | `src/adapters.py:976` (`prepare_request`) | Verified |
| R4 | No account; runs locally | `docs/PRIVACY-POLICY.md`; no account code path exists in `src/storage.py` | Verified (policy + absence) |

## README — "Why Relay"

| ID | Statement | Evidence | Status |
|---|---|---|---|
| R5 | One switch writes the Codex and Claude Code configuration | `app/bridge.py:524` (`connect_codex`); `app/bridge.py:588` (`connect_claude`); `src/codex_config.py:322` (`integrate`); `src/claude_config.py:288` (`integrate`) | Verified |
| R6 | Keeps a backup before writing | `src/codex_config.py:356`; `src/claude_config.py:313` | Verified |
| R7 | Detects changes made outside Relay | `src/codex_config.py:274` (`integration_status`); `app/bridge.py:122` (30 s status poll) | Verified |
| R8 | Restores the client on exit | `app/bridge.py:627` (`restore_on_exit`); `src/claude_config.py:336` (`restore`); `src/codex_config.py:388` (`restore_native`). Nuance: for Codex, exit restore returns the client to built-in OpenAI direct, not to an arbitrary previous provider. | Verified (wording constrained) |
| R9 | Retry before the response starts: 2 attempts, 3 for HTTP 500 | `src/server.py:160-162` (`MAX_UPSTREAM_ATTEMPTS=2`, `MAX_TRANSIENT_ATTEMPTS=3`); `src/server.py:220` (`_status_attempt_budget`) | Verified |
| R10 | Failed channel cools down for 60 seconds | `src/channels.py:22` (`COOLDOWN_SECONDS = 60.0`) | Verified |
| R11 | Failover to another channel, weighted at random | `src/channels.py:83` (`random.choices`); `src/server.py:1323` (`router.select(..., exclude=attempted_channels)`) | Verified |
| R12 | A started stream is never replayed | `src/server.py:470` (first SSE event prefetched so headers are not committed before retry); `src/server.py:415` (`_replay`) | Verified |
| R13 | Trip Token: two subtotals, scopes, naming, 10 s undo, ledger, total never resets | `src/trips.py:41` (scopes); `src/trips.py:217` (`started_at` on first call); `app/bridge.py:740` (`+10` undo window); `src/trip_ledger.py:88` (`reset_at`); `src/trip_ledger.py:13-15` (total is outside the ledger and never resets) | Verified |

## README — Quick start and endpoints

| ID | Statement | Evidence | Status |
|---|---|---|---|
| R14 | Installer installs to `C:\Program Files\MicroGlow Relay`, requires administrator | `installer/MicroGlowRelay.iss:20` (`DefaultDirName={autopf}\MicroGlow Relay`); `:23` (`PrivilegesRequired=admin`) | Verified |
| R15 | No preset models on first install | `src/storage.py:288` (`"profiles": []`) | Verified |
| R16 | Client is pointed at `http://127.0.0.1:4141` | `src/codex_config.py:174` (`base_url` with `/v1`); `src/claude_config.py:116` (`ANTHROPIC_BASE_URL`, no `/v1`) | Verified |
| R17 | `POST /v1/responses` inbound | `src/server.py:1172`; `src/server.py:1148` | Verified |
| R18 | `POST /v1/messages` inbound | `src/server.py:1155`; `src/server.py:1172` | Verified |
| R19 | `POST /v1/messages/count_tokens` is a local estimate | `src/server.py:1155`; `src/adapters.py:1383` (`estimate_tokens_for_messages`) | Verified |
| R20 | `GET /v1/models` returns configured models | `src/server.py:942` | Verified |
| R21 | `GET /health` is unauthenticated | `src/server.py:937`; auth check occurs after the health branch | Verified |
| R22 | Upstream protocols: Chat Completions, Responses, Anthropic Messages | `src/adapters.py:976` (dispatch by profile protocol); `src/storage.py:109` (endpoint suffixes) | Verified |
| R23 | Provider examples (DeepSeek, Zhipu, Moonshot, SiliconFlow, Ollama, OpenAI, Anthropic, custom relays) | `src/storage.py:35-42` (built-in provider defaults) | Verified |
| R24 | Streaming | `src/adapters.py` (`stream=True` in each upstream builder) | Verified |
| R25 | Tool calls, including parallel tool calls | `src/adapters.py` (multi-index tool-call aggregation); `src/codex_config.py:107` (`supports_parallel_tool_calls: True`) | Verified |
| R26 | Reasoning / thinking blocks | `src/adapters.py` (`reasoning_content`, `thinking_delta`, Responses reasoning items) | Verified |
| R27 | Image input | `src/adapters.py` (image_url / base64 image blocks) | Verified |
| R28 | Prompt-caching fields passed through per upstream | `src/adapters.py` (`cache_control` retained for Anthropic, stripped for Chat, content-part level kept for Responses) | Verified |
| R29 | `count_tokens` estimate = JSON characters / 4 | `src/adapters.py:1383` | Verified |

## README — Trip Token section

| ID | Statement | Evidence | Status |
|---|---|---|---|
| R30 | Switching scope changes the view, not the data | `src/trips.py` (`set_scope` keeps both protocol buckets and persists choice) | Verified |
| R31 | Timing starts at the first request after reset | `src/trips.py:217` (`started_at` set on first ledgered call) | Verified |
| R32 | Display indicates timing has not started | `app/final_views.py:282` (`elapsed is None` → `尚未开始`, translated per locale) | Verified |
| R33 | Reset clears only that subtotal and can be undone for 10 s | `app/bridge.py:740`; `src/trips.py` (`reset_trip` replaces only that segment's state) | Verified |
| R34 | Non-zero reset is written to the trip ledger with name, scope, times, tokens, requests, per-model breakdown | `app/bridge.py:732-735` (snapshot only when non-zero); `src/trip_ledger.py:73-94` (fields) | Verified |
| R35 | Total odometer never resets | `src/trip_ledger.py:13-15`; `app/bridge.py:712` (`grand_total` from the persistent log index) | Verified |
| R36 | Screenshot numbers are demo data | Asset provenance: images in `docs/images/` are the supplied marketing/diagram assets, produced with synthetic data (see `assets/theme-previews/README.md`). | Verified (provenance) |

## README — Privacy and security

| ID | Statement | Evidence | Status |
|---|---|---|---|
| R37 | API keys and local token encrypted with Windows DPAPI in Relay's settings | `src/storage.py:89` (`CryptProtectData`); `src/storage.py:287` (token protected) | Verified |
| R38 | Local token is written in plain text into the clients' config files | `src/codex_config.py:176` (`experimental_bearer_token`); `src/claude_config.py:116` (`ANTHROPIC_AUTH_TOKEN`) | Verified |
| R39 | Request/response bodies are not stored; usage log keeps metadata | `src/records.py:439` (row fields: timestamp, provider, model, status, elapsed, tokens, etc.) | Verified |
| R40 | Upstream error excerpt is redacted and truncated to 800 characters | `src/storage.py:498` (`redact`, 800); `src/server.py:1394` (only classified + redacted detail is recorded) | Verified |
| R41 | Reasoning text cached up to 7 days, max 2000 entries | `src/records.py:806` (cache file); `src/records.py:815-825` (7-day cutoff, 2000-entry cap) | Verified |
| R42 | Gateway binds to `127.0.0.1` only | `src/server.py:1606` | Verified |
| R43 | Bearer token required except `/health` | `src/server.py:754` (`hmac.compare_digest`); `src/server.py:937` (health bypass) | Verified |
| R44 | Requests with an `Origin` header are rejected | `src/server.py:750` | Verified |
| R45 | Anonymous statistics opt-in, off by default | `src/telemetry/consent.py:84` (`is_granted` false unless granted); `installer/MicroGlowRelay.iss:114-116` (no default selection) | Verified |
| R46 | One aggregate batch per day, uploaded on normal exit | `src/server.py:1659` (`shutdown` docstring: one upload pass per normal exit); `src/telemetry/endpoint.py:12` | Verified |
| R47 | Batch contains no prompt, response, endpoint URL, file or key | `src/telemetry/store.py` (aggregate fields only); `src/telemetry/transport.py:5` | Verified |
| R48 | Client sends no IP field and no country code | `src/telemetry/endpoint.py:22`; `src/telemetry/transport.py:69` (rejects rows containing `country_code`) | Verified |
| R49 | Connection exposes the source address; server infers country; raw IP is not stored as a statistics field | `telemetry-server/app/main.py:116` (source used for country lookup); `telemetry-server/app/geoip.py` (transient lookup); `telemetry-server/app/repository.py:64,178` (only `country_code` / `country_source` stored); `telemetry-server/app/repository.py:42` (installation id HMAC-hashed) | Verified |
| R50 | Update checks on by default | `app/bridge.py:446` (`auto_update` default `True`) | Verified |
| R51 | Check shortly after start, then at most once per local day | `app/update_controller.py:23` (`24 * 60 * 60 * 1000`); `:27` (`singleShot(5000)`); `:38` (same-day skip) | Verified |
| R52 | GitHub release API with fallback to the project website | `app/updates.py:57` (`api.github.com`); `app/updates.py:132` (fallback manifest). Note: the manifest host is `www.microglow.com.cn/updates/relay/`. | Verified |
| R53 | Update requests carry no installation ID, config, credentials, content or statistics | `app/updates.py:58` (fixed headers only); `app/updates.py:96` (manifest request) | Verified |
| R54 | New version downloaded and checksum-verified automatically; installation requires user action | `app/updates.py:159` (SHA-256 verify); `app/update_controller.py:3` (module promise: never starts an installer until an explicit click); `:79` (`install`) | Verified |
| R55 | Installer is not code-signed | `MicroGlow-Relay-1.0.spec:87` (`codesign_identity=None`); no `SignTool` directive in `installer/MicroGlowRelay.iss` | Verified |

## README — Platform, build, FAQ

| ID | Statement | Evidence | Status |
|---|---|---|---|
| R56 | Windows x64, 64-bit installer | `installer/MicroGlowRelay.iss:24` (`ArchitecturesAllowed=x64compatible`) | Verified |
| R57 | Qt 6.11 requires Windows 10 or later | `requirements-app.txt` (`PySide6==6.11.2`); Qt 6 official support matrix | External fact — **待确认**（不依赖本仓库代码） |
| R58 | 8 interface languages, list | `app/i18n.py:12-20` (`LANGUAGE_CHOICES`) | Verified |
| R59 | Installer itself is English/Simplified Chinese only | `installer/MicroGlowRelay.iss:35-39` | Verified |
| R60 | 8 skins, 4 seasons × day/night | `app/theme.py:325` (`PALETTES`), `app/theme.py:148-174` | Verified |
| R61 | Default is spring, day | `app/bridge.py:227` (`"spring-day"`) | Verified |
| R62 | Linux not supported in this release | `src/storage.py:77` (raises on non-Windows); `app/launcher.py` (single-instance returns None on non-Windows) | Verified |
| R63 | Python 3.11 or later | `src/codex_config.py:10` (`import tomllib`, 3.11+); `app/updates.py:159` (`hashlib.file_digest`, 3.11+) | Verified |
| R64 | Build commands, `--smoke-test`, `--data-dir` | `app/launcher.py:29-34` (argument parsing); `README.md` commands | Verified |
| R65 | PyInstaller onefile executable named after `VERSION` | `MicroGlow-Relay-1.0.spec:69-91` (single `EXE`, no `COLLECT`); `tools/build_app.py:23` (`EXE_NAME = f"MicroGlow-Relay-{VERSION}"`); `src/storage.py:22` (`VERSION = "1.0"`) | Verified |
| R66 | Installer build requires Inno Setup 6 | `build-installer.ps1` (locates `ISCC.exe`); `installer/MicroGlowRelay.iss` | Verified |
| R67 | Core tests run headless; UI tests need a desktop session | Test run 2026-11-19: 219 core tests OK; full discover terminates in Qt under `QT_QPA_PLATFORM=offscreen` | Verified (run) |
| R68 | Data directory `%LOCALAPPDATA%\MicroGlow Relay\data` (installed build) | `app/data_paths.py:26` | Verified |
| R69 | Base URL for Claude Code entry has no `/v1` | `src/claude_config.py:10` (comment) and `:116` (`http://127.0.0.1:{port}`) | Verified |

## CHANGELOG

| ID | Statement | Evidence | Status |
|---|---|---|---|
| C1 | First public source release | This repository, initial commit | Fact of this deliverable |
| C2 | Feature list in `## Added` | Same evidence as R1–R36, R58–R61 | Verified |
| C3 | Windows only; no Linux claim | R62 | Verified |
| C4 | Installer unsigned | R55 | Verified |
| C5 | Onefile packaging; LGPL replacement question unconfirmed | `MicroGlow-Relay-1.0.spec:69`; analysis in `THIRD_PARTY_NOTICES.md` | Verified |
| C6 | Reasoning cache 7 days / 2000 entries | R41 | Verified |
| C7 | Error excerpt redacted / 800 chars | R40 | Verified |
| C8 | Some builder-side tests may stop `build-app.ps1` | Removed from the final text: replaced by R67's verified statement about UI tests and headless sessions. | Rewritten |
| C9 | Cross-model session continuation is planned, not implemented | No implementation found in `src/`; listed under Roadmap only | Verified (absence) |

## Statements removed or rewritten (and why)

| Original wording | Problem | Action |
|---|---|---|
| “请求与回复正文永不落盘” (old `README.md`, old UI text) | False as written: reasoning text is cached (`src/records.py:806`) and redacted upstream error excerpts are stored (`src/storage.py:498`). | Rewritten in README as “request and response bodies are not stored”, followed by explicit cache and error-excerpt disclosure. The diagram asset was cropped to remove that badge; the final diagram (G) will use the corrected wording. |
| “活动记录只保留状态、耗时和 Token 统计” (old README) | Understates stored fields (provider, model, status, channel index, cache/reasoning token counts, error excerpt). | Replaced with the full metadata list. |
| “按用户安装到 `%LOCALAPPDATA%\Programs\...`” (old README) | Contradicts the installer (`{autopf}` + admin). | Corrected to `C:\Program Files\MicroGlow Relay`. |
| “自动检查更新…本轮未实现” (old README) | Contradicts `app/update_controller.py` and `app/updates.py`; the privacy policy already describes auto-update. | Replaced with the implemented behavior and explicit default-on disclosure. |
| “六套主题（官网色/黑/白/赛博朋克/金碧辉煌/iOS）” (old README) | Contradicts the current 4 × 2 palette model (`app/theme.py:325`). | Replaced with 8 skins. |
| “两者都可逆、有备份、退出时自动还原” (old README; implies exact restore for Codex) | Codex exit restore calls `restore_native()`, which resets to built-in OpenAI direct rather than replaying an arbitrary prior provider. | Wording limited to “restores the client”; the exact behavior is noted here and in `docs/USER-GUIDE.md`. |
| “the 1.0 build used Python 3.13” | True operationally but has no evidence inside the public repository. | Removed; only the code-verifiable “3.11+” requirement remains. |
| “an internal Linux copy exists and has been built” | Cannot be evidenced inside the public repository. | Removed; the only remaining statement is “Linux is not supported in this release.” |
| “`test_ui3.py` has stale assertions that stop the build” | Not reproducible as stated in this environment; the observed failure is headless Qt termination. | Replaced with the verified headless/desktop statement. |

## Legal and non-code statements

These are declarations, not code claims, and live in their own files:

- License grant and scope: `LICENSE`, `NOTICE`, `ARTWORK-LICENSE.md`, `LICENSES/CC-BY-NC-ND-4.0.txt`.
- Trademarks and non-affiliation: `TRADEMARKS.md`.
- Third-party components and LGPL analysis: `THIRD_PARTY_NOTICES.md`, `docs/licenses/`.
- Contact addresses and operator identity: `docs/USER-AGREEMENT.md` (support/privacy/security), matching the project website.

## Maintenance rule

Any new factual sentence in README, CHANGELOG or release notes must get an ID
here before merge. If the code changes and the evidence line disappears, the
sentence is treated as unverified until re-grounded.
