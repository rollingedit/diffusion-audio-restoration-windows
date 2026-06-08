from pathlib import Path
import sys

from rolling_a2sb.worker import inference_command, worker_env
from rolling_a2sb.subprocess_runner import run_command_streaming


def test_inference_command_uses_argument_array(tmp_path: Path) -> None:
    config = tmp_path / "restore_config.yaml"

    command = inference_command(config, python_exe=Path("runtime/Scripts/python.exe"))

    assert command[0] == Path("runtime/Scripts/python.exe")
    assert command[1].name == "ensembled_inference_api.py"
    assert command[2:] == ["predict", "-c", config]
    assert all(";" not in str(part) for part in command)


def test_worker_env_uses_app_owned_cache_dirs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))

    env = worker_env()

    assert env["HF_HOME"].startswith(str(tmp_path / "data" / "cache"))
    assert env["HUGGINGFACE_HUB_CACHE"].endswith("huggingface\\hub")
    assert env["TORCH_HOME"].endswith("torch")
    assert env["MPLCONFIGDIR"].endswith("matplotlib")
    assert env["PYTHONUTF8"] == "1"


def test_streaming_runner_captures_stdout_and_stderr(tmp_path: Path) -> None:
    lines: list[tuple[str, str]] = []

    result = run_command_streaming(
        [
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        ],
        cwd=tmp_path,
        on_line=lambda stream, line: lines.append((stream, line)),
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "out"
    assert result.stderr.strip() == "err"
    assert ("stdout", "out") in lines
    assert ("stderr", "err") in lines


def test_streaming_runner_can_cancel_process(tmp_path: Path) -> None:
    result = run_command_streaming(
        [
            sys.executable,
            "-c",
            "import time; print('started', flush=True); time.sleep(30)",
        ],
        cwd=tmp_path,
        should_cancel=lambda: True,
    )

    assert result.cancelled is True
    assert result.returncode != 0
