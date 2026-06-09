param(
    [string]$InstallerPath = "dist\installer\A2SB-Restorer-Setup.exe",
    [string]$InstallDir,
    [string]$AppDataDir,
    [string]$PipCacheDir,
    [string]$HfHome,
    [string]$HfHubCache,
    [string]$TorchHome,
    [string]$EvidenceDir = "evidence\installed-app",
    [Alias("Input")]
    [string]$InputPath,
    [Alias("Output")]
    [string]$OutputPath,
    [string]$CheckpointFolder,
    [switch]$TrustManualCheckpoints,
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$RequireDoctorPass
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
if (-not $InstallDir) { $InstallDir = Join-Path $AppRoot ".local_app_install\A2SB Restorer" }
if (-not $AppDataDir) { $AppDataDir = Join-Path $AppRoot ".local_app_data\A2SB Restorer" }
if (-not $PipCacheDir) { $PipCacheDir = Join-Path $AppRoot ".local_downloads\pip-cache" }
if (-not $HfHome) { $HfHome = Join-Path $AppRoot ".local_downloads\huggingface-cache" }
if (-not $HfHubCache) { $HfHubCache = Join-Path $HfHome "hub" }
if (-not $TorchHome) { $TorchHome = Join-Path $AppRoot ".local_downloads\torch-cache" }

$env:ROLLING_A2SB_DATA_DIR = $AppDataDir
$env:PIP_CACHE_DIR = $PipCacheDir
$env:HF_HOME = $HfHome
$env:HUGGINGFACE_HUB_CACHE = $HfHubCache
$env:TORCH_HOME = $TorchHome

if ([System.IO.Path]::IsPathRooted($InstallerPath)) {
    $Installer = $InstallerPath
} else {
    $Installer = Join-Path $AppRoot $InstallerPath
}
if ([System.IO.Path]::IsPathRooted($EvidenceDir)) {
    $EvidencePath = $EvidenceDir
} else {
    $EvidencePath = Join-Path $AppRoot $EvidenceDir
}
$SummaryPath = Join-Path $EvidencePath "installed_app_smoke.json"
$InstallLog = Join-Path $EvidencePath "install.log"
$DoctorJson = Join-Path $EvidencePath "installed_doctor.json"
$RestoreLog = Join-Path $EvidencePath "installed_restore.log"
$UninstallLog = Join-Path $EvidencePath "uninstall.log"

New-Item -ItemType Directory -Force -Path $EvidencePath | Out-Null
New-Item -ItemType Directory -Force -Path $AppDataDir, $PipCacheDir, $HfHome, $HfHubCache, $TorchHome | Out-Null

$summary = [ordered]@{
    ok = $false
    installed = $false
    install_dir = $InstallDir
    installer = $Installer
    install_exit = $null
    doctor_exit = $null
    restore_exit = $null
    uninstall_exit = $null
    required_files = @()
    missing_files = @()
    local_paths = [ordered]@{
        app_data_dir = $AppDataDir
        pip_cache_dir = $PipCacheDir
        hf_home = $HfHome
        hf_hub_cache = $HfHubCache
        torch_home = $TorchHome
    }
    evidence = [ordered]@{
        summary = $SummaryPath
        install_log = $InstallLog
        doctor_json = $DoctorJson
        restore_log = $RestoreLog
        uninstall_log = $UninstallLog
    }
}

function Save-Summary {
    param([object]$Data)
    $Data | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -Path $SummaryPath
}

function Resolve-SmokeInput {
    param([string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return (Resolve-Path (Join-Path $AppRoot $Path)).Path
}

function Resolve-SmokeOutput {
    param([string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return (Join-Path $AppRoot $Path)
}

try {
    if ($Install) {
        if (-not (Test-Path $Installer)) {
            throw "Installer artifact missing: $Installer"
        }
        $installArgs = @(
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/CLOSEAPPLICATIONS",
            "/FORCECLOSEAPPLICATIONS",
            "/NORESTART",
            "/SP-",
            "/DIR=""$InstallDir""",
            "/LOG=$InstallLog"
        )
        $installProcess = Start-Process -FilePath $Installer -ArgumentList $installArgs -Wait -PassThru -WindowStyle Hidden
        $summary.install_exit = $installProcess.ExitCode
        if ($installProcess.ExitCode -ne 0) {
            throw "Installer exited with code $($installProcess.ExitCode)."
        }
    }

    $requiredFiles = @(
        "A2SB Restorer.exe",
        "scripts\doctor.ps1",
        "scripts\setup_runtime.ps1",
        "scripts\repair_runtime.ps1",
        "scripts\smoke_restore.ps1",
        "bin\ffmpeg.exe",
        "bin\ffprobe.exe",
        "README-WINDOWS.md",
        "LICENSE-NOTICES.txt"
    )
    $summary.required_files = $requiredFiles
    $missing = @()
    foreach ($relative in $requiredFiles) {
        $path = Join-Path $InstallDir $relative
        if (-not (Test-Path $path)) {
            $missing += $relative
        }
    }
    $summary.missing_files = $missing
    if ($missing.Count -gt 0) {
        throw "Installed app is missing required files: $($missing -join ', ')"
    }
    $summary.installed = $true

    $shouldRunDoctor = (-not $Uninstall) -or $RequireDoctorPass -or [bool]$InputPath
    if ($shouldRunDoctor) {
        $doctor = Join-Path $InstallDir "scripts\doctor.ps1"
        & powershell -ExecutionPolicy Bypass -File $doctor -Json *> $DoctorJson
        $summary.doctor_exit = $LASTEXITCODE
        if ($RequireDoctorPass -and $LASTEXITCODE -ne 0) {
            throw "Installed doctor failed with code $LASTEXITCODE."
        }
    }

    if ($InputPath) {
        $smoke = Join-Path $InstallDir "scripts\smoke_restore.ps1"
        $resolvedInput = Resolve-SmokeInput $InputPath
        $smokeArgs = @("-Input", $resolvedInput)
        if ($OutputPath) { $smokeArgs += @("-Output", (Resolve-SmokeOutput $OutputPath)) }
        if ($CheckpointFolder) { $smokeArgs += @("-CheckpointFolder", $CheckpointFolder) }
        if ($TrustManualCheckpoints) { $smokeArgs += @("-TrustManualCheckpoints") }
        & powershell -ExecutionPolicy Bypass -File $smoke @smokeArgs *> $RestoreLog
        $summary.restore_exit = $LASTEXITCODE
        if ($LASTEXITCODE -ne 0) {
            throw "Installed restore smoke failed with code $LASTEXITCODE."
        }
    }

    if ($Uninstall) {
        $uninstaller = Get-ChildItem -Path $InstallDir -Filter "unins*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $uninstaller) {
            throw "Uninstaller was not found under $InstallDir."
        }
        $uninstallArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=$UninstallLog")
        $uninstallProcess = Start-Process -FilePath $uninstaller.FullName -ArgumentList $uninstallArgs -Wait -PassThru -WindowStyle Hidden
        $summary.uninstall_exit = $uninstallProcess.ExitCode
        if ($uninstallProcess.ExitCode -ne 0) {
            throw "Uninstaller exited with code $($uninstallProcess.ExitCode)."
        }
    }

    $summary.ok = $true
    Save-Summary $summary
    Write-Host "Wrote $SummaryPath"
    exit 0
} catch {
    $summary.error = $_.Exception.Message
    Save-Summary $summary
    Write-Host "Wrote $SummaryPath"
    Write-Error $_.Exception.Message
    exit 1
}
