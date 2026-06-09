from __future__ import annotations

import json
import sys
from pathlib import Path

from . import paths
from .audio_probe import probe_audio
from .errors import format_user_error
from .job import default_output_path
from .gui_actions import (
    about_text,
    about_html,
    audio_probe_text,
    doctor_report_text,
    download_plan_text,
    download_recommended_model_stream_text,
    execute_restore_text,
    latest_restore_log_text,
    model_download_confirmation_text,
    model_download_progress,
    is_checkpoint_setup_error,
    parse_restore_step_progress,
    prepare_restore_dry_run,
    repair_runtime_text,
    restore_plan_text,
    reuse_existing_model_text,
    select_checkpoint_folder_text,
    task_mode_help_text,
)
from .runtime_check import doctor


SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}


def run_gui() -> int:
    try:
        from PySide6.QtCore import QSize, QThread, QTimer, Qt, Signal
        from PySide6.QtGui import QColor, QIcon, QPainter
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QDoubleSpinBox,
            QFileDialog,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QProgressBar,
            QRadioButton,
            QSpinBox,
            QTabWidget,
            QTextBrowser,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except Exception as exc:
        raise RuntimeError("PySide6 is required for the graphical app. Run Repair Runtime.") from exc

    def app_icon_path() -> Path | None:
        candidates = [
            paths.app_install_dir() / "assets" / "app.ico",
            paths.app_install_dir() / "installer" / "assets" / "app.ico",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    class RestoreThread(QThread):
        restore_line = Signal(str, str)
        restore_finished = Signal(str)
        restore_failed = Signal(str)

        def __init__(self, restore_kwargs: dict) -> None:
            super().__init__()
            self.restore_kwargs = restore_kwargs
            self.cancel_requested = False

        def cancel(self) -> None:
            self.cancel_requested = True

        def run(self) -> None:
            try:
                self.restore_finished.emit(
                    execute_restore_text(
                        **self.restore_kwargs,
                        on_line=lambda stream_name, line: self.restore_line.emit(stream_name, line),
                        should_cancel=lambda: self.cancel_requested,
                    )
                )
            except Exception as exc:
                self.restore_failed.emit(format_user_error(exc))

    class RuntimeRepairThread(QThread):
        repair_line = Signal(str, str)
        repair_finished = Signal(str)
        repair_failed = Signal(str)

        def run(self) -> None:
            try:
                self.repair_finished.emit(
                    repair_runtime_text(on_line=lambda stream_name, line: self.repair_line.emit(stream_name, line))
                )
            except Exception as exc:
                self.repair_failed.emit(format_user_error(exc))

    class ModelDownloadThread(QThread):
        download_line = Signal(str)
        download_progress = Signal(object, object, str)
        download_finished = Signal(str)
        download_failed = Signal(str)

        def __init__(self, mode: str) -> None:
            super().__init__()
            self.mode = mode

        def run(self) -> None:
            try:
                self.download_finished.emit(
                    download_recommended_model_stream_text(
                        mode=self.mode,
                        on_progress=lambda line: self.download_line.emit(line),
                        on_progress_bytes=lambda current, total, label: self.download_progress.emit(current, total, label),
                    )
                )
            except Exception as exc:
                self.download_failed.emit(format_user_error(exc))

    class InpaintRangeSlider(QWidget):
        range_changed = Signal(float, float)

        def __init__(self) -> None:
            super().__init__()
            self._minimum = 0
            self._maximum = 0
            self._start = 0
            self._end = 50
            self._active_handle: str | None = None
            self.setMinimumHeight(34)

        def sizeHint(self) -> QSize:
            return QSize(520, 34)

        def setRange(self, minimum: int, maximum: int) -> None:
            self._minimum = int(minimum)
            self._maximum = max(int(maximum), self._minimum)
            self.setValues(self._start, self._end, emit=False)

        def setValues(self, start: int | float, end: int | float, emit: bool = True) -> None:
            old = (self._start, self._end)
            self._start = self._clamp_value(int(round(start)))
            self._end = self._clamp_value(int(round(end)))
            if self._end <= self._start:
                self._end = min(self._maximum, self._start + 1)
                self._start = max(self._minimum, self._end - 1)
            self.update()
            if emit and old != (self._start, self._end) and not self.signalsBlocked():
                self.range_changed.emit(self._start / 100, self._end / 100)

        def values(self) -> tuple[int, int]:
            return self._start, self._end

        def paintEvent(self, event) -> None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            y = self.height() // 2
            left = self._handle_radius()
            right = max(left + 1, self.width() - self._handle_radius())
            start_x = self._value_to_x(self._start)
            end_x = self._value_to_x(self._end)
            painter.setPen(QColor(130, 130, 130))
            painter.drawLine(left, y, right, y)
            painter.setPen(QColor(32, 139, 120))
            painter.drawLine(start_x, y, end_x, y)
            for x, active in [(start_x, self._active_handle == "start"), (end_x, self._active_handle == "end")]:
                painter.setBrush(QColor(32, 139, 120) if active else QColor(88, 88, 88))
                painter.setPen(QColor(185, 185, 185))
                painter.drawEllipse(x - 8, y - 8, 16, 16)
            painter.end()

        def mousePressEvent(self, event) -> None:
            if not self.isEnabled() or self._maximum <= self._minimum:
                return
            value = self._x_to_value(event.position().x())
            self._active_handle = "start" if abs(value - self._start) <= abs(value - self._end) else "end"
            self._move_active_handle(value)

        def mouseMoveEvent(self, event) -> None:
            if self._active_handle:
                self._move_active_handle(self._x_to_value(event.position().x()))

        def mouseReleaseEvent(self, event) -> None:
            self._active_handle = None
            self.update()

        def _move_active_handle(self, value: int) -> None:
            if self._active_handle == "start":
                self.setValues(min(value, self._end - 1), self._end)
            elif self._active_handle == "end":
                self.setValues(self._start, max(value, self._start + 1))

        def _handle_radius(self) -> int:
            return 10

        def _value_to_x(self, value: int) -> int:
            left = self._handle_radius()
            right = max(left + 1, self.width() - self._handle_radius())
            if self._maximum <= self._minimum:
                return left
            ratio = (value - self._minimum) / (self._maximum - self._minimum)
            return int(left + ratio * (right - left))

        def _x_to_value(self, x: float) -> int:
            left = self._handle_radius()
            right = max(left + 1, self.width() - self._handle_radius())
            ratio = max(0.0, min(1.0, (float(x) - left) / (right - left)))
            return self._clamp_value(int(round(self._minimum + ratio * (self._maximum - self._minimum))))

        def _clamp_value(self, value: int) -> int:
            return max(self._minimum, min(value, self._maximum))

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.restore_thread = None
            self.repair_thread = None
            self.download_thread = None
            self.download_mode = "twosplit"
            self.inpaint_audio_loaded = False
            self.last_output_folder: Path | None = None
            self.setWindowTitle("A2SB Restorer")
            icon_path = app_icon_path()
            if icon_path:
                self.setWindowIcon(QIcon(str(icon_path)))
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
            self.restore_tab = self.build_restore_tab()
            self.setup_tab = self.build_setup_tab()
            self.logs_tab = self.build_logs_tab()
            self.about_tab = self.build_about_tab()
            self.tabs.addTab(self.restore_tab, "Restore")
            self.tabs.addTab(self.setup_tab, "Setup")
            self.tabs.addTab(self.logs_tab, "Logs")
            self.tabs.addTab(self.about_tab, "About")
            layout.addWidget(self.tabs, 1)

            self.setCentralWidget(root)
            self.download_progress_timer = QTimer(self)
            self.download_progress_timer.timeout.connect(self.update_model_download_progress)
            report = self.refresh_report()
            if not report.get("ok"):
                self.tabs.setCurrentWidget(self.setup_tab)

        def build_setup_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout(tab)

            button_row = QHBoxLayout()
            self.recheck_button = QPushButton("Run Doctor")
            self.model_setup_button = QPushButton("Set Up Models")
            self.download_plan_button = QPushButton("Show Download Details")
            self.download_model_button = QPushButton("Download Official Model")
            self.repair_runtime_button = QPushButton("Repair Runtime")
            self.copy_button = QPushButton("Copy Diagnostic")
            self.models_button = QPushButton("Open Models Folder")
            self.logs_button = QPushButton("Open Logs Folder")
            button_row.addWidget(self.recheck_button)
            button_row.addWidget(self.model_setup_button)
            button_row.addWidget(self.download_plan_button)
            button_row.addWidget(self.download_model_button)
            button_row.addWidget(self.repair_runtime_button)
            button_row.addWidget(self.copy_button)
            button_row.addWidget(self.models_button)
            button_row.addWidget(self.logs_button)
            button_row.addStretch(1)
            layout.addLayout(button_row)

            self.report = QTextEdit()
            self.report.setReadOnly(True)
            layout.addWidget(self.report, 1)

            self.setup_progress = QProgressBar()
            self.setup_progress.setRange(0, 1000)
            self.setup_progress.setValue(0)
            self.setup_progress.setFixedHeight(22)
            self.setup_progress.setTextVisible(False)
            self.setup_progress.hide()
            layout.addWidget(self.setup_progress)

            self.recheck_button.clicked.connect(self.refresh_report)
            self.model_setup_button.clicked.connect(self.open_model_setup_dialog)
            self.download_plan_button.clicked.connect(self.show_download_plan)
            self.download_model_button.clicked.connect(self.confirm_and_download_model)
            self.repair_runtime_button.clicked.connect(self.start_runtime_repair)
            self.copy_button.clicked.connect(self.copy_report)
            self.models_button.clicked.connect(lambda: self.open_folder(paths.models_dir()))
            self.logs_button.clicked.connect(lambda: self.open_folder(paths.logs_dir()))
            return tab

        def build_restore_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout(tab)

            self.setup_notice = QLabel("")
            self.setup_notice.setWordWrap(True)
            self.setup_notice.setStyleSheet("font-weight: 600; color: #f0c674;")
            layout.addWidget(self.setup_notice)

            task_row = QHBoxLayout()
            self.bandwidth_radio = QRadioButton("Bandwidth extension")
            self.bandwidth_radio.setChecked(True)
            self.inpaint_radio = QRadioButton("Inpainting")
            self.cutoff_label = QLabel("Cutoff")
            self.cutoff_spin = QSpinBox()
            self.cutoff_spin.setRange(1000, 20000)
            self.cutoff_spin.setSingleStep(500)
            self.cutoff_spin.setValue(4000)
            self.advanced_check = QCheckBox("Advanced")
            task_row.addWidget(QLabel("Mode"))
            task_row.addWidget(self.bandwidth_radio)
            task_row.addWidget(self.inpaint_radio)
            task_row.addWidget(self.cutoff_label)
            task_row.addWidget(self.cutoff_spin)
            task_row.addStretch(1)
            task_row.addWidget(self.advanced_check)
            layout.addLayout(task_row)

            self.mode_help = QLabel("")
            self.mode_help.setWordWrap(True)
            layout.addWidget(self.mode_help)

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

            self.inpaint_range_row = QVBoxLayout()
            range_title_row = QHBoxLayout()
            self.inpaint_range_label = QLabel("Inpainting segment")
            self.inpaint_range_value = QLabel("Select audio first")
            range_title_row.addWidget(self.inpaint_range_label)
            range_title_row.addStretch(1)
            range_title_row.addWidget(self.inpaint_range_value)
            inpaint_time_row = QHBoxLayout()
            self.inpaint_start_label = QLabel("Start")
            self.inpaint_start_spin = QDoubleSpinBox()
            self.inpaint_start_spin.setRange(0.0, 3600.0)
            self.inpaint_start_spin.setDecimals(2)
            self.inpaint_start_spin.setSingleStep(0.1)
            self.inpaint_start_spin.setMinimumWidth(120)
            self.inpaint_start_spin.setEnabled(False)
            self.inpaint_end_label = QLabel("End")
            self.inpaint_end_spin = QDoubleSpinBox()
            self.inpaint_end_spin.setRange(0.01, 3600.0)
            self.inpaint_end_spin.setDecimals(2)
            self.inpaint_end_spin.setSingleStep(0.1)
            self.inpaint_end_spin.setValue(0.5)
            self.inpaint_end_spin.setMinimumWidth(120)
            self.inpaint_end_spin.setEnabled(False)
            self.inpaint_duration_label = QLabel("Duration 0.50s")
            inpaint_time_row.addWidget(self.inpaint_start_label)
            inpaint_time_row.addWidget(self.inpaint_start_spin)
            inpaint_time_row.addWidget(self.inpaint_end_label)
            inpaint_time_row.addWidget(self.inpaint_end_spin)
            inpaint_time_row.addWidget(self.inpaint_duration_label)
            inpaint_time_row.addStretch(1)
            self.inpaint_segment_slider = InpaintRangeSlider()
            self.inpaint_segment_slider.setRange(0, 0)
            self.inpaint_segment_slider.setEnabled(False)
            self.inpaint_range_row.addLayout(range_title_row)
            self.inpaint_range_row.addLayout(inpaint_time_row)
            self.inpaint_range_row.addWidget(self.inpaint_segment_slider)
            layout.addLayout(self.inpaint_range_row)

            checkpoint_row = QHBoxLayout()
            self.checkpoint_label = QLabel("Models")
            self.checkpoint_edit = QLineEdit()
            self.checkpoint_button = QPushButton("Checkpoints")
            self.trust_check = QCheckBox("Trust manual checkpoints")
            checkpoint_row.addWidget(self.checkpoint_label)
            checkpoint_row.addWidget(self.checkpoint_edit, 1)
            checkpoint_row.addWidget(self.checkpoint_button)
            checkpoint_row.addWidget(self.trust_check)
            layout.addLayout(checkpoint_row)

            option_row = QHBoxLayout()
            self.model_label = QLabel("Model")
            self.model_combo = QComboBox()
            self.model_combo.addItems(["twosplit", "onesplit"])
            self.steps_label = QLabel("Quality")
            self.steps_spin = QSpinBox()
            self.steps_spin.setRange(1, 500)
            self.steps_spin.setValue(50)
            self.inspect_button = QPushButton("Inspect")
            self.plan_button = QPushButton("Plan Restore")
            self.restore_button = QPushButton("Restore")
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.setEnabled(False)
            self.restore_setup_button = QPushButton("Set Up Models")
            self.restore_setup_button.setEnabled(False)
            self.open_output_button = QPushButton("Open Output Folder")
            self.open_output_button.setEnabled(False)
            self.restore_another_button = QPushButton("Restore Another File")
            option_row.addWidget(self.model_label)
            option_row.addWidget(self.model_combo)
            option_row.addWidget(self.steps_label)
            option_row.addWidget(self.steps_spin)
            option_row.addStretch(1)
            option_row.addWidget(self.inspect_button)
            option_row.addWidget(self.plan_button)
            option_row.addWidget(self.restore_button)
            option_row.addWidget(self.cancel_button)
            option_row.addWidget(self.restore_setup_button)
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
            self.cancel_button.clicked.connect(self.cancel_restore)
            self.restore_setup_button.clicked.connect(self.open_model_setup_dialog)
            self.open_output_button.clicked.connect(self.open_output_folder)
            self.restore_another_button.clicked.connect(self.restore_another_file)
            self.bandwidth_radio.toggled.connect(self.restore_task_changed)
            self.inpaint_radio.toggled.connect(self.restore_task_changed)
            self.inpaint_segment_slider.range_changed.connect(self.inpaint_slider_changed)
            self.inpaint_start_spin.valueChanged.connect(self.inpaint_spin_changed)
            self.inpaint_end_spin.valueChanged.connect(self.inpaint_spin_changed)
            self.advanced_check.stateChanged.connect(self.update_restore_mode_ui)
            self.update_restore_mode_ui()
            self.set_inpaint_controls_enabled(False)
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

            self.about_view = QTextBrowser()
            self.about_view.setOpenExternalLinks(True)
            self.about_view.setHtml(about_html())
            layout.addWidget(self.about_view, 1)
            return tab

        def refresh_report(self) -> dict:
            self.try_reuse_existing_models()
            report = doctor()
            self.status.setText("Ready" if report.get("ok") else self.not_ready_message(report))
            self.report.setPlainText(doctor_report_text())
            self.set_restore_ready(bool(report.get("ok")), report)
            return report

        def try_reuse_existing_models(self) -> None:
            try:
                reuse_existing_model_text(mode=self.current_model_mode())
            except Exception:
                pass

        def can_offer_model_download(self, report: dict) -> bool:
            checkpoints = report.get("checkpoints", {}) if isinstance(report.get("checkpoints"), dict) else {}
            required_ready = ["python", "imports", "torch", "ffmpeg", "ffprobe", "write_permissions"]
            return (not checkpoints.get("ok")) and all(
                isinstance(report.get(name), dict) and report[name].get("ok") for name in required_ready
            )

        def offer_startup_model_download(self) -> None:
            report = doctor()
            if not self.can_offer_model_download(report):
                return
            self.tabs.setCurrentWidget(self.setup_tab)
            mode = self.current_model_mode()
            self.report.setPlainText(model_download_confirmation_text(mode=mode))
            answer = QMessageBox.question(
                self,
                "Download official model",
                f"The app is installed, but the {mode} model checkpoints are missing.\n\n"
                "Download the official NVIDIA checkpoints from Hugging Face now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.Yes:
                self.download_official_model(prompt=False)

        def not_ready_message(self, report: dict) -> str:
            checkpoints = report.get("checkpoints", {}) if isinstance(report.get("checkpoints"), dict) else {}
            torch = report.get("torch", {}) if isinstance(report.get("torch"), dict) else {}
            if not checkpoints.get("ok"):
                return "Setup needs attention: download the official model or choose a trusted checkpoint folder."
            if not torch.get("ok"):
                return "Setup needs attention: repair the runtime or update the NVIDIA driver."
            return "Setup needs attention: run Doctor for details."

        def set_restore_ready(self, ready: bool, report: dict) -> None:
            self.setup_notice.setVisible(not ready)
            self.setup_notice.setText("" if ready else self.not_ready_message(report))
            self.restore_button.setEnabled(ready)
            self.plan_button.setEnabled(ready)
            self.restore_setup_button.setEnabled(not ready)

        def update_restore_mode_ui(self) -> None:
            inpaint = self.current_task_mode() == "inpaint"
            advanced = self.advanced_check.isChecked()
            self.mode_help.setText(self.mode_help_label())
            for widget in [self.cutoff_label, self.cutoff_spin]:
                widget.setVisible(not inpaint)
            for widget in [self.inpaint_start_label, self.inpaint_start_spin, self.inpaint_end_label, self.inpaint_end_spin]:
                widget.setVisible(inpaint)
            for index in range(self.inpaint_range_row.count()):
                item = self.inpaint_range_row.itemAt(index)
                if item and item.widget():
                    item.widget().setVisible(inpaint)
                elif item and item.layout():
                    for child_index in range(item.layout().count()):
                        child = item.layout().itemAt(child_index)
                        if child and child.widget():
                            child.widget().setVisible(inpaint)
            for widget in [
                self.checkpoint_label,
                self.checkpoint_edit,
                self.checkpoint_button,
                self.trust_check,
                self.model_label,
                self.model_combo,
                self.inspect_button,
                self.plan_button,
            ]:
                widget.setVisible(advanced)

        def restore_task_changed(self) -> None:
            if not self.sender().isChecked():
                return
            self.update_restore_mode_ui()
            self.restore_output.setPlainText(task_mode_help_text(self.current_task_mode()))
            audio_path = self.current_input_audio()
            if audio_path:
                current = self.current_output_audio()
                defaults = {
                    default_output_path(audio_path, task_mode="bandwidth"),
                    default_output_path(audio_path, task_mode="inpaint"),
                }
                if current is None or current in defaults:
                    self.output_edit.setText(str(default_output_path(audio_path, task_mode=self.current_task_mode())))

        def mode_help_label(self) -> str:
            if self.current_task_mode() == "inpaint":
                return "Inpainting repairs a short damaged or missing time segment. Select the segment below, then restore."
            return "Bandwidth extension predicts missing high-frequency detail for dull or low-passed audio."

        def set_inpaint_controls_enabled(self, enabled: bool) -> None:
            self.inpaint_audio_loaded = enabled
            for widget in [
                self.inpaint_segment_slider,
                self.inpaint_start_spin,
                self.inpaint_end_spin,
            ]:
                widget.setEnabled(enabled)
            if not enabled:
                self.inpaint_range_value.setText("Select audio first")

        def configure_inpaint_range_for_audio(self, audio_path: Path) -> None:
            try:
                info = probe_audio(audio_path)
            except Exception:
                self.set_inpaint_controls_enabled(False)
                return
            duration = info.duration_seconds
            if not duration or duration <= 0:
                self.set_inpaint_controls_enabled(False)
                return
            slider_max = max(1, int(duration * 100))
            self.inpaint_segment_slider.blockSignals(True)
            self.inpaint_segment_slider.setRange(0, slider_max)
            self.inpaint_segment_slider.setValues(0, slider_max, emit=False)
            self.inpaint_segment_slider.blockSignals(False)
            self.inpaint_start_spin.blockSignals(True)
            self.inpaint_end_spin.blockSignals(True)
            self.inpaint_start_spin.setRange(0.0, max(0.0, duration - 0.01))
            self.inpaint_end_spin.setRange(0.01, duration)
            self.inpaint_start_spin.setValue(0.0)
            self.inpaint_end_spin.setValue(duration)
            self.inpaint_start_spin.blockSignals(False)
            self.inpaint_end_spin.blockSignals(False)
            self.set_inpaint_controls_enabled(True)
            self.update_inpaint_range_label()

        def inpaint_slider_changed(self, start: float, end: float) -> None:
            if not self.inpaint_audio_loaded:
                return
            self.inpaint_start_spin.blockSignals(True)
            self.inpaint_end_spin.blockSignals(True)
            self.inpaint_start_spin.setValue(start)
            self.inpaint_end_spin.setValue(end)
            self.inpaint_start_spin.blockSignals(False)
            self.inpaint_end_spin.blockSignals(False)
            self.update_inpaint_range_label()

        def inpaint_spin_changed(self) -> None:
            if not self.inpaint_audio_loaded:
                return
            start_seconds = self.inpaint_start_spin.value()
            end_seconds = self.inpaint_end_spin.value()
            if end_seconds <= start_seconds:
                end_seconds = start_seconds + 0.01
                self.inpaint_end_spin.blockSignals(True)
                self.inpaint_end_spin.setValue(end_seconds)
                self.inpaint_end_spin.blockSignals(False)
            if end_seconds > self.inpaint_end_spin.maximum():
                end_seconds = self.inpaint_end_spin.maximum()
                self.inpaint_start_spin.blockSignals(True)
                self.inpaint_end_spin.blockSignals(True)
                self.inpaint_start_spin.setValue(start_seconds)
                self.inpaint_end_spin.setValue(end_seconds)
                self.inpaint_start_spin.blockSignals(False)
                self.inpaint_end_spin.blockSignals(False)
            self.inpaint_segment_slider.blockSignals(True)
            self.inpaint_segment_slider.setValues(int(start_seconds * 100), int(end_seconds * 100), emit=False)
            self.inpaint_segment_slider.blockSignals(False)
            self.update_inpaint_range_label()

        def update_inpaint_range_label(self) -> None:
            start = self.inpaint_start_spin.value()
            end = self.inpaint_end_spin.value()
            self.inpaint_range_value.setText(f"{start:.2f}s to {end:.2f}s")
            self.inpaint_duration_label.setText(f"Duration {max(0.0, end - start):.2f}s")

        def show_download_plan(self) -> None:
            self.report.setPlainText(download_plan_text(mode=self.current_model_mode()))

        def open_model_setup_dialog(self) -> None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Model Setup")
            layout = QVBoxLayout(dialog)

            summary = QLabel("Set up model checkpoints")
            summary.setStyleSheet("font-weight: 600;")
            layout.addWidget(summary)

            mode_row = QHBoxLayout()
            mode_combo = QComboBox()
            mode_combo.addItems(["twosplit", "onesplit"])
            mode_combo.setCurrentText(self.current_model_mode())
            mode_row.addWidget(QLabel("Model"))
            mode_row.addWidget(mode_combo)
            mode_row.addStretch(1)
            layout.addLayout(mode_row)

            output = QTextEdit()
            output.setReadOnly(True)
            output.setPlainText(model_download_confirmation_text(mode=mode_combo.currentText()))
            layout.addWidget(output, 1)

            button_row = QHBoxLayout()
            download_button = QPushButton("Start Official Model Setup")
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
                mode = mode_combo.currentText()
                answer = QMessageBox.question(
                    dialog,
                    "Download official model",
                    f"Download the official NVIDIA {mode} checkpoints from Hugging Face into the app model folder?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
                try:
                    self.model_combo.setCurrentText(mode)
                    self.tabs.setCurrentWidget(self.setup_tab)
                    dialog.accept()
                    self.download_official_model(prompt=False)
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
                    mode = mode_combo.currentText()
                    text = select_checkpoint_folder_text(Path(folder), mode=mode, trusted=True)
                    output.setPlainText(text)
                    self.report.setPlainText(text)
                    self.model_combo.setCurrentText(mode)
                    self.checkpoint_edit.setText(folder)
                    self.trust_check.setChecked(True)
                    self.refresh_report()
                except Exception as exc:
                    output.setPlainText(format_user_error(exc))

            mode_combo.currentTextChanged.connect(
                lambda mode: output.setPlainText(model_download_confirmation_text(mode=mode))
            )

            download_button.clicked.connect(download_from_dialog)
            existing_button.clicked.connect(use_existing_folder)
            open_models_button.clicked.connect(lambda: self.open_folder(paths.models_dir()))
            close_button.clicked.connect(dialog.accept)
            dialog.resize(720, 520)
            dialog.exec()

        def confirm_and_download_model(self) -> None:
            self.download_official_model(prompt=True)

        def download_official_model(self, prompt: bool = True) -> None:
            mode = self.current_model_mode()
            self.report.setPlainText("Checking for existing model checkpoints...\n")
            self.setup_progress.setRange(0, 1000)
            self.setup_progress.setValue(0)
            self.setup_progress.setTextVisible(False)
            self.setup_progress.show()
            reused = reuse_existing_model_text(mode=mode, on_progress=lambda line: self.report.append(line))
            if reused is not None:
                self.refresh_report()
                self.setup_progress.setRange(0, 1000)
                self.setup_progress.setValue(1000)
                self.setup_progress.setTextVisible(True)
                self.setup_progress.setFormat("Models already installed")
                self.report.setPlainText(reused)
                return
            self.setup_progress.hide()
            confirmation = model_download_confirmation_text(mode=mode)
            self.report.setPlainText(confirmation)
            if prompt:
                answer = QMessageBox.question(
                    self,
                    "Download official model",
                    f"Download the official NVIDIA {mode} checkpoints from Hugging Face into the app model folder?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
            self.start_model_download(mode)

        def start_model_download(self, mode: str) -> None:
            self.download_mode = mode
            self.set_setup_busy(True, "Downloading official model...\n")
            self.setup_progress.setRange(0, 1000)
            self.setup_progress.setValue(0)
            self.setup_progress.setTextVisible(True)
            self.setup_progress.setFormat("Connecting to Hugging Face...")
            self.download_thread = ModelDownloadThread(mode)
            self.download_thread.download_line.connect(self.model_download_line_received)
            self.download_thread.download_progress.connect(self.model_download_progress_received)
            self.download_thread.download_finished.connect(self.model_download_finished)
            self.download_thread.download_failed.connect(self.model_download_failed)
            self.download_thread.finished.connect(self.model_download_thread_finished)
            self.download_progress_timer.start(500)
            self.download_thread.start()

        def model_download_line_received(self, line: str) -> None:
            self.report.append(line)

        def update_model_download_progress(self) -> None:
            downloaded, required = model_download_progress(mode=self.download_mode)
            if required <= 0:
                self.setup_progress.setRange(0, 1000)
                self.setup_progress.setValue(0)
                self.setup_progress.setTextVisible(True)
                self.setup_progress.setFormat("Connecting to Hugging Face...")
                return
            ratio = max(0.0, min(float(downloaded) / float(required), 1.0))
            value = int(ratio * 1000)
            percent = int(ratio * 100)
            self.setup_progress.setRange(0, 1000)
            self.setup_progress.setValue(value)
            self.setup_progress.setTextVisible(True)
            self.setup_progress.setFormat(f"Downloading model: {percent}%")

        def model_download_progress_received(self, downloaded: object, required: object, label: str) -> None:
            downloaded = int(downloaded)
            required = int(required)
            if required <= 0:
                self.setup_progress.setRange(0, 1000)
                self.setup_progress.setValue(0)
                self.setup_progress.setTextVisible(True)
                self.setup_progress.setFormat(f"{label}: connecting...")
                return
            ratio = max(0.0, min(float(downloaded) / float(required), 1.0))
            value = int(ratio * 1000)
            percent = int(ratio * 100)
            self.setup_progress.setRange(0, 1000)
            self.setup_progress.setValue(value)
            self.setup_progress.setTextVisible(True)
            self.setup_progress.setFormat(f"{label}: {percent}%")

        def model_download_finished(self, text: str) -> None:
            self.download_progress_timer.stop()
            self.setup_progress.setRange(0, 1000)
            self.setup_progress.setValue(1000)
            self.setup_progress.setTextVisible(True)
            self.setup_progress.setFormat("Model setup complete")
            self.report.setPlainText(text)
            self.refresh_report()

        def model_download_failed(self, text: str) -> None:
            self.download_progress_timer.stop()
            self.report.setPlainText(f"Model download failed.\n\n{text}")

        def model_download_thread_finished(self) -> None:
            self.set_setup_busy(False)

        def start_runtime_repair(self) -> None:
            self.set_setup_busy(True, "Repairing runtime...\n")
            self.repair_thread = RuntimeRepairThread()
            self.repair_thread.repair_line.connect(self.repair_line_received)
            self.repair_thread.repair_finished.connect(self.repair_finished)
            self.repair_thread.repair_failed.connect(self.repair_failed)
            self.repair_thread.finished.connect(self.repair_thread_finished)
            self.repair_thread.start()

        def set_setup_busy(self, busy: bool, text: str | None = None) -> None:
            for button in [
                self.recheck_button,
                self.model_setup_button,
                self.download_plan_button,
                self.download_model_button,
                self.repair_runtime_button,
                self.copy_button,
                self.models_button,
                self.logs_button,
            ]:
                button.setEnabled(not busy)
            self.setup_progress.setVisible(busy)
            if not busy:
                self.setup_progress.setTextVisible(False)
            if text is not None:
                self.report.setPlainText(text)

        def repair_line_received(self, stream_name: str, line: str) -> None:
            self.report.append(f"{stream_name}: {line}")

        def repair_finished(self, text: str) -> None:
            self.report.setPlainText(f"Runtime repair complete.\n\n{text}")
            self.status.setText("Runtime repair complete. Run Doctor to recheck setup.")

        def repair_failed(self, text: str) -> None:
            self.report.setPlainText(f"Runtime repair failed.\n\n{text}")

        def repair_thread_finished(self) -> None:
            self.set_setup_busy(False)

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
            self.output_edit.setText(str(default_output_path(audio_path, task_mode=self.current_task_mode())))
            self.configure_inpaint_range_for_audio(audio_path)
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
                    task_mode=self.current_task_mode(),
                    cutoff_hz=self.cutoff_spin.value(),
                    inpaint_start_seconds=self.inpaint_start_spin.value() if self.current_task_mode() == "inpaint" else None,
                    inpaint_end_seconds=self.inpaint_end_spin.value() if self.current_task_mode() == "inpaint" else None,
                    checkpoint_folder=checkpoint_folder,
                    trust_manual_checkpoints=self.trust_check.isChecked(),
                )
            except Exception as exc:
                self.show_restore_error(format_user_error(exc))
                return
            self.restore_output.setPlainText(restore_plan_text(plan))
            self.restore_setup_button.setEnabled(False)

        def start_restore(self) -> None:
            audio_path = self.current_input_audio()
            if not audio_path:
                QMessageBox.warning(self, "Missing input", "Select an audio file first.")
                return
            self.restore_button.setEnabled(False)
            self.plan_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.restore_setup_button.setEnabled(False)
            self.open_output_button.setEnabled(False)
            self.restore_progress.setRange(0, 0)
            self.restore_progress.setTextVisible(False)
            self.restore_progress.show()
            self.restore_output.setPlainText("Preparing restore...\nLoading model...\nRestoring...")
            self.restore_thread = RestoreThread(
                {
                    "input_audio": audio_path,
                    "output_audio": self.current_output_audio(),
                    "steps": self.steps_spin.value(),
                    "model_mode": self.model_combo.currentText(),
                    "task_mode": self.current_task_mode(),
                    "cutoff_hz": self.cutoff_spin.value(),
                    "inpaint_start_seconds": self.inpaint_start_spin.value() if self.current_task_mode() == "inpaint" else None,
                    "inpaint_end_seconds": self.inpaint_end_spin.value() if self.current_task_mode() == "inpaint" else None,
                    "checkpoint_folder": self.current_checkpoint_folder(),
                    "trust_manual_checkpoints": self.trust_check.isChecked(),
                }
            )
            self.restore_thread.restore_line.connect(self.restore_line_received)
            self.restore_thread.restore_finished.connect(self.restore_finished)
            self.restore_thread.restore_failed.connect(self.restore_failed)
            self.restore_thread.finished.connect(self.restore_thread_finished)
            self.restore_thread.start()

        def cancel_restore(self) -> None:
            if self.restore_thread:
                self.restore_thread.cancel()
                self.cancel_button.setEnabled(False)
                self.restore_output.append("Cancel requested. Waiting for restore process to stop...")

        def restore_line_received(self, stream_name: str, line: str) -> None:
            progress = parse_restore_step_progress(line)
            if progress:
                current, total = progress
                self.restore_progress.setRange(0, total)
                self.restore_progress.setValue(current)
                self.restore_progress.setFormat(f"Step {current} of {total}")
                self.restore_progress.setTextVisible(True)
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
            self.show_restore_error(f"Restore failed.\n\n{text}")
            self.refresh_latest_log()

        def show_restore_error(self, text: str) -> None:
            if is_checkpoint_setup_error(text):
                text = f"{text}\n\nUse Set Up Models to download the official model or select a trusted checkpoint folder."
                self.restore_setup_button.setEnabled(True)
            else:
                self.restore_setup_button.setEnabled(False)
            self.restore_output.setPlainText(text)

        def restore_thread_finished(self) -> None:
            report = self.refresh_report()
            self.restore_button.setEnabled(bool(report.get("ok")))
            self.plan_button.setEnabled(bool(report.get("ok")))
            self.cancel_button.setEnabled(False)
            self.restore_progress.hide()

        def open_output_folder(self) -> None:
            if self.last_output_folder:
                self.open_folder(self.last_output_folder)

        def restore_another_file(self) -> None:
            self.input_edit.clear()
            self.output_edit.clear()
            self.restore_output.clear()
            self.set_inpaint_controls_enabled(False)
            self.last_output_folder = None
            self.open_output_button.setEnabled(False)
            self.restore_setup_button.setEnabled(False)
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

        def current_model_mode(self) -> str:
            return self.model_combo.currentText()

        def current_task_mode(self) -> str:
            return "inpaint" if self.inpaint_radio.isChecked() else "bandwidth"

    app = QApplication(sys.argv)
    icon_path = app_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    QTimer.singleShot(250, window.offer_startup_model_download)
    return app.exec()
