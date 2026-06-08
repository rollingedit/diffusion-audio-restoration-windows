from pathlib import Path
import wave

import pytest

from rolling_a2sb.audio_probe import is_supported_audio, probe_audio
from rolling_a2sb.errors import AudioProbeError


def write_wav(path: Path, sample_rate: int = 8000, channels: int = 1, frames: int = 8000) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frames * channels)


def test_supported_audio_extensions() -> None:
    assert is_supported_audio(Path("song.wav"))
    assert is_supported_audio(Path("song.mp3"))
    assert is_supported_audio(Path("song.flac"))
    assert not is_supported_audio(Path("song.txt"))


def test_probe_wav_with_stdlib(tmp_path: Path) -> None:
    audio = tmp_path / "short.wav"
    write_wav(audio)

    info = probe_audio(audio)

    assert info.path == str(audio.resolve())
    assert info.format == "wav"
    assert info.duration_seconds == 1.0
    assert info.sample_rate == 8000
    assert info.channels == 1


def test_probe_rejects_unsupported_extension(tmp_path: Path) -> None:
    audio = tmp_path / "note.txt"
    audio.write_text("not audio", encoding="utf-8")

    with pytest.raises(AudioProbeError):
        probe_audio(audio)

