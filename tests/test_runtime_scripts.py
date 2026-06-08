from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_setup_runtime_uses_private_python_310_runtime() -> None:
    text = (ROOT / "scripts" / "setup_runtime.ps1").read_text(encoding="utf-8")

    assert '$Runtime = Join-Path $AppRoot "runtime"' in text
    assert '$Python = Join-Path $Runtime "Scripts\\python.exe"' in text
    assert "& py -3.10 -m venv $Runtime" in text
    assert "Python 3.10 virtual environment" in text
    assert "-m pip install -e $AppRoot" in text
    assert "setup-status.json" in text


def test_setup_runtime_checks_private_runtime_with_doctor_json() -> None:
    text = (ROOT / "scripts" / "setup_runtime.ps1").read_text(encoding="utf-8")

    assert "$doctorJson = & $Python -m rolling_a2sb.cli doctor --json" in text
    assert "torch_ok" in text
    assert "checkpoints_ok" in text
    assert "doctor_ok" in text
    assert "readiness_ok = ($doctorExit -eq 0)" in text
    assert "exit 0" in text


def test_setup_runtime_prefers_lockfile_when_available() -> None:
    text = (ROOT / "scripts" / "setup_runtime.ps1").read_text(encoding="utf-8")

    assert '$LockRequirements = Join-Path $AppRoot "requirements\\lock-win-cu121.txt"' in text
    assert "$RuntimeRequirements = if (Test-Path $LockRequirements) { $LockRequirements } else { $Requirements }" in text
    assert "& $Python -m pip install -r $RuntimeRequirements" in text
    assert "lockfile_used" in text


def test_repair_runtime_delegates_to_setup_runtime_repair_mode() -> None:
    text = (ROOT / "scripts" / "repair_runtime.ps1").read_text(encoding="utf-8")

    assert 'setup_runtime.ps1") -Repair:$true' in text
    assert "-DryRun:$DryRun" in text
    assert "-Json:$Json" in text


def test_smoke_restore_uses_short_restore_defaults_and_runtime_fallback() -> None:
    text = (ROOT / "scripts" / "smoke_restore.ps1").read_text(encoding="utf-8")

    assert "[int]$Steps = 2" in text
    assert '$RuntimePython = Join-Path $AppRoot "runtime\\Scripts\\python.exe"' in text
    assert '$DevPython = Join-Path $AppRoot ".venv\\Scripts\\python.exe"' in text
    assert '"rolling_a2sb.cli", "restore"' in text
    assert '"--steps", "$Steps"' in text
    assert 'if ($DryRun) { $args += @("--dry-run") }' in text


def test_smoke_restore_can_trust_manual_checkpoint_folder_explicitly() -> None:
    text = (ROOT / "scripts" / "smoke_restore.ps1").read_text(encoding="utf-8")

    assert "[switch]$TrustManualCheckpoints" in text
    assert 'if ($CheckpointFolder) { $args += @("--checkpoint-folder", $CheckpointFolder) }' in text
    assert 'if ($TrustManualCheckpoints) { $args += @("--trust-manual-checkpoints") }' in text


def test_write_sha256sums_can_generate_without_release_validation() -> None:
    text = (ROOT / "scripts" / "write_sha256sums.ps1").read_text(encoding="utf-8")

    assert "[switch]$GenerateOnly" in text
    assert "raise SystemExit(0)" in text
    assert "validate_release_artifacts" in text


def test_collect_release_evidence_records_build_facts_without_smoke_claims() -> None:
    text = (ROOT / "scripts" / "collect_release_evidence.ps1").read_text(encoding="utf-8")

    assert "release_build_facts.json" in text
    assert "A2SB-Restorer-Setup.exe" in text
    assert "ffmpeg-manifest.json" in text
    assert "git rev-parse HEAD" in text
    assert "nvidia-smi --query-gpu=name" in text
    assert "Restore produced a WAV" not in text
