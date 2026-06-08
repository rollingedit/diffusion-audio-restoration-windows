from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .audio_probe import audio_info_dict, probe_audio
from .audio_prepare import prepare_audio
from .checkpoint_manager import (
    checkpoint_paths_from_validation,
    select_manual_checkpoint_folder,
    trusted_manual_checkpoint_warning,
    validate_checkpoint_folder,
)
from .config_builder import RestoreConfigRequest, write_restore_config
from .downloader import build_download_plan
from .job import create_restore_job, with_config_path
from .log import append_log
from .runtime_check import diagnostic_text, doctor
from .settings import load_settings, remember_input, update_settings
from .worker import inference_command


@dataclass(frozen=True)
class DryRunRestorePlan:
    job_id: str
    job_dir: str
    log_path: str
    input_audio: str
    prepared_input_audio: str
    audio_converted: bool
    output_audio: str
    partial_output_audio: str
    config_path: str
    command: list[str]


def doctor_report_text() -> str:
    return diagnostic_text(doctor())


def download_plan_text(mode: str = "twosplit", target_dir: Path | None = None) -> str:
    plan = build_download_plan(mode=mode, target_dir=target_dir)
    return json.dumps(
        {
            "repo_id": plan.repo_id,
            "model": plan.mode,
            "files": plan.filenames,
            "target_dir": str(plan.target_dir),
            "required_bytes": plan.required_bytes,
            "free_bytes": plan.free_bytes,
            "enough_space": plan.enough_space,
        },
        indent=2,
    )


def audio_probe_text(audio_path: Path) -> str:
    return json.dumps(audio_info_dict(probe_audio(audio_path)), indent=2)


def select_checkpoint_folder_text(
    folder: Path,
    mode: str = "twosplit",
    trusted: bool = False,
) -> str:
    validation, manifest_path = select_manual_checkpoint_folder(folder, mode=mode, trusted=trusted)
    return json.dumps(
        {
            "ok": validation.ok,
            "mode": validation.mode,
            "folder": str(Path(folder).resolve()),
            "manifest": str(manifest_path),
            "files": [str(file.path) for file in validation.files],
        },
        indent=2,
    )


def prepare_restore_dry_run(
    input_audio: Path,
    output_audio: Path | None = None,
    steps: int = 50,
    model_mode: str = "twosplit",
    checkpoint_folder: Path | None = None,
    trust_manual_checkpoints: bool = False,
) -> DryRunRestorePlan:
    settings = load_settings()
    selected_checkpoint_folder = checkpoint_folder or (
        Path(settings.checkpoint_folder) if settings.checkpoint_folder else None
    )
    if selected_checkpoint_folder is None:
        from . import paths

        selected_checkpoint_folder = paths.models_dir()

    if checkpoint_folder:
        if not trust_manual_checkpoints:
            raise PermissionError(trusted_manual_checkpoint_warning())
        update_settings(
            model_mode=model_mode,
            checkpoint_folder=str(selected_checkpoint_folder.resolve()),
            checkpoint_manifest=None,
            trusted_manual_checkpoint_folder=True,
        )

    validation = validate_checkpoint_folder(selected_checkpoint_folder, mode=model_mode)
    checkpoint_paths = checkpoint_paths_from_validation(validation)
    job = create_restore_job(input_audio, output_audio=output_audio, steps=steps, model_mode=model_mode)
    prepared = prepare_audio(input_audio, Path(job.job_dir), dry_run=True)
    remember_input(input_audio)
    append_log(Path(job.log_path), f"created restore dry-run job {job.job_id}")
    append_log(Path(job.log_path), f"input={Path(input_audio).resolve()}")
    append_log(Path(job.log_path), f"prepared_input={prepared.prepared_path}")
    append_log(Path(job.log_path), f"audio_converted={prepared.converted}")
    append_log(Path(job.log_path), f"output={job.output_audio}")
    append_log(Path(job.log_path), f"partial_output={job.partial_output_audio}")
    append_log(Path(job.log_path), f"checkpoint_folder={Path(selected_checkpoint_folder).resolve()}")

    config_path = write_restore_config(
        RestoreConfigRequest(
            input_audio=prepared.prepared_path,
            output_audio=Path(job.output_audio),
            checkpoint_paths=checkpoint_paths,
            job_dir=Path(job.job_dir),
            steps=steps,
            model_mode=model_mode,
            require_input_exists=not prepared.converted,
        )
    )
    job = with_config_path(job, config_path)
    command = [str(part) for part in inference_command(config_path)]
    append_log(Path(job.log_path), f"config={config_path}")
    append_log(Path(job.log_path), "dry-run: restore subprocess was not started")
    return DryRunRestorePlan(
        job_id=job.job_id,
        job_dir=job.job_dir,
        log_path=job.log_path,
        input_audio=job.input_audio,
        prepared_input_audio=str(prepared.prepared_path),
        audio_converted=prepared.converted,
        output_audio=job.output_audio,
        partial_output_audio=job.partial_output_audio,
        config_path=str(config_path),
        command=command,
    )


def restore_plan_text(plan: DryRunRestorePlan) -> str:
    return json.dumps(plan.__dict__, indent=2)
