param(
    [switch]$Json
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

if ($Json) {
    & $Python -m rolling_a2sb.cli doctor --json
} else {
    & $Python -m rolling_a2sb.cli doctor
}
exit $LASTEXITCODE

