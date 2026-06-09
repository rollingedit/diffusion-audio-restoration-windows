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


def local_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    data_dir = root / ".local_app_data" / "A2SB Restorer"
    download_dir = root / ".local_downloads"
    hf_home = download_dir / "huggingface-cache"
    env.setdefault("ROLLING_A2SB_DATA_DIR", str(data_dir))
    env.setdefault("ROLLING_A2SB_LOG_DIR", str(data_dir / "Logs"))
    env.setdefault("PIP_CACHE_DIR", str(download_dir / "pip-cache"))
    env.setdefault("HF_HOME", str(hf_home))
    env.setdefault("HUGGINGFACE_HUB_CACHE", str(hf_home / "hub"))
    env.setdefault("TORCH_HOME", str(download_dir / "torch-cache"))
    return env


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
        env=local_env(root),
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

    env = local_env(root)
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
