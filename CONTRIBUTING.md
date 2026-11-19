# Contributing

Thanks for your interest. This is a small project; please keep changes focused.

## Before you start

- Open an issue for anything larger than a bug fix or a small documentation
  change, so the approach can be agreed first.
- Read `docs/USER-GUIDE.md`, `docs/PRIVACY-POLICY.md` and
  `THIRD_PARTY_NOTICES.md`.

## Development

Requirements: Windows, Python 3.11+ (the release build was produced with 3.13).

```powershell
python -m venv work\venv
work\venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-app.txt
work\venv\Scripts\python.exe -m unittest discover -s tests -v
work\venv\Scripts\python.exe runapp.py
```

Note: UI test modules create Qt widgets and need a desktop session. The core
gateway, routing, trip and update tests run headless.

## Pull requests

- One logical change per PR, with a short description of the behavior change.
- Add or update tests when you change gateway, adapter, routing or trip logic.
- Do not include real API keys, tokens, prompt contents, conversation logs, user
  data, or machine-specific paths. Use synthetic values such as
  `sk-test-placeholder`.
- Do not add code that phones home, executes hidden commands, or detects forks.
- By submitting a PR you certify the [Developer Certificate of Origin
  (DCO) 1.1](https://developercertificate.org/). Sign off your commits with
  `git commit -s`.
- Contributions to the source code are accepted under the Apache License 2.0.
  Do not contribute artwork unless you own the rights; artwork is licensed
  separately (see `ARTWORK-LICENSE.md`).

## Reporting security issues

See `SECURITY.md`. Do not open a public issue.
