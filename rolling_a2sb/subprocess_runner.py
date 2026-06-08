from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def run_command(
    args: Iterable[str | Path],
    cwd: Path,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> CommandResult:
    command = [str(arg) for arg in args]
    merged_env = os.environ.copy()
    merged_env["PYTHONUTF8"] = "1"
    if env:
        merged_env.update(env)

    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        timeout=timeout,
        check=False,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)

