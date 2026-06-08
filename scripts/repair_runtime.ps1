param(
    [switch]$DryRun,
    [switch]$Json
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $ScriptDir "setup_runtime.ps1") -Repair:$true -DryRun:$DryRun -Json:$Json
exit $LASTEXITCODE

