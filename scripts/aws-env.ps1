# medicine-recommend 向け AWS CLI 環境（PowerShell）
# Usage: . .\scripts\aws-env.ps1
#
# 新アカウント staging (620992446973) は AWS_PROFILE=default（aws login / login_session）。
# 旧 Access Key プロファイル medicine-recommend-dev は既定にしない。
# 診断・再ログイン: .\scripts\aws-login-staging.ps1 -Login

$awsCli = "C:\Program Files\Amazon\AWSCLIV2"
if (Test-Path $awsCli) {
    $env:PATH = "$awsCli;" + $env:PATH
}
if (-not $env:AWS_PROFILE) {
    $env:AWS_PROFILE = "default"
}
Write-Host "AWS_PROFILE=$env:AWS_PROFILE"
Write-Host "Auth diagnose/login: .\scripts\aws-login-staging.ps1 [-Login] [-QuarantineStaleKeys]"
