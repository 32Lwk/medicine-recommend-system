# Register Windows Task Scheduler jobs for AWS staging competition schedule (JST).
# Usage (Admin not required for per-user tasks):
#   .\scripts\setup-aws-staging-schedule.ps1
# Remove:
#   .\scripts\setup-aws-staging-schedule.ps1 -Remove

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

$Prefix = "MedicineRecommend-AWS-Staging"
$Events = @(
    @{
        Name = "$Prefix-0731-Resume"
        At = "2026-07-31T16:15:00"
        Action = "resume"
        Label = "7/31 mentoring resume (17:00-17:30)"
        Description = "Resume ECS before 7/31 mentoring (17:00 start)"
    },
    @{
        Name = "$Prefix-0731-Stop"
        At = "2026-07-31T18:00:00"
        Action = "stop"
        Label = "7/31 mentoring stop"
        Description = "Stop ECS after 7/31 mentoring (17:30 end)"
    },
    @{
        Name = "$Prefix-0802-Resume"
        At = "2026-08-02T23:00:00"
        Action = "resume"
        Label = "8/3 competition window resume (always-on until 8/6)"
        Description = "Resume ECS for 8/3-8/6 always-on window"
    },
    @{
        Name = "$Prefix-0807-Stop"
        At = "2026-08-07T00:05:00"
        Action = "stop"
        Label = "Post-competition stop (after 8/6 23:59)"
        Description = "Stop ECS after competition window"
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
Write-Host "Schedule registered (JST local time). Verify:"
Write-Host "  Get-ScheduledTask -TaskName '$Prefix*' | Format-Table TaskName, State"
Write-Host "Log: log/ops/aws-staging-schedule.log"
Write-Host "Remove: .\scripts\setup-aws-staging-schedule.ps1 -Remove"
