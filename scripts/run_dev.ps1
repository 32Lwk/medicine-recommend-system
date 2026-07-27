# ローカル開発サーバー起動（.venv 固定）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error ".venv が見つかりません。先に python -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt を実行してください。"
}

Set-Location $Root
& $Python app.py @args
