from __future__ import annotations

import sys
from pathlib import Path
from typing import Mapping

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


def engine_import_check_command(python_exe: Path | None = None) -> list[str | Path]:
    return [
        python_exe or Path(sys.executable),
        "-c",
        "import ensembled_inference_api",
    ]


def check_engine_imports(python_exe: Path | None = None) -> dict[str, object]:
    command = engine_import_check_command(python_exe=python_exe)
    result = run_command(command, cwd=paths.engine_root(), env=worker_env())
    return {
        "ok": result.returncode == 0,
        "command": [str(part) for part in command],
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def worker_env() -> Mapping[str, str]:
    cache_root = paths.cache_dir()
    hf_home = cache_root / "huggingface"
    torch_home = cache_root / "torch"
    matplotlib_config = cache_root / "matplotlib"
    for path in [cache_root, hf_home, torch_home, matplotlib_config]:
        path.mkdir(parents=True, exist_ok=True)
    return {
        "HF_HOME": str(hf_home),
        "HUGGINGFACE_HUB_CACHE": str(hf_home / "hub"),
        "TORCH_HOME": str(torch_home),
        "MPLCONFIGDIR": str(matplotlib_config),
        "XDG_CACHE_HOME": str(cache_root),
        "PYTHONUTF8": "1",
    }


def run_restore_config(config_path: Path, python_exe: Path | None = None) -> CommandResult:
    return run_command(inference_command(config_path, python_exe=python_exe), cwd=paths.engine_root(), env=worker_env())


def run_restore_config_streaming(
    config_path: Path,
    python_exe: Path | None = None,
    on_line: LineCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> CommandResult:
    return run_command_streaming(
        inference_command(config_path, python_exe=python_exe),
        cwd=paths.engine_root(),
        env=worker_env(),
        on_line=on_line,
        should_cancel=should_cancel,
    )
