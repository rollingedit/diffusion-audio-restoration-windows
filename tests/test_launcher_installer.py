from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_launcher_uses_runtime_python_and_app_module() -> None:
    text = (ROOT / "launcher" / "launcher.py").read_text(encoding="utf-8")

    assert "runtime" in text
    assert "rolling_a2sb.app" in text
    assert "shell=False" in text


def test_inno_installer_is_per_user_and_has_shortcuts() -> None:
    text = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")

    assert "PrivilegesRequired=lowest" in text
    assert "A2SB Restorer" in text
    assert "A2SB Doctor" in text
    assert "Repair Runtime" in text
    assert "Open Models Folder" in text
    assert "Open Logs Folder" in text


def test_inno_installer_does_not_include_checkpoint_patterns() -> None:
    text = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")

    assert "*.ckpt" not in text
    assert "models\\*" not in text

