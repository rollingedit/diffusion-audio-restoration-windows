param(
    [string]$ArtifactsDir = "dist\installer",
    [string]$Output = "SHA256SUMS.txt",
    [switch]$ValidateOnly
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

$ArtifactsPath = Join-Path $AppRoot $ArtifactsDir
$OutputPath = Join-Path $ArtifactsPath $Output
$LicensesPath = Join-Path $AppRoot "LICENSES"
$ValidateOnlyPython = if ($ValidateOnly) { "True" } else { "False" }

$script = @"
from pathlib import Path
from rolling_a2sb.release import collect_release_artifacts, validate_release_artifacts, write_sha256sums

artifacts_dir = Path(r'''$ArtifactsPath''')
licenses_dir = Path(r'''$LicensesPath''')
output_path = Path(r'''$OutputPath''')
artifacts = collect_release_artifacts(artifacts_dir)
if not $($ValidateOnlyPython):
    write_sha256sums(artifacts, output_path)
result = validate_release_artifacts(artifacts_dir, licenses_dir)
for error in result.errors:
    print(error)
raise SystemExit(0 if result.ok else 1)
"@

& $Python -c $script
exit $LASTEXITCODE
