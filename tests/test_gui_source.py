from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gui_exposes_restore_controls_and_shared_actions() -> None:
    text = (ROOT / "rolling_a2sb" / "gui.py").read_text(encoding="utf-8")

    assert "QTabWidget" in text
    assert "QDialog" in text
    assert "Set Up Models" in text
    assert "self.setup_tab = self.build_setup_tab()" in text
    assert "report = self.refresh_report()" in text
    assert "self.tabs.setCurrentWidget(self.setup_tab)" in text
    assert "open_model_setup_dialog" in text
    assert "QTimer.singleShot" in text
    assert "offer_startup_model_download" in text
    assert "can_offer_model_download" in text
    assert "download_official_model(prompt=False)" in text
    assert "Plan Restore" in text
    assert "QThread" in text
    assert "QIcon" in text
    assert "app_icon_path" in text
    assert "setWindowIcon(QIcon(str(icon_path)))" in text
    assert "app.setWindowIcon(QIcon(str(icon_path)))" in text
    assert "QProgressBar" in text
    assert "QDoubleSpinBox" in text
    assert "QRadioButton" in text
    assert "QSlider" in text
    assert "self.inpaint_segment_slider = QSlider" in text
    assert "self.inpaint_start_slider" not in text
    assert "self.inpaint_end_slider" not in text
    assert "task_row.addWidget(self.inpaint_start_spin)" not in text
    assert "task_row.addWidget(self.inpaint_end_spin)" not in text
    assert "self.inpaint_start_spin.setMinimumWidth(120)" in text
    assert "self.inpaint_end_spin.setMinimumWidth(120)" in text
    assert "self.inpaint_duration_label" in text
    assert "Bandwidth extension" in text
    assert "Inpainting" in text
    assert "self.bandwidth_radio = QRadioButton" in text
    assert "self.inpaint_radio = QRadioButton" in text
    assert "self.task_combo" not in text
    assert "task_mode_help_text" in text
    assert "configure_inpaint_range_for_audio" in text
    assert "set_inpaint_controls_enabled(False)" in text
    assert "set_inpaint_controls_enabled(True)" in text
    assert "inpaint_slider_changed" in text
    assert "inpaint_spin_changed" in text
    assert "self.advanced_check = QCheckBox(\"Advanced\")" in text
    assert "update_restore_mode_ui" in text
    assert "restore_task_changed" in text
    assert "default_output_path(audio_path, task_mode=self.current_task_mode())" in text
    assert '"task_mode": self.current_task_mode()' in text
    assert '"inpaint_start_seconds"' in text
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
    assert "self.restore_setup_button = QPushButton(\"Set Up Models\")" in text
    assert "self.restore_setup_button.clicked.connect(self.open_model_setup_dialog)" in text
    assert "show_restore_error" in text
    assert "is_checkpoint_setup_error(text)" in text
    assert "Use Set Up Models to download the official model" in text
    assert "should_cancel=lambda: self.cancel_requested" in text
    assert "Cancel requested. Waiting for restore process to stop..." in text
    assert "restore_progress.show()" in text
    assert "restore_progress.hide()" in text
    assert "start_restore" in text
    assert "Download Official Model" in text
    assert "Repair Runtime" in text
    assert "RuntimeRepairThread" in text
    assert "repair_runtime_text" in text
    assert "self.repair_runtime_button.clicked.connect(self.start_runtime_repair)" in text
    assert "Use Existing Checkpoint Folder" in text
    assert "select_checkpoint_folder_text" in text
    assert "current_model_mode" in text
    assert "download_plan_text(mode=self.current_model_mode())" in text
    assert "model_download_confirmation_text(mode=mode_combo.currentText())" in text
    assert "download_recommended_model_stream_text" in text
    assert "ModelDownloadThread" in text
    assert "download_line = Signal(str)" in text
    assert "download_progress = Signal(int, int, str)" in text
    assert "on_progress_bytes=lambda current, total, label" in text
    assert "reuse_existing_model_text" in text
    assert "Checking for existing model checkpoints" in text
    assert "Models already installed" in text
    assert "self.setup_progress = QProgressBar()" in text
    assert "self.setup_progress.setRange(0, 0)" in text
    assert "self.setup_progress.setRange(0, 1000)" in text
    assert "update_model_download_progress" in text
    assert "model_download_progress(mode=self.download_mode)" in text
    assert "Downloading model: {percent}%" in text
    assert "model_download_progress_received" in text
    assert "{label}: {percent}%" in text
    assert "self.download_progress_timer.start(500)" not in text
    assert "set_setup_busy(True" in text
    assert "model_download_line_received" in text
    assert "select_checkpoint_folder_text(Path(folder), mode=mode, trusted=True)" in text
    assert "mode_combo.currentTextChanged.connect" in text
    assert "PyTorch checkpoint files can execute code" in text
    assert "confirm_and_download_model" in text
    assert "set_restore_ready" in text
    assert "self.restore_button.setEnabled(ready)" in text
    assert "self.plan_button.setEnabled(ready)" in text
    assert "build_logs_tab" in text
    assert "build_about_tab" in text
    assert "about_text" in text
    assert "QTextBrowser" in text
    assert "setOpenExternalLinks(True)" in text
    assert "about_html()" in text
    assert "Show Latest Log" in text
    assert "latest_restore_log_text" in text
    assert "prepare_restore_dry_run" in text
    assert "audio_probe_text" in text
    assert "setAcceptDrops(True)" in text
    assert "SUPPORTED_AUDIO_EXTENSIONS" in text
