from __future__ import annotations

import sys
from pathlib import Path

from . import paths
from .gui_actions import audio_probe_text, doctor_report_text, download_plan_text, prepare_restore_dry_run, restore_plan_text
from .runtime_check import doctor


SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}


def run_gui() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QFileDialog,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSpinBox,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except Exception as exc:
        raise RuntimeError("PySide6 is required for the graphical app. Run Repair Runtime.") from exc

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
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
            layout.addWidget(self.tabs, 1)

            self.setCentralWidget(root)
            self.refresh_report()

        def build_setup_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout(tab)

            button_row = QHBoxLayout()
            self.recheck_button = QPushButton("Run Doctor")
            self.download_plan_button = QPushButton("Model Download Plan")
            self.copy_button = QPushButton("Copy Diagnostic")
            self.models_button = QPushButton("Open Models Folder")
            self.logs_button = QPushButton("Open Logs Folder")
            button_row.addWidget(self.recheck_button)
            button_row.addWidget(self.download_plan_button)
            button_row.addWidget(self.copy_button)
            button_row.addWidget(self.models_button)
            button_row.addWidget(self.logs_button)
            button_row.addStretch(1)
            layout.addLayout(button_row)

            self.report = QTextEdit()
            self.report.setReadOnly(True)
            layout.addWidget(self.report, 1)

            self.recheck_button.clicked.connect(self.refresh_report)
            self.download_plan_button.clicked.connect(self.show_download_plan)
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
            option_row.addWidget(QLabel("Model"))
            option_row.addWidget(self.model_combo)
            option_row.addWidget(QLabel("Steps"))
            option_row.addWidget(self.steps_spin)
            option_row.addStretch(1)
            option_row.addWidget(self.inspect_button)
            option_row.addWidget(self.plan_button)
            layout.addLayout(option_row)

            self.restore_output = QTextEdit()
            self.restore_output.setReadOnly(True)
            layout.addWidget(self.restore_output, 1)

            self.input_button.clicked.connect(self.select_input_audio)
            self.output_button.clicked.connect(self.select_output_audio)
            self.checkpoint_button.clicked.connect(self.select_checkpoint_folder)
            self.inspect_button.clicked.connect(self.inspect_audio)
            self.plan_button.clicked.connect(self.plan_restore)
            return tab

        def refresh_report(self) -> None:
            report = doctor()
            self.status.setText("Ready" if report.get("ok") else "Setup needs attention")
            self.report.setPlainText(doctor_report_text())

        def show_download_plan(self) -> None:
            self.report.setPlainText(download_plan_text())

        def copy_report(self) -> None:
            QApplication.clipboard().setText(self.report.toPlainText())

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
                self.restore_output.setPlainText(str(exc))

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
                self.restore_output.setPlainText(str(exc))
                return
            self.restore_output.setPlainText(restore_plan_text(plan))

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
