# medicine-recommend 向け AWS CLI 環境（PowerShell）
# Usage: . .\scripts\aws-env.ps1
$awsCli = "C:\Program Files\Amazon\AWSCLIV2"
if (Test-Path $awsCli) {
    $env:PATH = "$awsCli;" + $env:PATH
}
$env:AWS_PROFILE = "medicine-recommend-dev"
Write-Host "AWS_PROFILE=$env:AWS_PROFILE"
