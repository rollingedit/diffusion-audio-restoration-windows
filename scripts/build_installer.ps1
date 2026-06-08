param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$Iss = Join-Path $AppRoot "installer\a2sb-restorer.iss"
$LauncherExe = Join-Path $AppRoot "dist\A2SB Restorer\A2SB Restorer.exe"
$FfmpegExe = Join-Path $AppRoot "bin\ffmpeg.exe"
$FfprobeExe = Join-Path $AppRoot "bin\ffprobe.exe"

if ($DryRun) {
    Write-Host "Would build installer from $Iss"
    Write-Host "Requires launcher output: $LauncherExe"
    Write-Host "Requires FFmpeg: $FfmpegExe"
    Write-Host "Requires ffprobe: $FfprobeExe"
    exit 0
}

if (-not (Test-Path $Iss)) {
    throw "Inno Setup script missing: $Iss"
}
if (-not (Test-Path $LauncherExe)) {
    throw "Launcher EXE missing: $LauncherExe. Run scripts\build_launcher.ps1 first."
}
if (-not (Test-Path $FfmpegExe)) {
    throw "FFmpeg binary missing: $FfmpegExe. Bundle the approved redistributable ffmpeg.exe before building the installer."
}
if (-not (Test-Path $FfprobeExe)) {
    throw "ffprobe binary missing: $FfprobeExe. Bundle the approved redistributable ffprobe.exe before building the installer."
}

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    throw "ISCC.exe was not found. Install Inno Setup before building the installer."
}

& $iscc.Source $Iss
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& (Join-Path $ScriptDir "write_sha256sums.ps1") -ArtifactsDir "dist\installer"
exit $LASTEXITCODE
