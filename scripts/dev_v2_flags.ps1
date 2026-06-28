# Chat Pipeline v2 — dev カナリア用環境変数（PowerShell）
# Usage:
#   . .\scripts\dev_v2_flags.ps1
#   . .\scripts\dev_v2_flags.ps1 -Sid "line:YOUR_USER_ID"
#   . .\scripts\dev_v2_flags.ps1 -Sid "line:YOUR_USER_ID" -Dispatch -Llm

param(
    [string]$Sid = "",
    [switch]$Shadow,
    [switch]$Dispatch,
    [switch]$Llm
)

$env:CHAT_PIPELINE_V2 = "true"

if ($Sid) {
    $env:CHAT_PIPELINE_V2_ALLOWLIST = $Sid
} else {
    Remove-Item Env:CHAT_PIPELINE_V2_ALLOWLIST -ErrorAction SilentlyContinue
}

Remove-Item Env:CHAT_PIPELINE_V2_DENYLIST -ErrorAction SilentlyContinue

# Shadow は既定 ON（明示 -Shadow のみでも可）
if ($Shadow -or (-not $Dispatch -and -not $Llm)) {
    $env:CHAT_PIPELINE_V2_INTENT_ROUTER = "true"
} else {
    Remove-Item Env:CHAT_PIPELINE_V2_INTENT_ROUTER -ErrorAction SilentlyContinue
}

if ($Dispatch) {
    $env:CHAT_PIPELINE_V2_INTENT_ROUTER = "true"
    $env:CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH = "true"
} else {
    Remove-Item Env:CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH -ErrorAction SilentlyContinue
}

if ($Llm) {
    $env:CHAT_PIPELINE_V2_INTENT_ROUTER = "true"
    $env:CHAT_PIPELINE_V2_INTENT_ROUTER_LLM = "true"
} else {
    Remove-Item Env:CHAT_PIPELINE_V2_INTENT_ROUTER_LLM -ErrorAction SilentlyContinue
}

Write-Host "CHAT_PIPELINE_V2=$env:CHAT_PIPELINE_V2"
Write-Host "CHAT_PIPELINE_V2_ALLOWLIST=$env:CHAT_PIPELINE_V2_ALLOWLIST"
Write-Host "CHAT_PIPELINE_V2_INTENT_ROUTER=$env:CHAT_PIPELINE_V2_INTENT_ROUTER"
Write-Host "CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH=$env:CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH"
Write-Host "CHAT_PIPELINE_V2_INTENT_ROUTER_LLM=$env:CHAT_PIPELINE_V2_INTENT_ROUTER_LLM"
