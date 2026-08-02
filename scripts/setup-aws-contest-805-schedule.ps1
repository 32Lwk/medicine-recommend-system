# 8/5 (JST) 0:00-23:59 のみ大会スケール（ECS 10台 + 1vCPU + WAF 緩和）
#
# Usage:
#   .\scripts\setup-aws-contest-805-schedule.ps1
#   .\scripts\setup-aws-contest-805-schedule.ps1 -Remove
#
# スケジュール（ローカル PC の時刻 = JST 想定）:
#   2026-08-05 00:00:00  contest-apply  （大会容量へ）
#   2026-08-06 00:00:00  contest-restore（8/5 終了後に平常構成へ）
#
# 注意: PC がスリープ中は StartWhenAvailable で起動後に実行。確実性重視なら当日手動 --apply も可。
param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ActionScript = Join-Path $Root "scripts\aws-staging-scheduled-action.ps1"
$PwshCmd = Get-Command pwsh -ErrorAction SilentlyContinue
if ($PwshCmd) {
    $Pwsh = $PwshCmd.Source
}
else {
    $Pwsh = (Get-Command powershell -ErrorAction SilentlyContinue).Source
}

$Prefix = "MedicineRecommend-Contest-805"
$Events = @(
    @{
        Name = "$Prefix-Apply"
        At = "2026-08-05T00:00:00"
        Action = "contest-apply"
        Label = "8/5 00:00 JST contest capacity apply"
        Description = "Scale ECS to 10x1024/2048, WAF 10000, Gunicorn workers 3"
    },
    @{
        Name = "$Prefix-Restore"
        At = "2026-08-06T00:00:00"
        Action = "contest-restore"
        Label = "8/6 00:00 JST contest capacity restore (end of 8/5 window)"
        Description = "Restore ECS/WAF from scripts/.aws-contest-capacity-state.json"
    }
)

function Remove-ScheduleTasks {
    foreach ($ev in $Events) {
        Unregister-ScheduledTask -TaskName $ev.Name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Removed: $($ev.Name)"
    }
}

if ($Remove) {
    Remove-ScheduleTasks
    exit 0
}

if (-not (Test-Path $ActionScript)) {
    throw "Missing $ActionScript"
}

Remove-ScheduleTasks

foreach ($ev in $Events) {
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$ActionScript`" -Action $($ev.Action) -Label `"$($ev.Label)`""
    $action = New-ScheduledTaskAction -Execute $Pwsh -Argument $argList -WorkingDirectory $Root
    $trigger = New-ScheduledTaskTrigger -Once -At ([datetime]$ev.At)
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $ev.Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $ev.Description | Out-Null
    Write-Host "Registered: $($ev.Name) at $($ev.At) -> $($ev.Action)"
}

Write-Host ""
Write-Host "8/5 contest schedule registered (local time = JST)."
Write-Host "  Apply:  2026-08-05 00:00  -> prepare-aws-contest-capacity.sh --apply"
Write-Host "  Restore: 2026-08-06 00:00 -> prepare-aws-contest-capacity.sh --restore"
Write-Host ""
Write-Host "Verify:"
Write-Host "  Get-ScheduledTask -TaskName '$Prefix*' | Format-Table TaskName, State"
Write-Host "Log: log/ops/aws-staging-schedule.log"
Write-Host "Remove: .\scripts\setup-aws-contest-805-schedule.ps1 -Remove"
