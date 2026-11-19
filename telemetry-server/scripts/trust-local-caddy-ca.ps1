# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$projectDirectory = Split-Path -Parent $PSScriptRoot
$temporaryCertificate = Join-Path ([System.IO.Path]::GetTempPath()) "microglow-caddy-local-root.crt"

Push-Location $projectDirectory
try {
    $gatewayContainer = docker compose ps -q gateway
    if (-not $gatewayContainer) {
        throw "gateway 容器未运行，请先执行 docker compose up -d。"
    }

    docker cp "${gatewayContainer}:/data/caddy/pki/authorities/local/root.crt" $temporaryCertificate | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "无法从 gateway 容器导出本地 CA 证书。"
    }

    $certificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($temporaryCertificate)
    $storePath = "Cert:\CurrentUser\Root\$($certificate.Thumbprint)"

    if ($Remove) {
        if (Test-Path -LiteralPath $storePath) {
            Remove-Item -LiteralPath $storePath
            Write-Host "已从当前 Windows 用户的受信任根证书中移除 MicroGlow 本地 CA。"
        } else {
            Write-Host "当前用户证书库中没有对应的 MicroGlow 本地 CA。"
        }
    } else {
        Import-Certificate -FilePath $temporaryCertificate -CertStoreLocation "Cert:\CurrentUser\Root" | Out-Null
        Write-Host "已信任 MicroGlow 本地 CA。请完全关闭并重新打开浏览器。"
        Write-Host "证书指纹：$($certificate.Thumbprint)"
    }
} finally {
    if (Test-Path -LiteralPath $temporaryCertificate) {
        Remove-Item -LiteralPath $temporaryCertificate -Force
    }
    Pop-Location
}

