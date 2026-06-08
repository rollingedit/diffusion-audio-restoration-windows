from pathlib import Path

from rolling_a2sb.worker import inference_command


def test_inference_command_uses_argument_array(tmp_path: Path) -> None:
    config = tmp_path / "restore_config.yaml"

    command = inference_command(config, python_exe=Path("runtime/Scripts/python.exe"))

    assert command[0] == Path("runtime/Scripts/python.exe")
    assert command[1].name == "ensembled_inference_api.py"
    assert command[2:] == ["predict", "-c", config]
    assert all(";" not in str(part) for part in command)

