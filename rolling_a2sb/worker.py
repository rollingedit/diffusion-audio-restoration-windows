from __future__ import annotations

import sys
from pathlib import Path

from . import paths
from .subprocess_runner import CommandResult, run_command


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

