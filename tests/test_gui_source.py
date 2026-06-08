from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gui_exposes_restore_controls_and_shared_actions() -> None:
    text = (ROOT / "rolling_a2sb" / "gui.py").read_text(encoding="utf-8")

    assert "QTabWidget" in text
    assert "QDialog" in text
    assert "Model Setup" in text
    assert "self.setup_tab = self.build_setup_tab()" in text
    assert "report = self.refresh_report()" in text
    assert "self.tabs.setCurrentWidget(self.setup_tab)" in text
    assert "open_model_setup_dialog" in text
    assert "Plan Restore" in text
    assert "QThread" in text
    assert "QProgressBar" in text
    assert "restore_line = Signal(str, str)" in text
    assert "restore_line_received" in text
    assert "parse_restore_step_progress" in text
    assert "self.restore_progress.setFormat" in text
    assert "Step {current} of {total}" in text
    assert "on_line=lambda stream_name, line" in text
    assert "self.restore_output.append" in text
    assert "Loading model..." in text
    assert "RestoreThread" in text
    assert "execute_restore_text" in text
    assert "Open Output Folder" in text
    assert "Restore Another File" in text
    assert "restore_another_file" in text
    assert "Restore complete." in text
    assert "Restore failed." in text
    assert "Cancel" in text
    assert "cancel_restore" in text
    assert "self.restore_setup_button = QPushButton(\"Model Setup\")" in text
    assert "self.restore_setup_button.clicked.connect(self.open_model_setup_dialog)" in text
    assert "show_restore_error" in text
    assert "is_checkpoint_setup_error(text)" in text
    assert "Use Model Setup to download the recommended model" in text
    assert "should_cancel=lambda: self.cancel_requested" in text
    assert "Cancel requested. Waiting for restore process to stop..." in text
    assert "restore_progress.show()" in text
    assert "restore_progress.hide()" in text
    assert "start_restore" in text
    assert "Download Recommended Model" in text
    assert "Repair Runtime" in text
    assert "RuntimeRepairThread" in text
    assert "repair_runtime_text" in text
    assert "self.repair_runtime_button.clicked.connect(self.start_runtime_repair)" in text
    assert "Use Existing Checkpoint Folder" in text
    assert "select_checkpoint_folder_text" in text
    assert "current_model_mode" in text
    assert "download_plan_text(mode=self.current_model_mode())" in text
    assert "model_download_confirmation_text(mode=mode_combo.currentText())" in text
    assert "download_recommended_model_text(mode=mode)" in text
    assert "select_checkpoint_folder_text(Path(folder), mode=mode, trusted=True)" in text
    assert "mode_combo.currentTextChanged.connect" in text
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
