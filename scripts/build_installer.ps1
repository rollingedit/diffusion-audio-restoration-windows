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
$InstallerIcon = Join-Path $AppRoot "installer\assets\app.ico"
$ArtifactsDir = Join-Path $AppRoot "dist\installer"
$Readme = Join-Path $AppRoot "README-WINDOWS.md"
$Notices = Join-Path $AppRoot "LICENSE-NOTICES.txt"

if ($DryRun) {
    Write-Host "Would build installer from $Iss"
    Write-Host "Requires launcher output: $LauncherExe"
    Write-Host "Requires FFmpeg: $FfmpegExe"
    Write-Host "Requires ffprobe: $FfprobeExe"
    Write-Host "Requires installer icon: $InstallerIcon"
    Write-Host "Would stage release docs into: $ArtifactsDir"
    exit 0
}

if (-not (Test-Path $Iss)) {
    throw "Inno Setup script missing: $Iss"
}
if (-not (Test-Path $LauncherExe)) {
    throw "Launcher EXE missing: $LauncherExe. Run scripts\build_launcher.ps1 first."
}
if (-not (Test-Path $FfmpegExe)) {
    throw "FFmpeg binary missing: $FfmpegExe. Run scripts\fetch_ffmpeg.ps1 to bundle the approved redistributable ffmpeg.exe before building the installer."
}
if (-not (Test-Path $FfprobeExe)) {
    throw "ffprobe binary missing: $FfprobeExe. Run scripts\fetch_ffmpeg.ps1 to bundle the approved redistributable ffprobe.exe before building the installer."
}
if (-not (Test-Path $InstallerIcon)) {
    throw "Installer icon missing: $InstallerIcon. Run scripts\generate_icon.ps1 before building the installer."
}
if (-not (Test-Path $Readme)) {
    throw "Windows README missing: $Readme"
}
if (-not (Test-Path $Notices)) {
    throw "License notices missing: $Notices"
}

$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $LocalInno = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
    $ProgramFilesInno = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
    if (Test-Path $LocalInno) {
        $iscc = $LocalInno
    } elseif (Test-Path $ProgramFilesInno) {
        $iscc = $ProgramFilesInno
    }
}
if (-not $iscc) {
    throw "ISCC.exe was not found. Install Inno Setup before building the installer."
}

& $iscc $Iss
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null
Copy-Item -Force -Path $Readme -Destination (Join-Path $ArtifactsDir "README-WINDOWS.md")
Copy-Item -Force -Path $Notices -Destination (Join-Path $ArtifactsDir "LICENSE-NOTICES.txt")

& (Join-Path $ScriptDir "write_sha256sums.ps1") -ArtifactsDir "dist\installer" -GenerateOnly
exit $LASTEXITCODE
