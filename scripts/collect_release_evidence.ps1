param(
    [string]$ArtifactsDir = "dist\installer",
    [string]$Output = "evidence\release_build_facts.json"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$ArtifactsPath = Join-Path $AppRoot $ArtifactsDir
$OutputPath = Join-Path $AppRoot $Output
$InstallerPath = Join-Path $ArtifactsPath "A2SB-Restorer-Setup.exe"
$ChecksumsPath = Join-Path $ArtifactsPath "SHA256SUMS.txt"
$FfmpegManifestPath = Join-Path $AppRoot "bin\ffmpeg-manifest.json"
$InstallerScript = Join-Path $AppRoot "installer\a2sb-restorer.iss"
$RuntimePython = Join-Path $AppRoot "runtime\Scripts\python.exe"
$DevPython = Join-Path $AppRoot ".venv\Scripts\python.exe"

function Read-InnoVersion {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $null
    }
    $match = Select-String -Path $Path -Pattern '^#define MyAppVersion "([^"]+)"$' | Select-Object -First 1
    if ($match) {
        return $match.Matches[0].Groups[1].Value
    }
    return $null
}

function Get-CommandText {
    param([string]$Command)
    try {
        $output = Invoke-Expression $Command 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            return (($output | Select-Object -First 1) -as [string]).Trim()
        }
    } catch {
        return $null
    }
    return $null
}

function Get-OptionalFileHash {
    param([string]$Path)
    if (Test-Path $Path) {
        return (Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    return $null
}

$python = if (Test-Path $RuntimePython) { $RuntimePython } elseif (Test-Path $DevPython) { $DevPython } else { "python" }
$ffmpegManifest = $null
if (Test-Path $FfmpegManifestPath) {
    $ffmpegManifest = Get-Content $FfmpegManifestPath -Raw | ConvertFrom-Json
}

$os = $null
try {
    $os = Get-CimInstance Win32_OperatingSystem
} catch {
    $os = $null
}

$facts = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    repo = "rollingedit/diffusion-audio-restoration-windows"
    version = Read-InnoVersion $InstallerScript
    git_commit = Get-CommandText "git rev-parse HEAD"
    build_machine = $env:COMPUTERNAME
    windows_version = if ($os) { "$($os.Caption) $($os.Version)" } else { $null }
    gpu_model = Get-CommandText "nvidia-smi --query-gpu=name --format=csv,noheader"
    nvidia_driver_version = Get-CommandText "nvidia-smi --query-gpu=driver_version --format=csv,noheader"
    cuda_reported_by_pytorch = Get-CommandText "& '$python' -c `"import torch; print(torch.version.cuda or '')`""
    installer_filename = if (Test-Path $InstallerPath) { Split-Path -Leaf $InstallerPath } else { $null }
    installer_sha256 = Get-OptionalFileHash $InstallerPath
    sha256sums_path = if (Test-Path $ChecksumsPath) { $ChecksumsPath.Replace($AppRoot.Path + "\", "") } else { $null }
    ffmpeg_build_filename = if ($ffmpegManifest) { $ffmpegManifest.asset } else { $null }
    ffmpeg_source_url = if ($ffmpegManifest) { $ffmpegManifest.url } else { $null }
    ffmpeg_manifest_path = if (Test-Path $FfmpegManifestPath) { "bin/ffmpeg-manifest.json" } else { $null }
    ffmpeg_sha256 = if ($ffmpegManifest) { $ffmpegManifest.ffmpeg_sha256 } else { $null }
    ffprobe_sha256 = if ($ffmpegManifest) { $ffmpegManifest.ffprobe_sha256 } else { $null }
    commands = [ordered]@{
        launcher_build = "powershell -ExecutionPolicy Bypass -File scripts/build_launcher.ps1; exit 0; dist/A2SB Restorer/A2SB Restorer.exe"
        installer_build = "powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1; exit 0; dist/installer/A2SB-Restorer-Setup.exe"
        sha256_generation = "powershell -ExecutionPolicy Bypass -File scripts/write_sha256sums.ps1 -ArtifactsDir dist/installer -GenerateOnly; exit 0; dist/installer/SHA256SUMS.txt"
        release_validation = "a2sb release-check --artifacts-dir dist/installer --licenses-dir LICENSES; exit 0; evidence/release_validation.txt"
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
$facts | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -Path $OutputPath
Write-Host "Wrote $OutputPath"
