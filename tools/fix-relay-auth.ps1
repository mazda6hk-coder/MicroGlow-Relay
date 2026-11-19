# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
param(
    [string]$Python = "python",
    [string]$DataDir = ""
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $Python)) { $Python = "python" }

$args = @((Join-Path $PSScriptRoot "fix_codex_auth.py"))
if ($DataDir -ne "") { $args += @("--data-dir", $DataDir) }

& $Python @args
exit $LASTEXITCODE
