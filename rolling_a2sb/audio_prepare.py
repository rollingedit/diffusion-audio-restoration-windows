from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import paths
from .audio_probe import AudioInfo, probe_audio
from .errors import AudioProbeError

TARGET_SAMPLE_RATE = 44100
TARGET_CHANNELS = 1


@dataclass(frozen=True)
class PreparedAudio:
    original_path: Path
    prepared_path: Path
    info: AudioInfo
    converted: bool
    command: list[str]


def needs_preparation(info: AudioInfo) -> bool:
    return not (
        info.format == "wav"
        and info.sample_rate == TARGET_SAMPLE_RATE
        and info.channels == TARGET_CHANNELS
    )


def prepare_audio(
    input_audio: Path,
    job_dir: Path,
    dry_run: bool = False,
    ffmpeg_path: Path | None = None,
) -> PreparedAudio:
    input_audio = Path(input_audio)
    job_dir = Path(job_dir)
    info = probe_audio(input_audio)
    if not needs_preparation(info):
        return PreparedAudio(
            original_path=input_audio.resolve(),
            prepared_path=input_audio.resolve(),
            info=info,
            converted=False,
            command=[],
        )

    prepared_path = job_dir / "prepared_input.wav"
    command = ffmpeg_prepare_command(input_audio, prepared_path, ffmpeg_path=ffmpeg_path)
    if not dry_run:
        prepared_path.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=False, creationflags=CREATE_NO_WINDOW)
        if completed.returncode != 0:
            raise AudioProbeError(completed.stderr.strip() or f"FFmpeg failed to prepare {input_audio}")

    return PreparedAudio(
        original_path=input_audio.resolve(),
        prepared_path=prepared_path.resolve(),
        info=info,
        converted=True,
        command=command,
    )


def ffmpeg_prepare_command(input_audio: Path, output_audio: Path, ffmpeg_path: Path | None = None) -> list[str]:
    ffmpeg = ffmpeg_path or paths.ffmpeg_path()
    if not ffmpeg.exists():
        import shutil

        found = shutil.which("ffmpeg")
        if found:
            ffmpeg = Path(found)
    return [
        str(ffmpeg),
        "-y",
        "-i",
        str(Path(input_audio)),
        "-ac",
        str(TARGET_CHANNELS),
        "-ar",
        str(TARGET_SAMPLE_RATE),
        "-vn",
        str(Path(output_audio)),
    ]
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

