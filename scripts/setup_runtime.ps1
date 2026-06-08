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

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$Runtime = Join-Path $AppRoot "runtime"
$Python = Join-Path $Runtime "Scripts\python.exe"
$Requirements = Join-Path $AppRoot "requirements\win-cu121.txt"
$GuiRequirements = Join-Path $AppRoot "requirements\gui.txt"
$SetupStatus = Join-Path $Runtime "setup-status.json"

$steps = New-Object System.Collections.Generic.List[object]

try {
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
        $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $pyLauncher) {
            throw "Python launcher 'py' was not found. Install Python 3.10 x64 or use the packaged runtime."
        }
        & py -3.10 -m venv $Runtime
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create Python 3.10 virtual environment at $Runtime."
        }
        $steps.Add((New-Status $true "venv" "Created private Python runtime." @{}))
    } else {
        $steps.Add((New-Status $true "venv" "Private Python runtime already exists." @{}))
    }

    & $Python -m pip install --upgrade pip setuptools wheel
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip tooling."
    }
    $steps.Add((New-Status $true "pip" "Upgraded pip, setuptools, and wheel." @{}))

    & $Python -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install CUDA runtime requirements."
    }
    $steps.Add((New-Status $true "requirements" "Installed CUDA runtime requirements." @{ requirements = $Requirements }))

    & $Python -m pip install -r $GuiRequirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install GUI requirements."
    }
    $steps.Add((New-Status $true "gui_requirements" "Installed GUI requirements." @{ requirements = $GuiRequirements }))

    & $Python -m pip install -e $AppRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install RollingEdit A2SB package."
    }
    $steps.Add((New-Status $true "package" "Installed RollingEdit A2SB package in editable mode." @{}))

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
    exit 0
} catch {
    $steps.Add((New-Status $false "error" $_.Exception.Message @{}))
    $result = [ordered]@{ ok = $false; dry_run = [bool]$DryRun; repair = [bool]$Repair; steps = $steps }
    New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
    $result | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -Path $SetupStatus
    if ($Json) { $result | ConvertTo-Json -Depth 8 } else { foreach ($step in $steps) { Write-Status $step } }
    exit 1
}
