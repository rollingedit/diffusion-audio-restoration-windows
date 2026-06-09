from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, paths


@dataclass(frozen=True)
class RestoreJob:
    job_id: str
    created_at: str
    input_audio: str
    output_audio: str
    partial_output_audio: str
    job_dir: str
    log_path: str
    config_path: str | None
    steps: int
    model_mode: str
    app_version: str


def safe_stem(path: Path) -> str:
    stem = Path(path).stem.strip() or "audio"
    stem = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "audio"


def default_output_path(input_audio: Path, output_dir: Path | None = None, task_mode: str = "bandwidth") -> Path:
    input_audio = Path(input_audio)
    target_dir = Path(output_dir) if output_dir else input_audio.parent / "A2SB Restored"
    task_suffixes = {
        "bandwidth": "highfreq",
        "inpaint": "inpaint",
    }
    suffix = task_suffixes.get(task_mode, "restore")
    base = f"{safe_stem(input_audio)}__a2sb_{suffix}.wav"
    candidate = target_dir / base
    index = 2
    while candidate.resolve() == input_audio.resolve() or candidate.exists():
        candidate = target_dir / f"{safe_stem(input_audio)}__a2sb_{suffix}-{index}.wav"
        index += 1
    return candidate


def partial_output_path(output_audio: Path, job_dir: Path | None = None) -> Path:
    output_audio = Path(output_audio)
    if job_dir:
        return Path(job_dir) / f"{output_audio.name}.partial"
    return output_audio.with_name(f"{output_audio.name}.partial")


def create_restore_job(
    input_audio: Path,
    output_audio: Path | None = None,
    steps: int = 50,
    model_mode: str = "twosplit",
    task_mode: str = "bandwidth",
) -> RestoreJob:
    paths.ensure_app_dirs()
    job_id = uuid.uuid4().hex
    job_dir = paths.jobs_dir() / job_id
    job_dir.mkdir(parents=True, exist_ok=False)

    output = output_audio or default_output_path(Path(input_audio), task_mode=task_mode)
    output.parent.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / "restore.log"
    partial_output = partial_output_path(output, job_dir)

    job = RestoreJob(
        job_id=job_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        input_audio=str(Path(input_audio).resolve()),
        output_audio=str(output.resolve()),
        partial_output_audio=str(partial_output.resolve()),
        job_dir=str(job_dir.resolve()),
        log_path=str(log_path.resolve()),
        config_path=None,
        steps=steps,
        model_mode=model_mode,
        app_version=__version__,
    )
    write_job_manifest(job)
    return job


def write_job_manifest(job: RestoreJob) -> Path:
    path = Path(job.job_dir) / "job.json"
    path.write_text(json.dumps(asdict(job), indent=2) + "\n", encoding="utf-8")
    return path


def with_config_path(job: RestoreJob, config_path: Path) -> RestoreJob:
    updated = RestoreJob(**{**asdict(job), "config_path": str(Path(config_path).resolve())})
    write_job_manifest(updated)
    return updated
