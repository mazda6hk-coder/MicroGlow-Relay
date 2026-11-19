param(
    [string]$Python = "C:\Users\刘军\AppData\Local\Programs\Python\Python313\python.exe",
    [string]$DataDir = ""
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $Python)) { $Python = "python" }

$args = @((Join-Path $PSScriptRoot "fix_codex_auth.py"))
if ($DataDir -ne "") { $args += @("--data-dir", $DataDir) }

& $Python @args
exit $LASTEXITCODE
