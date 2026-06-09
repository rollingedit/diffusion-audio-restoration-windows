from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


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
        creationflags=CREATE_NO_WINDOW,
    )
    return completed.returncode


def launch_app(root: Path) -> int:
    python = runtime_python(root)
    if not python.exists():
        print(f"Runtime Python was not found: {python}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.Popen(
        [str(python), "-m", "rolling_a2sb.app"],
        cwd=str(root),
        env=env,
        shell=False,
        creationflags=CREATE_NO_WINDOW,
    )
    return 0


def show_error(title: str, message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        print(f"{title}: {message}", file=sys.stderr)


def main() -> int:
    root = app_root()
    setup_code = ensure_runtime(root)
    if setup_code != 0:
        show_error(
            "A2SB Restorer setup failed",
            "Runtime setup failed. Use the Start Menu Repair Runtime shortcut, then run A2SB Doctor.",
        )
        return setup_code
    return launch_app(root)


if __name__ == "__main__":
    raise SystemExit(main())
