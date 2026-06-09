param(
    [switch]$Repair,
    [switch]$DryRun,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

function New-Status {
    param(
        [bool]$Ok,
        [string]$Step,
        [string]$Message,
        [hashtable]$Details = @{}
    )

    [ordered]@{
        ok = $Ok
        step = $Step
        message = $Message
        details = $Details
    }
}

function Write-Status {
    param([object]$Status)

    if ($Json) {
        $Status | ConvertTo-Json -Depth 8
    } else {
        $prefix = if ($Status.ok) { "OK" } else { "FAIL" }
        Write-Host "[$prefix] $($Status.step): $($Status.message)"
    }
}

function Write-SetupProgress {
    param(
        [int]$Percent,
        [string]$Activity,
        [string]$Status
    )

    if (-not $Json) {
        Write-Progress -Activity $Activity -Status $Status -PercentComplete $Percent
        Write-Host "[SETUP] $Status"
    }
}

function Install-PrivatePython310 {
    param(
        [string]$InstallDir,
        [string]$DownloadsDir
    )

    $PythonVersion = "3.10.11"
    $InstallerUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
    $InstallerPath = Join-Path $DownloadsDir "python-$PythonVersion-amd64.exe"
    $InstallerLog = Join-Path $DownloadsDir "python-$PythonVersion-install.log"
    $InstalledPython = Join-Path $InstallDir "python.exe"

    if (Test-Path $InstalledPython) {
        return $InstalledPython
    }

    New-Item -ItemType Directory -Force -Path $DownloadsDir | Out-Null
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

    if (-not (Test-Path $InstallerPath)) {
        Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath
    }

    $signature = Get-AuthenticodeSignature -FilePath $InstallerPath
    if ($signature.Status -ne "Valid") {
        throw "Downloaded Python installer signature is not valid: $($signature.Status)."
    }

    $installArgs = "/quiet InstallAllUsers=0 TargetDir=`"$InstallDir`" Include_launcher=0 InstallLauncherAllUsers=0 PrependPath=0 AssociateFiles=0 Shortcuts=0 Include_pip=1 Include_test=0 SimpleInstall=1 /log `"$InstallerLog`""
    $process = Start-Process -FilePath $InstallerPath -ArgumentList $installArgs -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "Private Python 3.10 installer exited with code $($process.ExitCode)."
    }
    if (-not (Test-Path $InstalledPython)) {
        throw "Private Python 3.10 install did not produce $InstalledPython."
    }

    return $InstalledPython
}

