from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gui_exposes_restore_controls_and_shared_actions() -> None:
    text = (ROOT / "rolling_a2sb" / "gui.py").read_text(encoding="utf-8")

    assert "QTabWidget" in text
    assert "Plan Restore" in text
    assert "QThread" in text
    assert "RestoreThread" in text
    assert "execute_restore_text" in text
    assert "Open Output Folder" in text
    assert "start_restore" in text
    assert "Download Recommended Model" in text
    assert "confirm_and_download_model" in text
    assert "build_logs_tab" in text
    assert "build_about_tab" in text
    assert "about_text" in text
    assert "Show Latest Log" in text
    assert "latest_restore_log_text" in text
    assert "prepare_restore_dry_run" in text
    assert "audio_probe_text" in text
    assert "setAcceptDrops(True)" in text
    assert "SUPPORTED_AUDIO_EXTENSIONS" in text
