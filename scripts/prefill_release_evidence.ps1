param(
    [string]$FactsPath = "evidence\release_build_facts.json",
    [string]$EvidencePath = "docs\RELEASE_EVIDENCE.md"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")

function Resolve-AppPath {
    param([string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return (Join-Path $AppRoot $Path)
}

function Set-EvidenceField {
    param(
        [string]$Text,
        [string]$Field,
        [object]$Value
    )
    if ($null -eq $Value) {
        return $Text
    }
    $stringValue = ([string]$Value).Trim()
    if (-not $stringValue) {
        return $Text
    }
    $escaped = [regex]::Escape($Field)
    return [regex]::Replace(
        $Text,
        "(?m)^- ${escaped}:[ \t]*.*$",
        "- ${Field}: $stringValue"
    )
}

$factsFile = Resolve-AppPath $FactsPath
$evidenceFile = Resolve-AppPath $EvidencePath
if (-not (Test-Path $factsFile)) {
    throw "Release build facts file is missing: $factsFile"
}
if (-not (Test-Path $evidenceFile)) {
    throw "Release evidence file is missing: $evidenceFile"
}

$facts = Get-Content $factsFile -Raw | ConvertFrom-Json
$text = Get-Content $evidenceFile -Raw

$fieldMap = [ordered]@{
    "Version" = $facts.version
    "Git commit" = $facts.git_commit
    "Build machine" = $facts.build_machine
    "Test machine" = $facts.test_machine
    "Windows version" = $facts.windows_version
    "GPU model" = $facts.gpu_model
    "NVIDIA driver version" = $facts.nvidia_driver_version
    "CUDA reported by PyTorch" = $facts.cuda_reported_by_pytorch
    "Installer filename" = $facts.installer_filename
    "Installer SHA256" = $facts.installer_sha256
    "FFmpeg build filename" = $facts.ffmpeg_build_filename
    "FFmpeg source URL" = $facts.ffmpeg_source_url
    "FFmpeg manifest path" = $facts.ffmpeg_manifest_path
    "FFmpeg SHA256" = $facts.ffmpeg_sha256
    "ffprobe SHA256" = $facts.ffprobe_sha256
    "Installer artifact folder" = if ($facts.installer_filename) { "dist/installer" } else { $null }
}

foreach ($entry in $fieldMap.GetEnumerator()) {
    $text = Set-EvidenceField -Text $text -Field $entry.Key -Value $entry.Value
}

[System.IO.File]::WriteAllText($evidenceFile, $text, [System.Text.UTF8Encoding]::new($false))
Write-Host "Prefilled factual release evidence in $evidenceFile"
Write-Host "Smoke-test commands, pass/fail results, hashes for test audio, screenshots, and blockers still require real release-candidate evidence."
