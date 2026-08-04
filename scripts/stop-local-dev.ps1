# ローカル app.py / uvicorn（既定 5000・5001）をプロセスツリーごと停止
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error ".venv が見つかりません。先に python -m venv .venv を作成してください。"
}

Set-Location $Root
& $Python (Join-Path $Root "scripts\stop_local_dev.py") @args
exit $LASTEXITCODE
