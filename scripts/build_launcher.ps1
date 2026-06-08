param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$RuntimePython = Join-Path $AppRoot ".venv\Scripts\python.exe"
$Launcher = Join-Path $AppRoot "launcher\launcher.py"
$Spec = Join-Path $AppRoot "launcher\launcher.spec"
$DistDir = Join-Path $AppRoot "dist"
$WorkDir = Join-Path $AppRoot "build\launcher"
$ExpectedExe = Join-Path $DistDir "A2SB Restorer\A2SB Restorer.exe"

if ($DryRun) {
    Write-Host "Would build launcher from $Launcher using $Spec"
    Write-Host "Expected output: $ExpectedExe"
    exit 0
}

if (-not (Test-Path $RuntimePython)) {
    throw "Development venv missing. Create .venv and install requirements/build.txt first."
}
if (-not (Test-Path $Launcher)) {
    throw "Launcher source missing: $Launcher"
}

if (Test-Path $Spec) {
    Push-Location (Join-Path $AppRoot "launcher")
    try {
        & $RuntimePython -m PyInstaller "launcher.spec" --noconfirm --distpath $DistDir --workpath $WorkDir
    } finally {
        Pop-Location
    }
} else {
    & $RuntimePython -m PyInstaller $Launcher --noconfirm --onedir --name "A2SB Restorer" --distpath $DistDir --workpath $WorkDir
}
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
if (-not (Test-Path $ExpectedExe)) {
    throw "Launcher build did not produce expected one-folder app: $ExpectedExe"
}
exit $LASTEXITCODE
