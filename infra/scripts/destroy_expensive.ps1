# Helper script to destroy Phase 2 expensive resources (Aurora, RDS Proxy, ElastiCache)
# Run this at the end of your working session to prevent billing accumulation.

$TerraformBin = Join-Path (Get-Item $PSScriptRoot).Parent.FullName "bin\terraform.exe"
$TerraformDir = Join-Path (Get-Item $PSScriptRoot).Parent.FullName "terraform"

Write-Host "Destroying Phase 2 expensive resources..." -ForegroundColor Red

& $TerraformBin -chdir=$TerraformDir destroy -var="enable_expensive_core=false" -auto-approve

Write-Host "Phase 2 expensive core destroyed. Phase 1 foundation remains active." -ForegroundColor Green

