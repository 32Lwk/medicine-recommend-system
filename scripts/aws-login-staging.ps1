# Diagnose / repair AWS CLI auth for medicine-recommend staging (account 620992446973).
#
# Root causes this script addresses:
# 1) Profiles with Access Keys cannot use `aws login` (Configuration error).
# 2) `default` login_session for ***973 expires; needs interactive `aws login`.
# 3) Scripts historically defaulted to broken `medicine-recommend-dev` (old ***994 keys).
# 4) Browser 400「要求の形式が正しくありません」— often missing SignInLocalDevelopmentAccess
#    on the *active console session* (or wrong account / switch-role not done yet).
#
# Usage:
#   cd D:\Programing\medicine-recommend
#   .\scripts\aws-login-staging.ps1                 # diagnose only
#   .\scripts\aws-login-staging.ps1 -Login          # aws login on -Profile (default)
#   .\scripts\aws-login-staging.ps1 -Login -Remote  # paste-code flow (recommended if 400 / firewall)
#   .\scripts\aws-login-staging.ps1 -QuarantineStaleKeys -Login
#   .\scripts\aws-login-staging.ps1 -Show400Help
#
# Before -Login (required for browser 400 fix):
#   1) Open a private window
#   2) Sign in to Console for account 620992446973 as root, OR as IAM user/role that has
#      managed policy SignInLocalDevelopmentAccess (signin:AuthorizeOAuth2Access + CreateOAuth2Token)
#   3) If you use switch-role: switch FIRST, then run this script
#   4) Do NOT reuse an old authorize URL from a previous failed attempt
#
# After success:
#   aws sts get-caller-identity --profile default
#   # Account must be 620992446973

[CmdletBinding()]
param(
    [string]$Profile = "default",
    [string]$ExpectedAccountId = "620992446973",
    [switch]$Login,
    [switch]$Remote,
    [switch]$QuarantineStaleKeys,
    [switch]$SkipBrowser,
    [switch]$Show400Help,
    [switch]$ClearLoginCache
)

$ErrorActionPreference = "Continue"
$AwsDir = Join-Path $env:USERPROFILE ".aws"
$ConfigPath = Join-Path $AwsDir "config"
$CredPath = Join-Path $AwsDir "credentials"
$ExpectedAccountId = $ExpectedAccountId.Trim()

function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Write-400Help {
    Write-Section "Browser 400 help (要求の形式が正しくありません)"
    Write-Host @"
That Japanese 400 page is usually NOT a typo. Common real causes:

  A) Active Console session lacks SignInLocalDevelopmentAccess
     - Root user: no extra policy needed (AWS docs).
     - IAM user/role: attach AWS managed policy SignInLocalDevelopmentAccess
       (actions: signin:AuthorizeOAuth2Access, signin:CreateOAuth2Token).

  B) Switch-role workflow: browser still on base account (no policy) when aws login runs
     - Fix: Console → switch into account $ExpectedAccountId first → then aws login.

  C) Stale authorize URL / cookies from a previous attempt
     - Close the 400 tab. Use a NEW private window. Do not reopen an old link.

  D) Localhost OAuth callback blocked
     - Use: .\scripts\aws-login-staging.ps1 -Login -Remote

Recommended recovery (root or IAM with the policy on $ExpectedAccountId):

  1) Private window → https://$ExpectedAccountId.signin.aws.amazon.com/console
     (or root sign-in for this account)
  2) Confirm account ID ends with ...973 in the Console top-right.
  3) cd D:\Programing\medicine-recommend
  4) .\scripts\aws-login-staging.ps1 -ClearLoginCache -Login -Remote
  5) Open the NEW URL printed in the terminal (not an old tab).
  6) Approve / paste the authorization code back into PowerShell.
  7) aws sts get-caller-identity --profile default

Fallback if aws login keeps failing: create IAM access keys for a user on
account $ExpectedAccountId (not the old ***994 keys) and put them in a NEW
profile name, e.g. medicine-recommend-dev-$ExpectedAccountId.
"@
}

if ($Show400Help) {
    Write-400Help
    exit 0
}

if ($ClearLoginCache) {
    Write-Section "Clear login cache"
    $cacheDir = Join-Path $AwsDir "login\cache"
    if (Test-Path $cacheDir) {
        $bakDir = Join-Path $AwsDir ("login\cache.bak." + (Get-Date -Format "yyyyMMdd_HHmmss"))
        Move-Item -LiteralPath $cacheDir -Destination $bakDir
        New-Item -ItemType Directory -Path $cacheDir | Out-Null
        Write-Host "Moved login cache -> $bakDir" -ForegroundColor Green
    }
    else {
        Write-Host "No login cache directory."
    }
}

function Get-CredentialProfileNames {
    if (-not (Test-Path $CredPath)) { return @() }
    Select-String -Path $CredPath -Pattern '^\[(.+)\]' | ForEach-Object { $_.Matches[0].Groups[1].Value }
}

