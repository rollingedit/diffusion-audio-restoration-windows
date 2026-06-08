from pathlib import Path
import wave

from rolling_a2sb.audio_prepare import TARGET_CHANNELS, TARGET_SAMPLE_RATE, needs_preparation, prepare_audio
from rolling_a2sb.audio_probe import AudioInfo


def write_wav(path: Path, sample_rate: int = 44100, channels: int = 1) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * sample_rate * channels)


def test_needs_preparation_for_non_target_audio() -> None:
    assert not needs_preparation(AudioInfo("x.wav", "wav", 1.0, TARGET_SAMPLE_RATE, TARGET_CHANNELS))
    assert needs_preparation(AudioInfo("x.wav", "wav", 1.0, 48000, 2))
    assert needs_preparation(AudioInfo("x.mp3", "mp3", 1.0, TARGET_SAMPLE_RATE, TARGET_CHANNELS))


def test_prepare_audio_passes_through_target_wav(tmp_path: Path) -> None:
    audio = tmp_path / "target.wav"
    write_wav(audio)

    prepared = prepare_audio(audio, tmp_path / "job", dry_run=True)

    assert prepared.converted is False
    assert prepared.prepared_path == audio.resolve()
    assert prepared.command == []


def test_prepare_audio_dry_run_plans_ffmpeg_for_non_target_wav(tmp_path: Path) -> None:
    audio = tmp_path / "stereo.wav"
    write_wav(audio, sample_rate=48000, channels=2)
    job_dir = tmp_path / "job"

    prepared = prepare_audio(audio, job_dir, dry_run=True, ffmpeg_path=tmp_path / "ffmpeg.exe")

    assert prepared.converted is True
    assert prepared.prepared_path == (job_dir / "prepared_input.wav").resolve()
    assert "-ac" in prepared.command
    assert "44100" in prepared.command

