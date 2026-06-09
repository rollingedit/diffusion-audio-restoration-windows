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

function Find-Python310 {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & py -3.10 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return "py"
        }
    }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"),
        (Join-Path $env:ProgramFiles "Python310\python.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Python310\python.exe")
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    return $null
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$Runtime = Join-Path $AppRoot "runtime"
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
        $Python310 = Find-Python310
        if (-not $Python310) {
            throw "Python 3.10 x64 was not found. Install Python 3.10 x64 or use the packaged runtime."
        }
        if ($Python310 -eq "py") {
            & py -3.10 -m venv $Runtime
        } else {
            & $Python310 -m venv $Runtime
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create Python 3.10 virtual environment at $Runtime."
        }
        $steps.Add((New-Status $true "venv" "Created private Python runtime." @{}))
    } else {
        Write-SetupProgress 15 "A2SB Restorer setup" "Private Python runtime already exists"
        $steps.Add((New-Status $true "venv" "Private Python runtime already exists." @{}))
    }

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
    $doctor = $doctorJson | ConvertFrom-Json
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
