from __future__ import annotations

import sys
from pathlib import Path

from . import paths
from .subprocess_runner import CancelCallback, CommandResult, LineCallback, run_command, run_command_streaming


def inference_command(config_path: Path, python_exe: Path | None = None) -> list[str | Path]:
    return [
        python_exe or Path(sys.executable),
        paths.engine_root() / "ensembled_inference_api.py",
        "predict",
        "-c",
        config_path,
    ]


def run_restore_config(config_path: Path, python_exe: Path | None = None) -> CommandResult:
    return run_command(inference_command(config_path, python_exe=python_exe), cwd=paths.engine_root())


def run_restore_config_streaming(
    config_path: Path,
    python_exe: Path | None = None,
    on_line: LineCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> CommandResult:
    return run_command_streaming(
        inference_command(config_path, python_exe=python_exe),
        cwd=paths.engine_root(),
        on_line=on_line,
        should_cancel=should_cancel,
    )
