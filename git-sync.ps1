# GitHub 自動 push/pull 用 PowerShell スクリプト
# 使い方:
#   .\git-sync.ps1 sync              # リモートから取得 → ローカル変更をプッシュ（推奨）
#   .\git-sync.ps1 sync -Msg "fix: 〇〇を修正"  # メッセージを指定して同期
#   .\git-sync.ps1 pull              # リモートから最新の変更を取得
#   .\git-sync.ps1 push              # デフォルトメッセージで push
#   .\git-sync.ps1 push -Msg "fix: 〇〇を修正"  # メッセージを指定して push

param(
    [Parameter(Position=0)]
    [ValidateSet("sync", "pull", "push", "add", "commit", "status", "status-verbose")]
    [string]$Command = "sync",
    
    [string]$Msg = "",
    [string]$Remote = "origin",
    [string]$Branch = ""
)

# ブランチが指定されていない場合は現在のブランチを取得
if ([string]::IsNullOrEmpty($Branch)) {
    $Branch = (git branch --show-current).Trim()
}

# メッセージが指定されていない場合はデフォルトメッセージを生成
if ([string]::IsNullOrEmpty($Msg)) {
    $Msg = "Update: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}

function Invoke-GitAdd {
    Write-Host "Staging all changes (including new/untracked files, images, PDFs)..." -ForegroundColor Cyan
    git add -A
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Staged all changes" -ForegroundColor Green
        $status = git status --short
        if ($status) {
            Write-Host "Files to be committed:" -ForegroundColor Gray
            $status | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        }
    }
}

function Invoke-GitCommit {
    param([string]$Message)
    Write-Host "Committing changes..." -ForegroundColor Cyan
    git commit -m $Message
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Committed with message: $Message" -ForegroundColor Green
    } else {
        Write-Host "No changes to commit or commit failed (this is OK)" -ForegroundColor Yellow
    }
}

function Invoke-GitPull {
    param([string]$RemoteName, [string]$BranchName)
    Write-Host "Pulling from $RemoteName/$BranchName..." -ForegroundColor Cyan
    git pull $RemoteName $BranchName
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Pulled from $RemoteName/$BranchName" -ForegroundColor Green
        return $true
    } else {
        Write-Host "Pull failed! There may be conflicts or uncommitted changes." -ForegroundColor Red
        Write-Host "Please resolve conflicts or commit your changes first." -ForegroundColor Yellow
        return $false
    }
}

function Invoke-GitPush {
    param([string]$RemoteName, [string]$BranchName)
    Write-Host "Pushing to $RemoteName/$BranchName..." -ForegroundColor Cyan
    git push $RemoteName $BranchName
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Pushed to $RemoteName/$BranchName" -ForegroundColor Green
    } else {
        Write-Host "Push failed" -ForegroundColor Red
        exit 1
    }
}

function Show-GitStatus {
    Write-Host "`n=== Git Status ===" -ForegroundColor Cyan
    git status
}

function Show-GitStatusVerbose {
    Show-GitStatus
    Write-Host "`n=== Latest Commit ===" -ForegroundColor Cyan
    git log -1 --oneline
    Write-Host "`n=== Remote Info ===" -ForegroundColor Cyan
    git remote -v
}

# メイン処理
switch ($Command) {
    "sync" {
        Write-Host "`n=== Starting Sync ===" -ForegroundColor Yellow
        
        # まずローカルの変更をコミット（競合を避けるため）
        git diff --quiet
        $hasUnstaged = $LASTEXITCODE -ne 0
        git diff --cached --quiet
        $hasStaged = $LASTEXITCODE -ne 0
        
        if ($hasUnstaged -or $hasStaged) {
            Write-Host "Committing local changes before pull..." -ForegroundColor Cyan
            Invoke-GitAdd
            Invoke-GitCommit -Message $Msg
        }
        
        # リモートから取得
        $pullSuccess = Invoke-GitPull -RemoteName $Remote -BranchName $Branch
        if (-not $pullSuccess) {
            Write-Host "`n=== Sync Failed ===" -ForegroundColor Red
            Write-Host "Pull failed. Please resolve conflicts manually and try again." -ForegroundColor Yellow
            Write-Host "You can use: git status  to see what needs to be resolved." -ForegroundColor Yellow
            exit 1
        }
        
        # プッシュ（pull後に新しい変更がある可能性があるため、再度確認）
        git diff --quiet
        $hasUnstaged = $LASTEXITCODE -ne 0
        git diff --cached --quiet
        $hasStaged = $LASTEXITCODE -ne 0
        
        if ($hasUnstaged -or $hasStaged) {
            Write-Host "Committing any remaining changes after pull..." -ForegroundColor Cyan
            Invoke-GitAdd
            Invoke-GitCommit -Message $Msg
        }
        
        Invoke-GitPush -RemoteName $Remote -BranchName $Branch
        Write-Host "`n=== Sync Complete ===" -ForegroundColor Green
        Write-Host "Synced: Pulled from and pushed to $Remote/$Branch" -ForegroundColor Green
    }
    
    "pull" {
        Write-Host "`n=== Pulling ===" -ForegroundColor Yellow
        $pullSuccess = Invoke-GitPull -RemoteName $Remote -BranchName $Branch
        if (-not $pullSuccess) {
            exit 1
        }
    }
    
    "push" {
        Write-Host "`n=== Pushing ===" -ForegroundColor Yellow
        Invoke-GitAdd
        Invoke-GitCommit -Message $Msg
        Invoke-GitPush -RemoteName $Remote -BranchName $Branch
        Write-Host "Pushed to $Remote/$Branch" -ForegroundColor Green
    }
    
    "add" {
        Write-Host "`n=== Staging ===" -ForegroundColor Yellow
        Invoke-GitAdd
    }
    
    "commit" {
        Write-Host "`n=== Committing ===" -ForegroundColor Yellow
        Invoke-GitAdd
        Invoke-GitCommit -Message $Msg
    }
    
    "status" {
        Show-GitStatus
    }
    
    "status-verbose" {
        Show-GitStatusVerbose
    }
    
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Available commands: sync, pull, push, add, commit, status, status-verbose" -ForegroundColor Yellow
        exit 1
    }
}