function Test-ProfileHasAccessKeys([string]$Name) {
    (Get-CredentialProfileNames) -contains $Name
}

function Invoke-StsProbe([string]$Name) {
    $tmpOut = [System.IO.Path]::GetTempFileName()
    $tmpErr = [System.IO.Path]::GetTempFileName()
    try {
        $p = Start-Process -FilePath "aws" `
            -ArgumentList @("sts", "get-caller-identity", "--profile", $Name, "--output", "json") `
            -NoNewWindow -Wait -PassThru `
            -RedirectStandardOutput $tmpOut `
            -RedirectStandardError $tmpErr
        $stdout = (Get-Content -LiteralPath $tmpOut -Raw -ErrorAction SilentlyContinue)
        $stderr = (Get-Content -LiteralPath $tmpErr -Raw -ErrorAction SilentlyContinue)
        $text = @($stdout, $stderr) | Where-Object { $_ } | ForEach-Object { $_.Trim() }
        $joined = ($text -join "`n").Trim()
        return [PSCustomObject]@{
            Profile = $Name
            ExitCode = $p.ExitCode
            Output = $joined
            Ok = ($p.ExitCode -eq 0)
        }
    }
    finally {
        Remove-Item -LiteralPath $tmpOut, $tmpErr -Force -ErrorAction SilentlyContinue
    }
}

function Backup-AwsFile([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $bak = "$Path.bak.$stamp"
    Copy-Item -LiteralPath $Path -Destination $bak -Force
    return $bak
}

function Quarantine-AccessKeyProfiles {
    param([string[]]$Names)

    if (-not (Test-Path $CredPath)) {
        Write-Host "No credentials file; nothing to quarantine." -ForegroundColor Yellow
        return
    }

    $bak = Backup-AwsFile $CredPath
    Write-Host "Backed up credentials -> $bak"

    $legacyPath = Join-Path $AwsDir ("credentials.legacy-old-account." + (Get-Date -Format "yyyyMMdd_HHmmss"))
    $lines = Get-Content -LiteralPath $CredPath
    $keep = New-Object System.Collections.Generic.List[string]
    $legacy = New-Object System.Collections.Generic.List[string]
    $current = $null
    $inTarget = $false

    foreach ($line in $lines) {
        if ($line -match '^\[(.+)\]') {
            $current = $Matches[1]
            $inTarget = $Names -contains $current
        }
        if ($inTarget) {
            [void]$legacy.Add($line)
        }
        else {
            [void]$keep.Add($line)
        }
    }

    if ($legacy.Count -eq 0) {
        Write-Host "No matching Access Key profiles found among: $($Names -join ', ')" -ForegroundColor Yellow
        return
    }

    Set-Content -LiteralPath $legacyPath -Value $legacy -Encoding utf8
    # Keep a credentials file even if empty of profiles (AWS CLI tolerates empty / whitespace)
    $keepText = ($keep -join "`n").TrimEnd() + "`n"
    Set-Content -LiteralPath $CredPath -Value $keepText -Encoding utf8 -NoNewline:$false
    Write-Host "Quarantined profiles -> $legacyPath" -ForegroundColor Green
    Write-Host "Removed from credentials: $($Names -join ', ')" -ForegroundColor Green
    Write-Host "You can now run: aws login --profile <name> for those names, or use -Login on -Profile default."
}

Write-Section "Environment"
Write-Host ("AWS CLI: " + ((& aws --version) 2>&1 | Select-Object -First 1))
Write-Host "Config:      $ConfigPath"
Write-Host "Credentials: $CredPath"
Write-Host "Target profile: $Profile"
Write-Host "Expected account: $ExpectedAccountId"

Write-Section "Profile inventory"
$credNames = @(Get-CredentialProfileNames)
Write-Host ("Access-key profiles in credentials: " + ($(if ($credNames.Count) { $credNames -join ', ' } else { '(none)' })))
if (Test-Path $ConfigPath) {
    Write-Host "config profiles / login_session:"
    Get-Content $ConfigPath | ForEach-Object { Write-Host "  $_" }
}

Write-Section "STS probes"
$profilesToProbe = @("default", "medicine-recommend-dev", "admin", "admin-cli") | Select-Object -Unique
if ($profilesToProbe -notcontains $Profile) { $profilesToProbe += $Profile }

$anyOk = $false
foreach ($p in $profilesToProbe) {
    $hasKeys = Test-ProfileHasAccessKeys $p
    $r = Invoke-StsProbe $p
    $status = if ($r.Ok) { "OK" } else { "FAIL" }
    $color = if ($r.Ok) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1}  access_keys={2}" -f $status, $p, $hasKeys) -ForegroundColor $color
    if ($r.Ok) {
        $anyOk = $true
        Write-Host $r.Output
        try {
            $id = $r.Output | ConvertFrom-Json
            if ($id.Account -ne $ExpectedAccountId) {
                Write-Host ("WARNING: Account {0} != expected {1}" -f $id.Account, $ExpectedAccountId) -ForegroundColor Yellow
            }
        }
        catch { }
    }
    else {
        $oneLine = ($r.Output -split "`r?`n" | Where-Object { $_ -and ($_ -notmatch '^\s*$') } | Select-Object -First 2) -join " | "
        Write-Host ("  -> {0}" -f $oneLine) -ForegroundColor DarkYellow
        if ($hasKeys) {
            Write-Host "  -> Cause: Access Key credentials block ``aws login`` on this profile." -ForegroundColor Yellow
            Write-Host "     Fix: .\scripts\aws-login-staging.ps1 -QuarantineStaleKeys" -ForegroundColor Yellow
            Write-Host "     Or:  aws login --profile ${p}-$ExpectedAccountId  (new profile name)" -ForegroundColor Yellow
        }
        elseif ($r.Output -match "session has expired|reauthenticate|aws login") {
            Write-Host "  -> Cause: login_session expired. Run: aws login --profile $p" -ForegroundColor Yellow
        }
    }
}

