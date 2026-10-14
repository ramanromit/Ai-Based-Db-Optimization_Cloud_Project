#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Phase 2 Session Destroy — tears down Aurora + RDS Proxy to stop billing.
    Run this at the END of every AWS session. Aurora/Proxy bill continuously.

.PARAMETER Password
    Aurora master password (required by Terraform even for destroy).

.EXAMPLE
    .\infra\scripts\phase2_destroy.ps1 -Password "MyStr0ngPass"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Password
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TF_DIR = "$PSScriptRoot\..\terraform"
$ROOT    = "$PSScriptRoot\..\.."

Write-Host "`n═══════════════════════════════════════════════════════" -ForegroundColor Red
Write-Host " CAQI Phase 2 — Session Destroy (STOP BILLING)" -ForegroundColor Red
Write-Host "═══════════════════════════════════════════════════════`n" -ForegroundColor Red

Write-Host "This will DESTROY the following resources:" -ForegroundColor Yellow
Write-Host "  • aws_db_proxy_target.rds_proxy_target_aurora"
Write-Host "  • aws_db_proxy_default_target_group.rds_proxy_targets"
Write-Host "  • aws_db_proxy.caqi_rds_proxy"
Write-Host "  • aws_secretsmanager_secret_version.db_credentials_val"
Write-Host "  • aws_secretsmanager_secret.db_credentials"
Write-Host "  • aws_rds_cluster_instance.reader_instance"
Write-Host "  • aws_rds_cluster_instance.writer_instance"
Write-Host "  • aws_rds_cluster.aurora_cluster"
Write-Host ""
Write-Host "Phase 1 resources (VPC, SGs, KMS, S3, DynamoDB, SQS, SNS) are PRESERVED." -ForegroundColor Green
Write-Host ""

$confirm = Read-Host "Type 'yes' to proceed with destroy"
if ($confirm -ne "yes") {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
}

Push-Location $TF_DIR

Write-Host "`n[1/3] Destroying RDS Proxy resources..." -ForegroundColor Yellow
terraform destroy `
    -var "enable_expensive_core=true" `
    -var "db_master_password=$Password" `
    -target=aws_db_proxy_target.rds_proxy_target_aurora `
    -target=aws_db_proxy_default_target_group.rds_proxy_targets `
    -target=aws_db_proxy.caqi_rds_proxy `
    -target=aws_secretsmanager_secret_version.db_credentials_val `
    -target=aws_secretsmanager_secret.db_credentials `
    -auto-approve

Write-Host "`n[2/3] Destroying Aurora cluster (takes 3-5 min)..." -ForegroundColor Yellow
terraform destroy `
    -var "enable_expensive_core=true" `
    -var "db_master_password=$Password" `
    -target=aws_rds_cluster_instance.reader_instance `
    -target=aws_rds_cluster_instance.writer_instance `
    -target=aws_rds_cluster.aurora_cluster `
    -auto-approve

Pop-Location

# Reset .env to local mode
$envFile = "$ROOT\.env"
if (Test-Path $envFile) {
    (Get-Content $envFile) |
        ForEach-Object {
            if ($_ -match '^USE_AWS=') { "USE_AWS=false" }
            elseif ($_ -match '^RDS_PROXY_ENDPOINT=')      { "RDS_PROXY_ENDPOINT=" }
            elseif ($_ -match '^AURORA_READER_ENDPOINT=')  { "AURORA_READER_ENDPOINT=" }
            else { $_ }
        } | Set-Content $envFile
    Write-Host "`n[3/3] ✅ .env reset to local mode (USE_AWS=false)." -ForegroundColor Green
}

Write-Host "`n✅ Phase 2 resources destroyed. Billing has stopped." -ForegroundColor Green
Write-Host "   Phase 1 resources are still running (they are free/negligible cost)." -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════`n" -ForegroundColor Red
