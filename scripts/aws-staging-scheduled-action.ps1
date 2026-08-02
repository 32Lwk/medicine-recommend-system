# AWS staging スケジュール実行 + デスクトップ通知
# Usage:
#   .\scripts\aws-staging-scheduled-action.ps1 -Action resume -Label "7/31 mentoring start"
#   .\scripts\aws-staging-scheduled-action.ps1 -Action contest-apply -Label "8/5 contest scale up"
#   .\scripts\aws-staging-scheduled-action.ps1 -Action contest-restore -Label "8/5 contest scale down"
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("resume", "stop", "contest-apply", "contest-restore")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$Label
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Bash = "C:\Program Files\Git\bin\bash.exe"
$LogDir = Join-Path $Root "log\ops"
$LogFile = Join-Path $LogDir "aws-staging-schedule.log"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-ScheduleLog {
    param([string]$Message)
    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Action, $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Show-ScheduleToast {
    param([string]$Title, [string]$Body, [string]$Level = "Info")
    try {
        if (-not ([System.Management.Automation.PSTypeName]"BurntToast.BurntToastMessageBuilder").Type) {
            Import-Module BurntToast -ErrorAction Stop
        }
        New-BurntToastNotification -Text $Title, $Body | Out-Null
    }
    catch {
        try {
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.MessageBox]::Show($Body, $Title) | Out-Null
        }
        catch {
            Write-ScheduleLog "Notification fallback: $Title — $Body"
        }
    }
}

if (-not (Test-Path $Bash)) {
    Write-ScheduleLog "ERROR: Git Bash not found at $Bash"
    Show-ScheduleToast "AWS staging schedule failed" "$Label — Git Bash not found"
    exit 1
}

switch ($Action) {
    "resume" { $bashCmd = "cd '$($Root -replace '\\','/')' && export AWS_PROFILE=medicine-recommend-dev && ./scripts/resume-aws-staging.sh" }
    "stop" { $bashCmd = "cd '$($Root -replace '\\','/')' && export AWS_PROFILE=medicine-recommend-dev && ./scripts/stop-aws-staging.sh" }
    "contest-apply" { $bashCmd = "cd '$($Root -replace '\\','/')' && export AWS_PROFILE=medicine-recommend-dev && ./scripts/prepare-aws-contest-capacity.sh --apply" }
    "contest-restore" { $bashCmd = "cd '$($Root -replace '\\','/')' && export AWS_PROFILE=medicine-recommend-dev && ./scripts/prepare-aws-contest-capacity.sh --restore" }
}
Write-ScheduleLog "START $Label -> $Action"

$output = & $Bash -lc $bashCmd 2>&1
$output | ForEach-Object { Write-ScheduleLog $_ }

if ($LASTEXITCODE -ne 0) {
    Write-ScheduleLog "ERROR exit=$LASTEXITCODE"
    Show-ScheduleToast "AWS staging $Action failed" "$Label — see log/ops/aws-staging-schedule.log"
    exit $LASTEXITCODE
}

if ($Action -in @("resume", "contest-apply")) {
    Start-Sleep -Seconds 45
    $health = try {
        (Invoke-WebRequest -Uri "https://aws.medicine.yutok.dev/health" -UseBasicParsing -TimeoutSec 30).StatusCode
    }
    catch {
        "error"
    }
    Write-ScheduleLog "health=$health"
    if ($health -eq 200) {
        $toastTitle = if ($Action -eq "contest-apply") { "AWS contest capacity applied" } else { "AWS staging resumed" }
        Show-ScheduleToast $toastTitle "$Label — health OK (200)"
    }
    else {
        Show-ScheduleToast "AWS staging action done (check health)" "$Label — health=$health"
    }
}
elseif ($Action -eq "contest-restore") {
    Show-ScheduleToast "AWS contest capacity restored" "$Label — normal sizing"
}
else {
    Show-ScheduleToast "AWS staging stopped" "$Label — ECS desiredCount=0"
}

Write-ScheduleLog "DONE $Label"
exit 0
