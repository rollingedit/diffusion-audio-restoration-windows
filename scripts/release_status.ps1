param(
    [string]$ArtifactsDir = "dist\installer",
    [string]$LicensesDir = "LICENSES"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$RuntimePython = Join-Path $AppRoot ".venv\Scripts\python.exe"

if (Test-Path $RuntimePython) {
    $Python = $RuntimePython
} else {
    $Python = "python"
}

Push-Location $AppRoot
try {
    & $Python -m rolling_a2sb.cli release-status --artifacts-dir $ArtifactsDir --licenses-dir $LicensesDir
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
