from __future__ import annotations

import os
import threading
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    cancelled: bool = False


LineCallback = Callable[[str, str], None]
CancelCallback = Callable[[], bool]


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
    return CommandResult(completed.returncode, completed.stdout, completed.stderr, cancelled=False)


def run_command_streaming(
    args: Iterable[str | Path],
    cwd: Path,
    env: Mapping[str, str] | None = None,
    on_line: LineCallback | None = None,
    should_cancel: CancelCallback | None = None,
    poll_interval: float = 0.1,
) -> CommandResult:
    command = [str(arg) for arg in args]
    merged_env = os.environ.copy()
    merged_env["PYTHONUTF8"] = "1"
    if env:
        merged_env.update(env)

    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        bufsize=1,
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def read_stream(stream, stream_name: str, sink: list[str]) -> None:
        try:
            for line in iter(stream.readline, ""):
                sink.append(line)
                if on_line:
                    on_line(stream_name, line.rstrip("\r\n"))
        finally:
            stream.close()

    threads = [
        threading.Thread(target=read_stream, args=(process.stdout, "stdout", stdout_lines), daemon=True),
        threading.Thread(target=read_stream, args=(process.stderr, "stderr", stderr_lines), daemon=True),
    ]
    for thread in threads:
        thread.start()

    cancelled = False
    while process.poll() is None:
        if should_cancel and should_cancel():
            cancelled = True
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            break
        try:
            process.wait(timeout=poll_interval)
        except subprocess.TimeoutExpired:
            pass

    for thread in threads:
        thread.join(timeout=2)

    return CommandResult(
        returncode=process.returncode if process.returncode is not None else 1,
        stdout="".join(stdout_lines),
        stderr="".join(stderr_lines),
        cancelled=cancelled,
    )
