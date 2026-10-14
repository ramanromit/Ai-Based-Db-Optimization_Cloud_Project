#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Phase 2 Session Start — provisions Aurora + RDS Proxy + Read Replica.
    Run this at the START of every AWS session where Phase 2 is needed.

.PARAMETER Password
    Aurora master password. Passed as -var to Terraform (never stored in code).
    Requirements: min 8 chars, no @, /, or spaces.

.PARAMETER SkipAurora
    Skip Aurora cluster apply (if already provisioned this session).

.EXAMPLE
    .\infra\scripts\phase2_start.ps1 -Password "MyStr0ngPass"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Password,

    [switch]$SkipAurora
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TF_DIR = "$PSScriptRoot\..\terraform"
$ROOT    = "$PSScriptRoot\..\.."

Write-Host "`n═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " CAQI Phase 2 — Session Start Script" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# ── 1. Verify AWS credentials are set ──────────────────────────────
Write-Host "[1/6] Verifying AWS credentials..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "  ✅ Account : $($identity.Account)" -ForegroundColor Green
    Write-Host "  ✅ Role    : $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ AWS credentials not set or expired!" -ForegroundColor Red
    Write-Host "  → Open Learner Lab → AWS Details → AWS CLI → copy & paste the 3 env vars" -ForegroundColor Red
    exit 1
}

# ── 2. Verify Phase 1 resources are present ────────────────────────
Write-Host "`n[2/6] Checking Phase 1 baseline (terraform plan)..." -ForegroundColor Yellow
Push-Location $TF_DIR
terraform plan -var "enable_expensive_core=false" -var "db_master_password=$Password" `
    -detailed-exitcode -out /dev/null 2>&1 | Out-Null
if ($LASTEXITCODE -eq 1) {
    Write-Host "  ❌ Terraform plan failed — Phase 1 resources may be missing." -ForegroundColor Red
    Write-Host "  → Run: terraform apply (in infra/terraform/) to restore Phase 1 first." -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "  ✅ Phase 1 resources present." -ForegroundColor Green
Pop-Location

# ── 3. Apply Aurora cluster + writer instance ─────────────────────
if (-not $SkipAurora) {
    Write-Host "`n[3/6] Provisioning Aurora cluster (takes 5-10 min)..." -ForegroundColor Yellow
    Push-Location $TF_DIR
    terraform apply `
        -var "enable_expensive_core=true" `
        -var "db_master_password=$Password" `
        -target=aws_rds_cluster.aurora_cluster `
        -target=aws_rds_cluster_instance.writer_instance `
        -target=aws_rds_cluster_instance.reader_instance `
        -auto-approve
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ Aurora provisioning failed. Check above errors." -ForegroundColor Red
        Pop-Location; exit 1
    }
    Pop-Location
    Write-Host "  ✅ Aurora cluster + writer + reader instance provisioned." -ForegroundColor Green
} else {
    Write-Host "`n[3/6] SkipAurora flag set — skipping Aurora apply." -ForegroundColor Yellow
}

# ── 4. Apply Secrets Manager + RDS Proxy ─────────────────────────
Write-Host "`n[4/6] Provisioning Secrets Manager secret + RDS Proxy (takes 5-10 min)..." -ForegroundColor Yellow
Push-Location $TF_DIR
terraform apply `
    -var "enable_expensive_core=true" `
    -var "db_master_password=$Password" `
    -target=aws_secretsmanager_secret.db_credentials `
    -target=aws_secretsmanager_secret_version.db_credentials_val `
    -target=aws_db_proxy.caqi_rds_proxy `
    -target=aws_db_proxy_default_target_group.rds_proxy_targets `
    -target=aws_db_proxy_target.rds_proxy_target_aurora `
    -auto-approve
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ RDS Proxy provisioning failed. Check above errors." -ForegroundColor Red
    Pop-Location; exit 1
}
Pop-Location
Write-Host "  ✅ RDS Proxy provisioned." -ForegroundColor Green

# ── 5. Capture endpoints and write .env ─────────────────────────
Write-Host "`n[5/6] Fetching endpoints from Terraform outputs..." -ForegroundColor Yellow
Push-Location $TF_DIR
$proxyEndpoint  = (terraform output -raw rds_proxy_endpoint 2>$null).Trim()
$readerEndpoint = (terraform output -raw aurora_reader_endpoint 2>$null).Trim()
$writerEndpoint = (terraform output -raw aurora_writer_endpoint 2>$null).Trim()
Pop-Location

Write-Host "  RDS Proxy Endpoint   : $proxyEndpoint" -ForegroundColor Cyan
Write-Host "  Aurora Reader Endpoint: $readerEndpoint" -ForegroundColor Cyan
Write-Host "  Aurora Writer Endpoint: $writerEndpoint (migration only)" -ForegroundColor DarkGray

# Write endpoints to .env in project root
$envFile = "$ROOT\.env"
if (Test-Path $envFile) {
    # Update existing values
    (Get-Content $envFile) |
        ForEach-Object {
            if ($_ -match '^RDS_PROXY_ENDPOINT=')     { "RDS_PROXY_ENDPOINT=$proxyEndpoint" }
            elseif ($_ -match '^AURORA_READER_ENDPOINT=') { "AURORA_READER_ENDPOINT=$readerEndpoint" }
            elseif ($_ -match '^USE_AWS=')              { "USE_AWS=true" }
            elseif ($_ -match '^DB_PASSWORD=')          { "DB_PASSWORD=$Password" }
            else { $_ }
        } | Set-Content $envFile
    Write-Host "  ✅ .env updated with live endpoints." -ForegroundColor Green
} else {
    Write-Host "  ⚠️  No .env found at $envFile — copy .env.example to .env and re-run." -ForegroundColor Yellow
}

# ── 6. Print next steps ───────────────────────────────────────────
Write-Host "`n[6/6] Next steps:" -ForegroundColor Yellow
Write-Host "  a) Wait for RDS Proxy status = Available in AWS Console → RDS → Proxies"
Write-Host "  b) Schema migration (first session only):"
Write-Host "     python infra\scripts\migrate_schema.py --host $writerEndpoint --password $Password"
Write-Host "  c) Start backend with AWS mode:"
Write-Host "     `$env:USE_AWS='true'; python -m uvicorn api.main:app --port 8000 --reload"
Write-Host "  d) Run tests:"
Write-Host "     `$env:USE_AWS='true'; python -m pytest tests/ -v"
Write-Host ""
Write-Host "  ⚠️  REMEMBER: Run phase2_destroy.ps1 before ending your session!" -ForegroundColor Red
Write-Host "═══════════════════════════════════════════════════════`n" -ForegroundColor Cyan
