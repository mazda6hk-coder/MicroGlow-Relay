# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root 'work\venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }

& $python (Join-Path $root 'tools\build_app.py')
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
