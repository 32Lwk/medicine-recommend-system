# Golden PR live E2E — validate + HTTP smoke
param(
    [string]$BaseUrl = "http://127.0.0.1:5000/",
    [int]$Subset = 0,
    [switch]$ValidateOnly,
    [switch]$NoJudge
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$args = @(
    "scripts/run_golden_pr_live.py",
    "--base-url", $BaseUrl,
    "--report-suffix", "golden-pr-live"
)
if ($Subset -gt 0) { $args += @("--subset", "$Subset") }
if ($ValidateOnly) { $args += "--validate-only" }
if (-not $NoJudge) { $args += "--judge-on-fail" }

Push-Location $Root
try {
    py -3 @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
