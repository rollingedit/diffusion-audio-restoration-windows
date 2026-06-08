from pathlib import Path
import wave

from rolling_a2sb.cli import main


def write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 8000)


def test_probe_cli_json_outputs_audio_info(tmp_path: Path, capsys) -> None:
    audio = tmp_path / "short.wav"
    write_wav(audio)

    exit_code = main(["probe", str(audio), "--json"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"sample_rate": 8000' in output
    assert '"channels": 1' in output


def test_download_model_requires_confirmation(tmp_path: Path, capsys) -> None:
    exit_code = main(["download-model", "--model", "twosplit", "--target-dir", str(tmp_path)])

    assert exit_code == 2
    output = capsys.readouterr().out
    assert '"confirmation_required": true' in output
    assert "nvidia/audio_to_audio_schrodinger_bridge" in output

