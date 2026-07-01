# Chat Pipeline v2 — ローカル / dev 一括 ON
# Usage:
#   . .\scripts\dev_v2_flags.ps1          # v2 全機能有効（ALLOWLIST 不要）
#   . .\scripts\dev_v2_flags.ps1 -Off     # 明示 OFF（dev 自動 ON を上書き）

param(
    [switch]$Off
)

if ($Off) {
    $env:CHAT_PIPELINE_V2 = "false"
} else {
    $env:CHAT_PIPELINE_V2 = "true"
}

Remove-Item Env:CHAT_PIPELINE_V2_ALLOWLIST -ErrorAction SilentlyContinue
Remove-Item Env:CHAT_PIPELINE_V2_DENYLIST -ErrorAction SilentlyContinue
Remove-Item Env:CHAT_PIPELINE_V2_INTENT_ROUTER -ErrorAction SilentlyContinue
Remove-Item Env:CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH -ErrorAction SilentlyContinue
Remove-Item Env:CHAT_PIPELINE_V2_INTENT_ROUTER_LLM -ErrorAction SilentlyContinue

Write-Host "CHAT_PIPELINE_V2=$env:CHAT_PIPELINE_V2 (router/dispatch/LLM cascade ON when true)"
Write-Host "ALLOWLIST/DENYLIST cleared — all sessions use v2"
