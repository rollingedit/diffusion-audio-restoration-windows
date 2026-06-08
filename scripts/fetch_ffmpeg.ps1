param(
    [string]$ReleaseApi = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest",
    [string]$OutDir = "bin",
    [string]$CacheDir = ".local_downloads\ffmpeg",
    [switch]$AllowShared
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$OutputDir = Join-Path $AppRoot $OutDir
$DownloadDir = Join-Path $AppRoot $CacheDir

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null

$headers = @{ "User-Agent" = "RollingEdit-A2SB-Restorer-release-setup" }
$release = Invoke-RestMethod -Uri $ReleaseApi -Headers $headers
$assets = @($release.assets)

$candidates = @(
    $assets | Where-Object {
        $_.name -match "win64-lgpl.*\.zip$" -and
        $_.name -notmatch "nonfree" -and
        ($AllowShared -or $_.name -notmatch "shared")
    }
)

if (-not $candidates -and -not $AllowShared) {
    throw "No non-shared win64 LGPL FFmpeg ZIP asset was found. Rerun with -AllowShared only after installer DLL bundling has been reviewed."
}
if (-not $candidates) {
    throw "No win64 LGPL FFmpeg ZIP asset was found in $ReleaseApi."
}

$asset = $candidates | Sort-Object name | Select-Object -First 1
$zipPath = Join-Path $DownloadDir $asset.name
$extractDir = Join-Path $DownloadDir ([IO.Path]::GetFileNameWithoutExtension($asset.name))

Write-Host "Downloading $($asset.browser_download_url)"
Invoke-WebRequest -Uri $asset.browser_download_url -Headers $headers -OutFile $zipPath

if (Test-Path $extractDir) {
    Remove-Item -LiteralPath $extractDir -Recurse -Force
}
Expand-Archive -Path $zipPath -DestinationPath $extractDir

$ffmpeg = Get-ChildItem -Path $extractDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
$ffprobe = Get-ChildItem -Path $extractDir -Recurse -Filter "ffprobe.exe" | Select-Object -First 1

if (-not $ffmpeg) {
    throw "Downloaded FFmpeg ZIP did not contain ffmpeg.exe."
}
if (-not $ffprobe) {
    throw "Downloaded FFmpeg ZIP did not contain ffprobe.exe."
}

Copy-Item -Force -Path $ffmpeg.FullName -Destination (Join-Path $OutputDir "ffmpeg.exe")
Copy-Item -Force -Path $ffprobe.FullName -Destination (Join-Path $OutputDir "ffprobe.exe")

foreach ($exe in @("ffmpeg.exe", "ffprobe.exe")) {
    $path = Join-Path $OutputDir $exe
    $bytes = [IO.File]::ReadAllBytes($path)
    if ($bytes.Length -lt 2 -or $bytes[0] -ne 0x4d -or $bytes[1] -ne 0x5a) {
        throw "$exe is not a Windows executable."
    }
}

$manifest = [ordered]@{
    source = "BtbN FFmpeg Builds"
    release_api = $ReleaseApi
    asset = $asset.name
    url = $asset.browser_download_url
    output_dir = $OutDir
    ffmpeg = "bin/ffmpeg.exe"
    ffprobe = "bin/ffprobe.exe"
}
$manifestPath = Join-Path $OutputDir "ffmpeg-manifest.json"
$manifest | ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 -Path $manifestPath

Write-Host "Wrote $manifestPath"
