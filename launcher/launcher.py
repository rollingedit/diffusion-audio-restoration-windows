from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def runtime_python(root: Path) -> Path:
    return root / "runtime" / "Scripts" / "python.exe"


def setup_script(root: Path) -> Path:
    return root / "scripts" / "setup_runtime.ps1"


def ensure_runtime(root: Path) -> int:
    python = runtime_python(root)
    if python.exists():
        return 0

    script = setup_script(root)
    if not script.exists():
        print(f"Runtime is missing and setup script was not found: {script}", file=sys.stderr)
        return 1

    completed = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=str(root),
        shell=False,
        check=False,
    )
    return completed.returncode


def launch_app(root: Path) -> int:
    python = runtime_python(root)
    if not python.exists():
        print(f"Runtime Python was not found: {python}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        [str(python), "-m", "rolling_a2sb.app"],
        cwd=str(root),
        env=env,
        shell=False,
        check=False,
    )
    return completed.returncode


def main() -> int:
    root = app_root()
    setup_code = ensure_runtime(root)
    if setup_code != 0:
        return setup_code
    return launch_app(root)


if __name__ == "__main__":
    raise SystemExit(main())

