from __future__ import annotations

import json
import sys
from pathlib import Path

from . import paths
from .errors import format_user_error
from .gui_actions import (
    about_text,
    audio_probe_text,
    doctor_report_text,
    download_plan_text,
    download_recommended_model_text,
    execute_restore_text,
    latest_restore_log_text,
    model_download_confirmation_text,
    prepare_restore_dry_run,
    restore_plan_text,
    select_checkpoint_folder_text,
)
from .runtime_check import doctor


SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}


def run_gui() -> int:
    try:
        from PySide6.QtCore import QThread, Qt, Signal
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QFileDialog,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QProgressBar,
            QSpinBox,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except Exception as exc:
        raise RuntimeError("PySide6 is required for the graphical app. Run Repair Runtime.") from exc

    class RestoreThread(QThread):
        restore_line = Signal(str, str)
        restore_finished = Signal(str)
        restore_failed = Signal(str)

        def __init__(self, restore_kwargs: dict) -> None:
            super().__init__()
            self.restore_kwargs = restore_kwargs

        def run(self) -> None:
            try:
                self.restore_finished.emit(
                    execute_restore_text(
                        **self.restore_kwargs,
                        on_line=lambda stream_name, line: self.restore_line.emit(stream_name, line),
                    )
                )
            except Exception as exc:
                self.restore_failed.emit(format_user_error(exc))

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.restore_thread = None
            self.last_output_folder: Path | None = None
            self.setWindowTitle("A2SB Restorer")
            self.resize(900, 620)
            self.setAcceptDrops(True)

            root = QWidget()
            layout = QVBoxLayout(root)

            title = QLabel("A2SB Restorer")
            title.setAlignment(Qt.AlignLeft)
            title.setStyleSheet("font-size: 22px; font-weight: 600;")
            layout.addWidget(title)

            self.status = QLabel("")
            layout.addWidget(self.status)

            self.tabs = QTabWidget()
            self.tabs.addTab(self.build_restore_tab(), "Restore")
            self.tabs.addTab(self.build_setup_tab(), "Setup")
            self.tabs.addTab(self.build_logs_tab(), "Logs")
            self.tabs.addTab(self.build_about_tab(), "About")
            layout.addWidget(self.tabs, 1)

            self.setCentralWidget(root)
            self.refresh_report()

        def build_setup_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout(tab)

            button_row = QHBoxLayout()
            self.recheck_button = QPushButton("Run Doctor")
            self.model_setup_button = QPushButton("Model Setup")
            self.download_plan_button = QPushButton("Model Download Plan")
            self.download_model_button = QPushButton("Download Recommended Model")
            self.copy_button = QPushButton("Copy Diagnostic")
            self.models_button = QPushButton("Open Models Folder")
            self.logs_button = QPushButton("Open Logs Folder")
            button_row.addWidget(self.recheck_button)
            button_row.addWidget(self.model_setup_button)
            button_row.addWidget(self.download_plan_button)
            button_row.addWidget(self.download_model_button)
            button_row.addWidget(self.copy_button)
            button_row.addWidget(self.models_button)
            button_row.addWidget(self.logs_button)
            button_row.addStretch(1)
            layout.addLayout(button_row)

            self.report = QTextEdit()
            self.report.setReadOnly(True)
            layout.addWidget(self.report, 1)

            self.recheck_button.clicked.connect(self.refresh_report)
            self.model_setup_button.clicked.connect(self.open_model_setup_dialog)
            self.download_plan_button.clicked.connect(self.show_download_plan)
            self.download_model_button.clicked.connect(self.confirm_and_download_model)
            self.copy_button.clicked.connect(self.copy_report)
            self.models_button.clicked.connect(lambda: self.open_folder(paths.models_dir()))
            self.logs_button.clicked.connect(lambda: self.open_folder(paths.logs_dir()))
            return tab

        def build_restore_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout(tab)

            input_row = QHBoxLayout()
            self.input_edit = QLineEdit()
            self.input_edit.setPlaceholderText("Drop or select WAV, MP3, or FLAC")
            self.input_button = QPushButton("Select Audio")
            input_row.addWidget(QLabel("Input"))
            input_row.addWidget(self.input_edit, 1)
            input_row.addWidget(self.input_button)
            layout.addLayout(input_row)

            output_row = QHBoxLayout()
            self.output_edit = QLineEdit()
            self.output_button = QPushButton("Output")
            output_row.addWidget(QLabel("Output"))
            output_row.addWidget(self.output_edit, 1)
            output_row.addWidget(self.output_button)
            layout.addLayout(output_row)

            checkpoint_row = QHBoxLayout()
            self.checkpoint_edit = QLineEdit()
            self.checkpoint_button = QPushButton("Checkpoints")
            self.trust_check = QCheckBox("Trust manual checkpoints")
            checkpoint_row.addWidget(QLabel("Models"))
            checkpoint_row.addWidget(self.checkpoint_edit, 1)
            checkpoint_row.addWidget(self.checkpoint_button)
            checkpoint_row.addWidget(self.trust_check)
            layout.addLayout(checkpoint_row)

            option_row = QHBoxLayout()
            self.model_combo = QComboBox()
            self.model_combo.addItems(["twosplit", "onesplit"])
            self.steps_spin = QSpinBox()
            self.steps_spin.setRange(1, 500)
            self.steps_spin.setValue(50)
            self.inspect_button = QPushButton("Inspect")
            self.plan_button = QPushButton("Plan Restore")
            self.restore_button = QPushButton("Restore")
            self.open_output_button = QPushButton("Open Output Folder")
            self.open_output_button.setEnabled(False)
            self.restore_another_button = QPushButton("Restore Another File")
            option_row.addWidget(QLabel("Model"))
            option_row.addWidget(self.model_combo)
            option_row.addWidget(QLabel("Steps"))
            option_row.addWidget(self.steps_spin)
            option_row.addStretch(1)
            option_row.addWidget(self.inspect_button)
            option_row.addWidget(self.plan_button)
            option_row.addWidget(self.restore_button)
            option_row.addWidget(self.open_output_button)
            option_row.addWidget(self.restore_another_button)
            layout.addLayout(option_row)

            self.restore_progress = QProgressBar()
            self.restore_progress.setRange(0, 0)
            self.restore_progress.setTextVisible(False)
            self.restore_progress.hide()
            layout.addWidget(self.restore_progress)

            self.restore_output = QTextEdit()
            self.restore_output.setReadOnly(True)
            layout.addWidget(self.restore_output, 1)

            self.input_button.clicked.connect(self.select_input_audio)
            self.output_button.clicked.connect(self.select_output_audio)
            self.checkpoint_button.clicked.connect(self.select_checkpoint_folder)
            self.inspect_button.clicked.connect(self.inspect_audio)
            self.plan_button.clicked.connect(self.plan_restore)
            self.restore_button.clicked.connect(self.start_restore)
            self.open_output_button.clicked.connect(self.open_output_folder)
            self.restore_another_button.clicked.connect(self.restore_another_file)
            return tab

        def build_logs_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout(tab)

            button_row = QHBoxLayout()
            self.refresh_log_button = QPushButton("Show Latest Log")
            self.copy_log_button = QPushButton("Copy Log")
            self.open_logs_tab_button = QPushButton("Open Logs Folder")
            button_row.addWidget(self.refresh_log_button)
            button_row.addWidget(self.copy_log_button)
            button_row.addWidget(self.open_logs_tab_button)
            button_row.addStretch(1)
            layout.addLayout(button_row)

            self.log_view = QTextEdit()
            self.log_view.setReadOnly(True)
            layout.addWidget(self.log_view, 1)

            self.refresh_log_button.clicked.connect(self.refresh_latest_log)
            self.copy_log_button.clicked.connect(self.copy_log)
            self.open_logs_tab_button.clicked.connect(lambda: self.open_folder(paths.logs_dir()))
            return tab

        def build_about_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout(tab)

            self.about_view = QTextEdit()
            self.about_view.setReadOnly(True)
            self.about_view.setPlainText(about_text())
            layout.addWidget(self.about_view, 1)
            return tab

        def refresh_report(self) -> None:
            report = doctor()
            self.status.setText("Ready" if report.get("ok") else "Setup needs attention")
            self.report.setPlainText(doctor_report_text())

        def show_download_plan(self) -> None:
            self.report.setPlainText(download_plan_text())

        def open_model_setup_dialog(self) -> None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Model Setup")
            layout = QVBoxLayout(dialog)

            summary = QLabel("Official NVIDIA two-split checkpoints")
            summary.setStyleSheet("font-weight: 600;")
            layout.addWidget(summary)

            output = QTextEdit()
            output.setReadOnly(True)
            output.setPlainText(model_download_confirmation_text())
            layout.addWidget(output, 1)

            button_row = QHBoxLayout()
            download_button = QPushButton("Download Recommended Model")
            existing_button = QPushButton("Use Existing Checkpoint Folder")
            open_models_button = QPushButton("Open Models Folder")
            close_button = QPushButton("Close")
            button_row.addWidget(download_button)
            button_row.addWidget(existing_button)
            button_row.addWidget(open_models_button)
            button_row.addStretch(1)
            button_row.addWidget(close_button)
            layout.addLayout(button_row)

            def download_from_dialog() -> None:
                answer = QMessageBox.question(
                    dialog,
                    "Download recommended model",
                    "Download the official NVIDIA two-split checkpoints from Hugging Face into the app model folder?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
                try:
                    output.setPlainText(download_recommended_model_text())
                    self.report.setPlainText(output.toPlainText())
                    self.refresh_report()
                except Exception as exc:
                    output.setPlainText(format_user_error(exc))

            def use_existing_folder() -> None:
                folder = QFileDialog.getExistingDirectory(dialog, "Select checkpoint folder", str(paths.models_dir()))
                if not folder:
                    return
                answer = QMessageBox.question(
                    dialog,
                    "Trust checkpoint folder",
                    "Use this checkpoint folder only if you trust its source. PyTorch checkpoint files can execute code when loaded.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
                try:
                    text = select_checkpoint_folder_text(Path(folder), trusted=True)
                    output.setPlainText(text)
                    self.report.setPlainText(text)
                    self.checkpoint_edit.setText(folder)
                    self.trust_check.setChecked(True)
                    self.refresh_report()
                except Exception as exc:
                    output.setPlainText(format_user_error(exc))

            download_button.clicked.connect(download_from_dialog)
            existing_button.clicked.connect(use_existing_folder)
            open_models_button.clicked.connect(lambda: self.open_folder(paths.models_dir()))
            close_button.clicked.connect(dialog.accept)
            dialog.resize(720, 520)
            dialog.exec()

        def confirm_and_download_model(self) -> None:
            confirmation = model_download_confirmation_text()
            self.report.setPlainText(confirmation)
            answer = QMessageBox.question(
                self,
                "Download recommended model",
                "Download the official NVIDIA two-split checkpoints from Hugging Face into the app model folder?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            try:
                self.report.setPlainText(download_recommended_model_text())
                self.refresh_report()
            except Exception as exc:
                self.report.setPlainText(format_user_error(exc))

        def copy_report(self) -> None:
            QApplication.clipboard().setText(self.report.toPlainText())

        def refresh_latest_log(self) -> None:
            try:
                self.log_view.setPlainText(latest_restore_log_text())
            except Exception as exc:
                self.log_view.setPlainText(format_user_error(exc))

        def copy_log(self) -> None:
            QApplication.clipboard().setText(self.log_view.toPlainText())

        def open_folder(self, folder: Path) -> None:
            folder.mkdir(parents=True, exist_ok=True)
            import os

            os.startfile(str(folder))

        def dragEnterEvent(self, event) -> None:
            if self.first_supported_drop(event):
                event.acceptProposedAction()

        def dropEvent(self, event) -> None:
            audio_path = self.first_supported_drop(event)
            if not audio_path:
                return
            self.set_input_audio(audio_path)
            event.acceptProposedAction()

        def first_supported_drop(self, event) -> Path | None:
            if not event.mimeData().hasUrls():
                return None
            for url in event.mimeData().urls():
                if not url.isLocalFile():
                    continue
                path = Path(url.toLocalFile())
                if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
                    return path
            return None

        def select_input_audio(self) -> None:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Select audio",
                str(Path.home()),
                "Audio files (*.wav *.mp3 *.flac)",
            )
            if filename:
                self.set_input_audio(Path(filename))

        def set_input_audio(self, audio_path: Path) -> None:
            self.input_edit.setText(str(audio_path))
            self.output_edit.clear()
            self.inspect_audio()

        def select_output_audio(self) -> None:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Select output WAV",
                str(Path.home() / "A2SB Restored" / "restored.wav"),
                "WAV files (*.wav)",
            )
            if filename:
                self.output_edit.setText(str(Path(filename)))

        def select_checkpoint_folder(self) -> None:
            folder = QFileDialog.getExistingDirectory(self, "Select checkpoint folder", str(paths.models_dir()))
            if folder:
                self.checkpoint_edit.setText(folder)

        def inspect_audio(self) -> None:
            audio_path = self.current_input_audio()
            if not audio_path:
                return
            try:
                self.restore_output.setPlainText(audio_probe_text(audio_path))
            except Exception as exc:
                self.restore_output.setPlainText(format_user_error(exc))

        def plan_restore(self) -> None:
            audio_path = self.current_input_audio()
            if not audio_path:
                QMessageBox.warning(self, "Missing input", "Select an audio file first.")
                return
            checkpoint_folder = self.current_checkpoint_folder()
            try:
                plan = prepare_restore_dry_run(
                    input_audio=audio_path,
                    output_audio=self.current_output_audio(),
                    steps=self.steps_spin.value(),
                    model_mode=self.model_combo.currentText(),
                    checkpoint_folder=checkpoint_folder,
                    trust_manual_checkpoints=self.trust_check.isChecked(),
                )
            except Exception as exc:
                self.restore_output.setPlainText(format_user_error(exc))
                return
            self.restore_output.setPlainText(restore_plan_text(plan))

        def start_restore(self) -> None:
            audio_path = self.current_input_audio()
            if not audio_path:
                QMessageBox.warning(self, "Missing input", "Select an audio file first.")
                return
            self.restore_button.setEnabled(False)
            self.plan_button.setEnabled(False)
            self.open_output_button.setEnabled(False)
            self.restore_progress.show()
            self.restore_output.setPlainText("Preparing restore...\nLoading model...\nRestoring...")
            self.restore_thread = RestoreThread(
                {
                    "input_audio": audio_path,
                    "output_audio": self.current_output_audio(),
                    "steps": self.steps_spin.value(),
                    "model_mode": self.model_combo.currentText(),
                    "checkpoint_folder": self.current_checkpoint_folder(),
                    "trust_manual_checkpoints": self.trust_check.isChecked(),
                }
            )
            self.restore_thread.restore_line.connect(self.restore_line_received)
            self.restore_thread.restore_finished.connect(self.restore_finished)
            self.restore_thread.restore_failed.connect(self.restore_failed)
            self.restore_thread.finished.connect(self.restore_thread_finished)
            self.restore_thread.start()

        def restore_line_received(self, stream_name: str, line: str) -> None:
            self.restore_output.append(f"{stream_name}: {line}")

        def restore_finished(self, text: str) -> None:
            self.restore_output.setPlainText(f"Restore complete.\n\n{text}")
            try:
                data = json.loads(text)
                if data.get("ok") and data.get("output"):
                    self.last_output_folder = Path(data["output"]).parent
                    self.open_output_button.setEnabled(True)
            except Exception:
                pass
            self.refresh_latest_log()

        def restore_failed(self, text: str) -> None:
            self.restore_output.setPlainText(f"Restore failed.\n\n{text}")
            self.refresh_latest_log()

        def restore_thread_finished(self) -> None:
            self.restore_button.setEnabled(True)
            self.plan_button.setEnabled(True)
            self.restore_progress.hide()

        def open_output_folder(self) -> None:
            if self.last_output_folder:
                self.open_folder(self.last_output_folder)

        def restore_another_file(self) -> None:
            self.input_edit.clear()
            self.output_edit.clear()
            self.restore_output.clear()
            self.last_output_folder = None
            self.open_output_button.setEnabled(False)
            self.input_edit.setFocus()

        def current_input_audio(self) -> Path | None:
            text = self.input_edit.text().strip()
            if not text:
                return None
            path = Path(text)
            if path.is_dir() or path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
                self.restore_output.setPlainText("Unsupported input. Select WAV, MP3, or FLAC audio.")
                return None
            return path

        def current_output_audio(self) -> Path | None:
            text = self.output_edit.text().strip()
            return Path(text) if text else None

        def current_checkpoint_folder(self) -> Path | None:
            text = self.checkpoint_edit.text().strip()
            return Path(text) if text else None

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
