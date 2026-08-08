# PR 用 E2E コーパス スモーク（既定 20 分岐）
# 前提: app.py が http://127.0.0.1:5000 で起動済み
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$venv = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $venv)) { $venv = "python" }

& $venv scripts/build_v2_e2e_corpus_from_logs.py
& $venv scripts/validate_e2e_corpus.py
& $venv scripts/local_v2_chat_test_runner.py `
  --scenarios-path tests/fixtures/v2_e2e_corpus_pr500.yaml `
  --limit 20 `
  --report-suffix pr500-smoke
