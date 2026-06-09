param(
    [Parameter(Mandatory=$true)]
    [Alias("Input")]
    [string]$InputPath,

    [Alias("Output")]
    [string]$OutputPath,
    [int]$Steps = 2,
    [string]$CheckpointFolder,
    [switch]$TrustManualCheckpoints,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$RuntimePython = Join-Path $AppRoot "runtime\Scripts\python.exe"
$DevPython = Join-Path $AppRoot ".venv\Scripts\python.exe"

if (Test-Path $RuntimePython) {
    $Python = $RuntimePython
} elseif (Test-Path $DevPython) {
    $Python = $DevPython
} else {
    $Python = "python"
}

$args = @("-m", "rolling_a2sb.cli", "restore", "--input", $InputPath, "--steps", "$Steps")
if ($OutputPath) { $args += @("--output", $OutputPath) }
if ($CheckpointFolder) { $args += @("--checkpoint-folder", $CheckpointFolder) }
if ($TrustManualCheckpoints) { $args += @("--trust-manual-checkpoints") }
if ($DryRun) { $args += @("--dry-run") }

Push-Location $AppRoot
try {
    & $Python @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