if ($QuarantineStaleKeys) {
    Write-Section "Quarantine stale Access Keys"
    # Old-account / invalid AKIA leftovers that block aws login
    Quarantine-AccessKeyProfiles -Names @("admin", "admin-cli", "medicine-recommend-dev")
}

if ($Login) {
    Write-Section "aws login --profile $Profile"
    if ((Test-ProfileHasAccessKeys $Profile) -and -not $QuarantineStaleKeys) {
        Write-Host "REFUSING login: profile '$Profile' still has Access Keys in credentials." -ForegroundColor Red
        Write-Host "Re-run with -QuarantineStaleKeys, or use -Profile default, or a new profile name." -ForegroundColor Red
        exit 2
    }
    if ($SkipBrowser) {
        Write-Host "SkipBrowser set; not starting interactive login."
    }
    else {
        Write-Host "Starting interactive aws login. Complete browser / console auth for account $ExpectedAccountId."
        Write-Host "If the browser shows Japanese 400 (要求の形式が正しくありません):" -ForegroundColor Yellow
        Write-Host "  - Sign into Console for $ExpectedAccountId FIRST (root, or IAM with SignInLocalDevelopmentAccess)." -ForegroundColor Yellow
        Write-Host "  - Prefer: .\scripts\aws-login-staging.ps1 -ClearLoginCache -Login -Remote" -ForegroundColor Yellow
        Write-Host "  - Help:   .\scripts\aws-login-staging.ps1 -Show400Help" -ForegroundColor Yellow
        Write-Host "Do not enable JEV primary / POLICY_ENFORCEMENT_D2 as part of this auth step."
        $loginArgs = @("login", "--profile", $Profile)
        if ($Remote) { $loginArgs += "--remote" }
        & aws @loginArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Host "aws login exited with code $LASTEXITCODE" -ForegroundColor Red
            Write-400Help
            exit $LASTEXITCODE
        }
    }

    Write-Section "Post-login STS"
    $r = Invoke-StsProbe $Profile
    if (-not $r.Ok) {
        Write-Host $r.Output -ForegroundColor Red
        exit 1
    }
    Write-Host $r.Output -ForegroundColor Green
    $id = $r.Output | ConvertFrom-Json
    if ($id.Account -ne $ExpectedAccountId) {
        Write-Host ("Account mismatch: got {0}, expected {1}" -f $id.Account, $ExpectedAccountId) -ForegroundColor Red
        exit 3
    }
    Write-Host "STS OK for staging account $ExpectedAccountId (profile=$Profile)." -ForegroundColor Green
    Write-Host "Tip: `$env:AWS_PROFILE='$Profile'   or   . .\scripts\aws-env.ps1"
    exit 0
}

Write-Section "Next steps"
if ($anyOk) {
    Write-Host "At least one profile already has working STS. Prefer AWS_PROFILE=$Profile only if it is OK above."
}
else {
    Write-Host "No working STS. Recommended path for this repo:" -ForegroundColor Yellow
    Write-Host "  0) Browser: private window → Console login for account $ExpectedAccountId"
    Write-Host "     (root OK; IAM needs SignInLocalDevelopmentAccess). Switch-role FIRST if used."
    Write-Host "  1) cd D:\Programing\medicine-recommend"
    Write-Host "  2) .\scripts\aws-login-staging.ps1 -ClearLoginCache -Login -Remote"
    Write-Host "  3) If browser 400 persists: .\scripts\aws-login-staging.ps1 -Show400Help"
    Write-Host "  4) Optional same-name profiles after quarantine:"
    Write-Host "     .\scripts\aws-login-staging.ps1 -QuarantineStaleKeys -Login -Remote -Profile medicine-recommend-dev"
}
Write-Host ""
Write-Host "Scripts now default AWS_PROFILE=default (see scripts/lib/aws_common.sh, scripts/aws-env.ps1)."
exit 1
