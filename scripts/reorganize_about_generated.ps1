# Reorganize static/img/about/generated into clear subfolders.
$ErrorActionPreference = "Stop"
$root = "d:\Programing\medicine-recommend\static\img\about\generated"
$aboutParent = "d:\Programing\medicine-recommend\static\img\about"

$dirs = @(
    "$root\about\hero",
    "$root\about\icons",
    "$root\about\pain",
    "$root\about\backgrounds",
    "$root\about\ui-mocks",
    "$root\about\safety",
    "$root\about\demo",
    "$root\about\legacy",
    "$root\about\tech-diagram",
    "$root\drugstore",
    "$root\line",
    "$root\infographics\system-design",
    "$root\infographics\saas-cto",
    "$root\infographics\pharma-cto",
    "$root\infographics\architecture",
    "$root\infographics\cto-pitch-deck",
    "$root\infographics\gcp-log-analysis",
    "$root\infographics\service",
    "$root\infographics\summary",
    "$root\presentations\service-deck",
    "$root\presentations\gikushokai",
    "$root\presentations\pamphlet",
    "$root\presentations\pipeline-v2",
    "$root\presentations\geekhaku",
    "$root\presentations\particles",
    "$root\archive\cursor-imports",
    "$root\archive\duplicates",
    "$root\archive\unrelated"
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

function Move-Safe {
    param([string]$Src, [string]$DestDir)
    if (-not (Test-Path $Src)) { return $false }
    $name = Split-Path $Src -Leaf
    $dest = Join-Path $DestDir $name
    if (Test-Path $dest) {
        $archive = Join-Path $root "archive\duplicates"
        $dest = Join-Path $archive $name
        $i = 1
        while (Test-Path $dest) {
            $base = [System.IO.Path]::GetFileNameWithoutExtension($name)
            $ext = [System.IO.Path]::GetExtension($name)
            $dest = Join-Path $archive "${base}_dup$i$ext"
            $i++
        }
    }
    Move-Item -Force $Src $dest
    return $true
}

# --- img/about root → generated/about ---
Move-Safe "$aboutParent\demo-ipad-product.png" "$root\about\demo"
Move-Safe "$aboutParent\Demo.png" "$root\about\legacy"
Move-Safe "$aboutParent\flowchart.png" "$root\about\legacy"
Move-Safe "$aboutParent\language.png" "$root\about\legacy"
Move-Safe "$aboutParent\medicine_recommended.png" "$root\about\legacy"
Move-Safe "$aboutParent\recommend.png" "$root\about\legacy"

# --- generated root → categorized ---
$rootFiles = Get-ChildItem $root -File -ErrorAction SilentlyContinue
foreach ($f in $rootFiles) {
    $n = $f.Name
    $src = $f.FullName
    $moved = $false
    switch -Regex ($n) {
        '^hero-' { $moved = Move-Safe $src "$root\about\hero" }
        '^icon-' { $moved = Move-Safe $src "$root\about\icons" }
        '^pain-' { $moved = Move-Safe $src "$root\about\pain" }
        '^bg-pattern|^soft-gradient' { $moved = Move-Safe $src "$root\about\backgrounds" }
        '^how-chat|^chat-ui-mock' { $moved = Move-Safe $src "$root\about\ui-mocks" }
        '^safety-' { $moved = Move-Safe $src "$root\about\safety" }
        '^architecture-diagram|^tech-architecture|^tech-stack' { $moved = Move-Safe $src "$root\about\tech-diagram" }
        '^trust-healthcare' { $moved = Move-Safe $src "$root\about\safety" }
        '^line-flex|^rich-menu' { $moved = Move-Safe $src "$root\line" }
        '^drugstore' { $moved = Move-Safe $src "$root\drugstore" }
        '^infographic-summary' { $moved = Move-Safe $src "$root\infographics\summary" }
        default { }
    }
}

# --- system-design/ → infographics/system-design/ ---
$sd = "$root\system-design"
if (Test-Path $sd) {
    Get-ChildItem $sd -File | ForEach-Object { Move-Safe $_.FullName "$root\infographics\system-design" }
    Remove-Item $sd -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Classify saas-cto dump ---
$saasDump = "$root\infographics\saas-cto"
if (Test-Path $saasDump) {
    Get-ChildItem $saasDump -File | ForEach-Object {
        $n = $_.Name
        $src = $_.FullName
        if ($n -match '^SaaS-\d+\.png$') { return }
        if ($n -match '^c__Users_|^d__Programing_') { Move-Safe $src "$root\archive\cursor-imports"; return }
        if ($n -match 'beach-|personality_|medical-test-|safety-test-|^_tmp') { Move-Safe $src "$root\archive\unrelated"; return }
        if ($n -match '^slide-\d') { Move-Safe $src "$root\presentations\service-deck"; return }
        if ($n -match '^slide_\d') { Move-Safe $src "$root\presentations\service-deck"; return }
        if ($n -match '^slide\d') { Move-Safe $src "$root\presentations\gikushokai"; return }
        if ($n -match '^pamphlet') { Move-Safe $src "$root\presentations\pamphlet"; return }
        if ($n -match '^geekhaku') { Move-Safe $src "$root\presentations\geekhaku"; return }
        if ($n -match '^chat_pipeline_v2') { Move-Safe $src "$root\presentations\pipeline-v2"; return }
        if ($n -match '^particle-|^event-|^pumpkin-soft|^heart-glow') { Move-Safe $src "$root\presentations\particles"; return }
        if ($n -match '^drugstore') { Move-Safe $src "$root\drugstore"; return }
        if ($n -match '^line-flex|^rich-menu') { Move-Safe $src "$root\line"; return }
        if ($n -match '^\d{2}-') { Move-Safe $src "$root\infographics\system-design"; return }
        if ($n -match '^hero-|^icon-|^pain-|^bg-pattern|^soft-gradient|^how-chat|^chat-ui|^safety-|^trust-') {
            $sub = switch -Regex ($n) {
                '^hero-' { 'hero' }; '^icon-' { 'icons' }; '^pain-' { 'pain' }
                '^bg-pattern|^soft-gradient' { 'backgrounds' }
                '^how-chat|^chat-ui' { 'ui-mocks' }; default { 'safety' }
            }
            Move-Safe $src "$root\about\$sub"; return
        }
        if ($n -match '^architecture-diagram|^tech-architecture|^tech-stack') { Move-Safe $src "$root\about\tech-diagram"; return }
        if ($n -match '^infographic-summary') { Move-Safe $src "$root\infographics\summary"; return }
        # remaining misc → archive/unrelated
        Move-Safe $src "$root\archive\unrelated"
    }
}

# --- Move tech-stack-export if exists at about level ---
Move-Safe "$aboutParent\tech-stack-export.html" "$root\about\legacy" -ErrorAction SilentlyContinue

# --- Summary: counts ---
Write-Host "`n=== Final structure (file counts) ==="
Get-ChildItem $root -Directory | Sort-Object Name | ForEach-Object {
    $count = (Get-ChildItem $_.FullName -Recurse -File).Count
    Write-Host ("{0,-30} {1}" -f $_.Name, $count)
}
$total = (Get-ChildItem $root -Recurse -File).Count
Write-Host "`nTotal files under generated: $total"
