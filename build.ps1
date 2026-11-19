# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'build-app.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
