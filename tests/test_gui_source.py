from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gui_exposes_restore_controls_and_shared_actions() -> None:
    text = (ROOT / "rolling_a2sb" / "gui.py").read_text(encoding="utf-8")

    assert "QTabWidget" in text
    assert "QDialog" in text
    assert "Model Setup" in text
    assert "open_model_setup_dialog" in text
    assert "Plan Restore" in text
    assert "QThread" in text
    assert "QProgressBar" in text
    assert "RestoreThread" in text
    assert "execute_restore_text" in text
    assert "Open Output Folder" in text
    assert "Restore Another File" in text
    assert "restore_another_file" in text
    assert "Restore complete." in text
    assert "Restore failed." in text
    assert "restore_progress.show()" in text
    assert "restore_progress.hide()" in text
    assert "start_restore" in text
    assert "Download Recommended Model" in text
    assert "Use Existing Checkpoint Folder" in text
    assert "select_checkpoint_folder_text" in text
    assert "PyTorch checkpoint files can execute code" in text
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