function Install-VcRedist {
    param([string]$DownloadsDir)

    $InstallerUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    $InstallerPath = Join-Path $DownloadsDir "vc_redist.x64.exe"
    $InstallerLog = Join-Path $DownloadsDir "vc_redist.x64-install.log"

    New-Item -ItemType Directory -Force -Path $DownloadsDir | Out-Null
    if (-not (Test-Path $InstallerPath)) {
        Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath
    }

    $signature = Get-AuthenticodeSignature -FilePath $InstallerPath
    if ($signature.Status -ne "Valid") {
        throw "Downloaded Microsoft Visual C++ Redistributable signature is not valid: $($signature.Status)."
    }

    $installArgs = "/install /quiet /norestart /log `"$InstallerLog`""
    $process = Start-Process -FilePath $InstallerPath -ArgumentList $installArgs -Wait -PassThru
    if (($process.ExitCode -ne 0) -and ($process.ExitCode -ne 3010)) {
        throw "Microsoft Visual C++ Redistributable installer exited with code $($process.ExitCode)."
    }

    return $process.ExitCode
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$DefaultDataDir = Join-Path $AppRoot ".local_app_data\A2SB Restorer"
$DefaultDownloadsDir = Join-Path $AppRoot ".local_downloads"
$DefaultHfHome = Join-Path $DefaultDownloadsDir "huggingface-cache"
if (-not $env:ROLLING_A2SB_DATA_DIR) { $env:ROLLING_A2SB_DATA_DIR = $DefaultDataDir }
if (-not $env:ROLLING_A2SB_LOG_DIR) { $env:ROLLING_A2SB_LOG_DIR = Join-Path $DefaultDataDir "Logs" }
if (-not $env:PIP_CACHE_DIR) { $env:PIP_CACHE_DIR = Join-Path $DefaultDownloadsDir "pip-cache" }
if (-not $env:HF_HOME) { $env:HF_HOME = $DefaultHfHome }
if (-not $env:HUGGINGFACE_HUB_CACHE) { $env:HUGGINGFACE_HUB_CACHE = Join-Path $DefaultHfHome "hub" }
if (-not $env:TORCH_HOME) { $env:TORCH_HOME = Join-Path $DefaultDownloadsDir "torch-cache" }
$Runtime = Join-Path $AppRoot "runtime"
$PrivatePython310 = Join-Path $AppRoot "python310"
$Python = Join-Path $Runtime "Scripts\python.exe"
$Requirements = Join-Path $AppRoot "requirements\win-cu121.txt"
$LockRequirements = Join-Path $AppRoot "requirements\lock-win-cu121.txt"
$GuiRequirements = Join-Path $AppRoot "requirements\gui.txt"
$SetupStatus = Join-Path $Runtime "setup-status.json"
$FilteredRequirements = Join-Path $Runtime "requirements-no-ssr-eval.txt"

$steps = New-Object System.Collections.Generic.List[object]

try {
    Write-SetupProgress 5 "A2SB Restorer setup" "Preparing install paths"
    $steps.Add((New-Status $true "paths" "Resolved app paths." @{
        app_root = $AppRoot.Path
        runtime = $Runtime
        python = $Python
    }))

    if ($DryRun) {
        $steps.Add((New-Status $true "dry_run" "Dry run requested; no runtime changes were made." @{}))
        $result = [ordered]@{ ok = $true; dry_run = $true; repair = [bool]$Repair; steps = $steps }
        if ($Json) { $result | ConvertTo-Json -Depth 8 } else { foreach ($step in $steps) { Write-Status $step } }
        exit 0
    }

    if ($Repair -and (Test-Path $Runtime)) {
        $steps.Add((New-Status $true "repair" "Repair requested; existing runtime will be reused and dependencies refreshed." @{}))
    }

    if (-not (Test-Path $Python)) {
        Write-SetupProgress 15 "A2SB Restorer setup" "Creating private Python runtime"
        Write-SetupProgress 15 "A2SB Restorer setup" "Installing private Python 3.10 bootstrap"
        $Python310 = Install-PrivatePython310 -InstallDir $PrivatePython310 -DownloadsDir $DefaultDownloadsDir
        & $Python310 -m venv $Runtime
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create Python 3.10 virtual environment at $Runtime."
        }
        $steps.Add((New-Status $true "venv" "Created private Python runtime." @{}))
    } else {
        Write-SetupProgress 15 "A2SB Restorer setup" "Private Python runtime already exists"
        $steps.Add((New-Status $true "venv" "Private Python runtime already exists." @{}))
    }

    Write-SetupProgress 25 "A2SB Restorer setup" "Installing Microsoft Visual C++ runtime"
    $vcRedistExit = Install-VcRedist -DownloadsDir $DefaultDownloadsDir
    $steps.Add((New-Status $true "vc_redist" "Installed or repaired Microsoft Visual C++ Redistributable." @{ exit_code = $vcRedistExit }))

    Write-SetupProgress 30 "A2SB Restorer setup" "Upgrading pip tooling"
    & $Python -m pip install --upgrade pip "setuptools<81" wheel
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip tooling."
    }
    $steps.Add((New-Status $true "pip" "Upgraded pip, setuptools, and wheel." @{}))

    $RuntimeRequirements = if (Test-Path $LockRequirements) { $LockRequirements } else { $Requirements }
    New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
    $runtimeRequirementLines = Get-Content $RuntimeRequirements | Where-Object { $_ -notmatch '^\s*ssr-eval==' }
    $runtimeRequirementLines | Set-Content -Encoding UTF8 -Path $FilteredRequirements
    Write-SetupProgress 45 "A2SB Restorer setup" "Installing CUDA and ML runtime packages"
    & $Python -m pip install -r $FilteredRequirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install CUDA runtime requirements."
    }
    Write-SetupProgress 65 "A2SB Restorer setup" "Installing Windows-safe evaluation dependency"
    & $Python -m pip install --no-deps ssr-eval==0.0.7
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install ssr-eval without broken Windows transitive dependencies."
    }
    $steps.Add((New-Status $true "requirements" "Installed CUDA runtime requirements." @{ requirements = $RuntimeRequirements; filtered_requirements = $FilteredRequirements; lockfile_used = (Test-Path $LockRequirements); ssr_eval_no_deps = $true }))

    Write-SetupProgress 75 "A2SB Restorer setup" "Installing GUI packages"
    & $Python -m pip install -r $GuiRequirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install GUI requirements."
    }
    $steps.Add((New-Status $true "gui_requirements" "Installed GUI requirements." @{ requirements = $GuiRequirements }))

    Write-SetupProgress 85 "A2SB Restorer setup" "Registering A2SB Restorer package"
    & $Python -m pip install -e $AppRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install RollingEdit A2SB package."
    }
    $steps.Add((New-Status $true "package" "Installed RollingEdit A2SB package in editable mode." @{}))

    Write-SetupProgress 95 "A2SB Restorer setup" "Checking runtime readiness"
    $doctorJson = & $Python -m rolling_a2sb.cli doctor --json
    $doctorExit = $LASTEXITCODE
    $doctorText = ($doctorJson -join "`n")
    $doctorJsonStart = $doctorText.IndexOf("{")
    if ($doctorJsonStart -lt 0) {
        throw "Doctor did not produce JSON output."
    }
    $doctor = $doctorText.Substring($doctorJsonStart) | ConvertFrom-Json
    $steps.Add((New-Status ($doctorExit -eq 0) "doctor" "Runtime doctor completed." @{
        doctor_ok = [bool]$doctor.ok
        torch_ok = [bool]$doctor.torch.ok
        checkpoints_ok = [bool]$doctor.checkpoints.ok
    }))

    New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
    $result = [ordered]@{
        ok = $true
        readiness_ok = ($doctorExit -eq 0)
        dry_run = $false
        repair = [bool]$Repair
        steps = $steps
    }
    $result | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -Path $SetupStatus

    if ($Json) { $result | ConvertTo-Json -Depth 8 } else { foreach ($step in $steps) { Write-Status $step } }
    if (-not $Json) { Write-Progress -Activity "A2SB Restorer setup" -Completed }
    exit 0
} catch {
    $steps.Add((New-Status $false "error" $_.Exception.Message @{}))
    $result = [ordered]@{ ok = $false; dry_run = [bool]$DryRun; repair = [bool]$Repair; steps = $steps }
    New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
    $result | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -Path $SetupStatus
    if ($Json) { $result | ConvertTo-Json -Depth 8 } else { foreach ($step in $steps) { Write-Status $step } }
    if (-not $Json) { Write-Progress -Activity "A2SB Restorer setup" -Completed }
    exit 1
}
