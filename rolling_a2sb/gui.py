from __future__ import annotations

import sys
from pathlib import Path

from . import paths
from .runtime_check import diagnostic_text, doctor


def run_gui() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QHBoxLayout,
            QLabel,
            QMainWindow,
            QPushButton,
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

            root = QWidget()
            layout = QVBoxLayout(root)

            title = QLabel("A2SB Restorer")
            title.setAlignment(Qt.AlignLeft)
            title.setStyleSheet("font-size: 22px; font-weight: 600;")
            layout.addWidget(title)

            self.status = QLabel("")
            layout.addWidget(self.status)

            button_row = QHBoxLayout()
            self.recheck_button = QPushButton("Run Doctor")
            self.models_button = QPushButton("Open Models Folder")
            self.logs_button = QPushButton("Open Logs Folder")
            button_row.addWidget(self.recheck_button)
            button_row.addWidget(self.models_button)
            button_row.addWidget(self.logs_button)
            button_row.addStretch(1)
            layout.addLayout(button_row)

            self.report = QTextEdit()
            self.report.setReadOnly(True)
            layout.addWidget(self.report, 1)

            self.setCentralWidget(root)

            self.recheck_button.clicked.connect(self.refresh_report)
            self.models_button.clicked.connect(lambda: self.open_folder(paths.models_dir()))
            self.logs_button.clicked.connect(lambda: self.open_folder(paths.logs_dir()))
            self.refresh_report()

        def refresh_report(self) -> None:
            report = doctor()
            self.status.setText("Ready" if report.get("ok") else "Setup needs attention")
            self.report.setPlainText(diagnostic_text(report))

        def open_folder(self, folder: Path) -> None:
            folder.mkdir(parents=True, exist_ok=True)
            import os

            os.startfile(str(folder))

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()

