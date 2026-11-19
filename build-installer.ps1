# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot 'work\venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$sourceDirectory = Join-Path $projectRoot 'src'
$version = (& $python -c "import sys; sys.path.insert(0, sys.argv[1]); from storage import VERSION; print(VERSION)" $sourceDirectory).Trim()
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^\d+\.\d+$') { throw '无法读取有效版本号' }
$sourceExe = Join-Path $projectRoot "MicroGlow-Relay-$version.exe"
if (-not (Test-Path -LiteralPath $sourceExe)) { throw "请先构建 $sourceExe" }
$compiler = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $compiler) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe')
    )
    $compiler = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
}
if (-not $compiler) { throw '未找到 Inno Setup 6 的 ISCC.exe；安装后再运行本脚本' }
& $compiler "/DAppVersion=$version" "/DSourceExe=$sourceExe" (Join-Path $projectRoot 'installer\MicroGlowRelay.iss')
if ($LASTEXITCODE -ne 0) { throw "安装包构建失败，退出码 $LASTEXITCODE" }
