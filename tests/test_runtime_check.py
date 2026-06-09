import sys
from types import SimpleNamespace

from rolling_a2sb.runtime_check import (
    add_next_actions,
    check_app,
    check_ffmpeg,
    check_imports,
    check_python,
    check_torch_cuda,
    diagnostic_text,
    readiness_summary,
)
from rolling_a2sb import __version__
from rolling_a2sb.settings import save_settings, AppSettings


def test_check_app_reports_version_and_paths() -> None:
    result = check_app()

    assert result["ok"] is True
    assert result["name"] == "A2SB Restorer"
    assert result["version"] == __version__
    assert result["install_dir"]
    assert result["data_dir"]
    assert result["logs_dir"]


def test_check_python_reports_supported_dev_python() -> None:
    result = check_python()

    assert result["version"].count(".") == 2
    assert result["executable"] == sys.executable


def test_check_imports_has_group_ok() -> None:
    result = check_imports(["json"])

    assert result["ok"] is True
    assert result["modules"]["json"]["ok"] is True


def test_check_imports_reports_missing_module() -> None:
    result = check_imports(["definitely_missing_a2sb_module"])

    assert result["ok"] is False
    assert result["modules"]["definitely_missing_a2sb_module"]["ok"] is False


def test_check_torch_cuda_reports_cuda_false(monkeypatch) -> None:
    fake_torch = SimpleNamespace(
        __version__="2.2.2+cu121",
        version=SimpleNamespace(cuda="12.1"),
        cuda=SimpleNamespace(is_available=lambda: False),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    result = check_torch_cuda()

    assert result["ok"] is False
    assert result["cuda_available"] is False
    assert result["cuda_version"] == "12.1"


def test_check_ffmpeg_reports_missing_binary(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("rolling_a2sb.runtime_check.paths.ffmpeg_path", lambda: tmp_path / "bin" / "ffmpeg.exe")
    monkeypatch.setattr("rolling_a2sb.runtime_check.shutil.which", lambda name: None)

    result = check_ffmpeg()

    assert result["ok"] is False
    assert result["path"].endswith("ffmpeg.exe")


def test_diagnostic_text_includes_missing_checkpoints() -> None:
    report = {
        "ok": False,
        "app": {"ok": True, "version": "0.1.0a0"},
        "python": {"ok": True},
        "checkpoints": {"ok": False, "missing": ["a.ckpt", "b.ckpt"]},
    }

    text = diagnostic_text(report)

    assert "overall: not ready" in text
    assert "app_version: 0.1.0a0" in text
    assert "checkpoints: needs attention" in text
    assert "missing: a.ckpt, b.ckpt" in text


def test_readiness_summary_reports_key_statuses() -> None:
    report = {
        "ok": False,
        "app": {"ok": True},
        "python": {"ok": True},
        "torch": {"ok": False, "cuda_available": False},
        "nvidia_smi": {"ok": True},
        "ffmpeg": {"ok": True},
        "ffprobe": {"ok": True},
        "checkpoints": {"ok": False},
        "write_permissions": {"ok": True},
    }

    summary = readiness_summary(report)

    assert summary["overall"] == "not ready"
    assert summary["app"] == "ok"
    assert summary["python"] == "ok"
    assert summary["cuda"] == "needs attention"
    assert summary["gpu"] == "ok"
    assert summary["checkpoints"] == "needs attention"
    assert summary["write_permissions"] == "ok"


def test_diagnostic_text_includes_readiness_summary() -> None:
    report = {
        "ok": False,
        "app": {"ok": True},
        "python": {"ok": True},
        "torch": {"ok": False, "cuda_available": False},
        "nvidia_smi": {"ok": False},
        "ffmpeg": {"ok": True},
        "ffprobe": {"ok": True},
        "checkpoints": {"ok": False, "missing": ["a.ckpt"]},
        "write_permissions": {"ok": True},
    }

    text = diagnostic_text(report)

    assert "readiness:" in text
    assert "  python: ok" in text
    assert "  cuda: needs attention" in text
    assert "  checkpoints: needs attention" in text


def test_next_actions_added_to_failed_checks() -> None:
    checks = add_next_actions({"torch": {"ok": False, "error": "missing"}})

    assert "Repair Runtime" in checks["torch"]["next_action"]


def test_checkpoints_ignore_missing_saved_folder_for_default_models(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(data_dir))
    save_settings(AppSettings(checkpoint_folder=str(tmp_path / "missing-c-drive-models")))

    called = {}

    def fake_validate(folder, **kwargs):
        called["folder"] = folder
        return SimpleNamespace(ok=True, mode="twosplit", files=[], missing=[], errors=[])

    monkeypatch.setattr("rolling_a2sb.runtime_check.validate_checkpoint_folder", fake_validate)

    from rolling_a2sb.runtime_check import check_checkpoints

    result = check_checkpoints()

    assert called["folder"] == data_dir.resolve() / "models"
    assert result["ok"] is True
    assert result["ignored_saved_folder"].endswith("missing-c-drive-models")


def test_diagnostic_text_includes_next_action() -> None:
    report = {
        "ok": False,
        "torch": {
            "ok": False,
            "error": "No module named 'torch'",
            "next_action": "Run Repair Runtime.",
        },
    }

    text = diagnostic_text(report)

    assert "next: Run Repair Runtime." in text
