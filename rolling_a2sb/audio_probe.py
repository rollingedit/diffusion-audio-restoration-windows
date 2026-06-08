from __future__ import annotations

import json
import subprocess
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

from . import paths
from .errors import AudioProbeError

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac"}


@dataclass(frozen=True)
class AudioInfo:
    path: str
    format: str
    duration_seconds: float | None
    sample_rate: int | None
    channels: int | None


def is_supported_audio(path: Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def probe_audio(path: Path, ffprobe_path: Path | None = None) -> AudioInfo:
    path = Path(path)
    if not path.exists():
        raise AudioProbeError(f"Audio file does not exist: {path}")
    if not path.is_file():
        raise AudioProbeError(f"Audio path is not a file: {path}")
    if not is_supported_audio(path):
        raise AudioProbeError(f"Unsupported audio extension: {path.suffix}")

    if path.suffix.lower() == ".wav":
        wav_info = _probe_wav(path)
        if wav_info:
            return wav_info

    return _probe_with_ffprobe(path, ffprobe_path=ffprobe_path)


def _probe_wav(path: Path) -> AudioInfo | None:
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            sample_rate = handle.getframerate()
            duration = frames / sample_rate if sample_rate else None
            return AudioInfo(
                path=str(path.resolve()),
                format="wav",
                duration_seconds=duration,
                sample_rate=sample_rate,
                channels=handle.getnchannels(),
            )
    except wave.Error:
        return None


def _probe_with_ffprobe(path: Path, ffprobe_path: Path | None = None) -> AudioInfo:
    ffprobe = ffprobe_path or paths.ffprobe_path()
    if not ffprobe.exists():
        raise AudioProbeError(f"ffprobe is required to inspect this audio file: {ffprobe}")

    command = [
        str(ffprobe),
        "-v",
        "error",
        "-show_entries",
        "format=format_name,duration:stream=sample_rate,channels",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=False)
    if completed.returncode != 0:
        raise AudioProbeError(completed.stderr.strip() or f"ffprobe failed for {path}")

    data = json.loads(completed.stdout)
    stream = next((item for item in data.get("streams", []) if "sample_rate" in item), {})
    fmt = data.get("format", {})
    duration = fmt.get("duration")
    return AudioInfo(
        path=str(path.resolve()),
        format=str(fmt.get("format_name") or path.suffix.lstrip(".").lower()),
        duration_seconds=float(duration) if duration is not None else None,
        sample_rate=int(stream["sample_rate"]) if stream.get("sample_rate") else None,
        channels=int(stream["channels"]) if stream.get("channels") else None,
    )


def audio_info_dict(info: AudioInfo) -> dict:
    return asdict(info)

