param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$RuntimePython = Join-Path $AppRoot ".venv\Scripts\python.exe"
$Launcher = Join-Path $AppRoot "launcher\launcher.py"
$Spec = Join-Path $AppRoot "launcher\launcher.spec"

if ($DryRun) {
    Write-Host "Would build launcher from $Launcher using $Spec"
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
        & $RuntimePython -m PyInstaller "launcher.spec" --noconfirm
    } finally {
        Pop-Location
    }
} else {
    & $RuntimePython -m PyInstaller $Launcher --noconfirm --onedir --name "A2SB Restorer"
}
exit $LASTEXITCODE
