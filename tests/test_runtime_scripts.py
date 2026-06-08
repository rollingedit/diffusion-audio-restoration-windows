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


def test_repair_runtime_delegates_to_setup_runtime_repair_mode() -> None:
    text = (ROOT / "scripts" / "repair_runtime.ps1").read_text(encoding="utf-8")

    assert 'setup_runtime.ps1") -Repair:$true' in text
    assert "-DryRun:$DryRun" in text
    assert "-Json:$Json" in text
