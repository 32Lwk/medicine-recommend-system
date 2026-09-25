param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt,

    [ValidateSet("fast", "quality")]
    [string]$Model = "fast",

    [string]$NegativePrompt = "",
    [string]$OutputDir = "local_outputs/imagegen",
    [int]$Width = 0,
    [int]$Height = 0,
    [int]$Steps = 0,
    [double]$GuidanceScale = -1,
    [int]$Seed = -1,
    [int]$NumImages = 1,
    [switch]$CpuOffload
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$python = Join-Path $root ".venv-imagegen\Scripts\python.exe"
$script = Join-Path $PSScriptRoot "generate.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing image generation venv: $python"
}

$argsList = @(
    $script,
    "--model", $Model,
    "--prompt", $Prompt,
    "--output-dir", $OutputDir,
    "--num-images", $NumImages
)

if ($NegativePrompt) {
    $argsList += @("--negative-prompt", $NegativePrompt)
}
if ($Width -gt 0) {
    $argsList += @("--width", $Width)
}
if ($Height -gt 0) {
    $argsList += @("--height", $Height)
}
if ($Steps -gt 0) {
    $argsList += @("--steps", $Steps)
}
if ($GuidanceScale -ge 0) {
    $argsList += @("--guidance-scale", $GuidanceScale)
}
if ($Seed -ge 0) {
    $argsList += @("--seed", $Seed)
}
if ($CpuOffload) {
    $argsList += "--cpu-offload"
}

& $python @argsList
