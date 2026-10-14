# Helper script to set session credentials for AWS Academy Learner Lab
param (
    [Parameter(Mandatory=$true)][string]$AccessKeyId,
    [Parameter(Mandatory=$true)][string]$SecretAccessKey,
    [Parameter(Mandatory=$true)][string]$SessionToken,
    [string]$Region = "us-east-1"
)

$env:AWS_ACCESS_KEY_ID = $AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $SecretAccessKey
$env:AWS_SESSION_TOKEN = $SessionToken
$env:AWS_DEFAULT_REGION = $Region
$env:AWS_REGION = $Region

Write-Host "AWS Academy credentials loaded successfully for region $Region" -ForegroundColor Green
Write-Host "Verifying identity..." -ForegroundColor Yellow
python -c "import boto3; sts = boto3.client('sts'); print(sts.get_caller_identity())"

