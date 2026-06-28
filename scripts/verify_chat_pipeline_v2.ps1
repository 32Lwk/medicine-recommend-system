#!/usr/bin/env pwsh
# Chat Pipeline v2 契約テスト一括実行（CI と同等）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== w1a scope =="
python scripts/check_w1a_scope.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== pytest =="
python -m pytest tests/dialogue/ tests/contract/ tests/chat/test_chat_post_pipeline_v2.py tests/handlers/test_chat_post_pipeline_sync.py tests/analysis/test_intent_router_log_analysis.py tests/dialogue/routing/ tests/handlers/test_nlu_resolve_v2_history.py tests/services/test_line_memory_context_v2.py tests/services/test_chat_response_service_v2.py tests/routing/test_routing_context.py tests/utils/test_correction_detection.py tests/services/test_counseling_generator_user_inject.py -q --tb=short
exit $LASTEXITCODE
