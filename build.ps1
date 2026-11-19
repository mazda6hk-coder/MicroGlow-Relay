$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'build-app.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
