from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import paths
from .audio_prepare import prepare_audio
from .checkpoint_manager import (
    checkpoint_paths_from_validation,
    trusted_manual_checkpoint_warning,
    validate_checkpoint_folder,
)
from .config_builder import RestoreConfigRequest, write_restore_config
from .job import create_restore_job, with_config_path
from .log import append_block, append_log
from .runtime_check import diagnostic_text, doctor
from .settings import effective_checkpoint_folder, load_settings, remember_input, update_settings
from .subprocess_runner import CommandResult
from .worker import inference_command, run_restore_config_streaming


LineCallback = Callable[[str, str], None]
CancelCallback = Callable[[], bool]
RestoreRunner = Callable[..., CommandResult]


@dataclass(frozen=True)
class RestorePreparation:
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


@dataclass(frozen=True)
class RestoreExecution:
    plan: RestorePreparation
    returncode: int
    stdout: str
    stderr: str
    cancelled: bool = False


def prepare_restore(
    input_audio: Path,
    output_audio: Path | None = None,
    steps: int = 50,
    model_mode: str = "twosplit",
    task_mode: str = "bandwidth",
    cutoff_hz: int = 4000,
    inpaint_start_seconds: float | None = None,
    inpaint_end_seconds: float | None = None,
    checkpoint_folder: Path | None = None,
    trust_manual_checkpoints: bool = False,
    dry_run: bool = False,
) -> RestorePreparation:
    settings = load_settings()
    selected_checkpoint_folder = effective_checkpoint_folder(settings, checkpoint_folder)

    if checkpoint_folder:
        if not trust_manual_checkpoints:
            raise PermissionError(trusted_manual_checkpoint_warning())
        update_settings(
            model_mode=model_mode,
            checkpoint_folder=str(selected_checkpoint_folder.resolve()),
            checkpoint_manifest=None,
            trusted_manual_checkpoint_folder=True,
        )

    if not dry_run:
        require_runtime_ready(model_mode)

    validation = validate_checkpoint_folder(selected_checkpoint_folder, mode=model_mode)
    checkpoint_paths = checkpoint_paths_from_validation(validation)
    job = create_restore_job(
        input_audio,
        output_audio=output_audio,
        steps=steps,
        model_mode=model_mode,
        task_mode=task_mode,
    )
    prepared = prepare_audio(input_audio, Path(job.job_dir), dry_run=dry_run)
    remember_input(input_audio)

    append_log(Path(job.log_path), f"created restore {'dry-run ' if dry_run else ''}job {job.job_id}")
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
            task_mode=task_mode,
            cutoff_hz=cutoff_hz,
            inpaint_start_seconds=inpaint_start_seconds,
            inpaint_end_seconds=inpaint_end_seconds,
            require_input_exists=not (dry_run and prepared.converted),
        )
    )
    job = with_config_path(job, config_path)
    append_log(Path(job.log_path), f"config={config_path}")
    command = [str(part) for part in inference_command(config_path)]

    if dry_run:
        append_log(Path(job.log_path), "dry-run: restore subprocess was not started")

    return RestorePreparation(
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


def require_runtime_ready(model_mode: str = "twosplit") -> None:
    report = doctor(mode=model_mode)
    required_checks = ["python", "imports", "torch", "ffmpeg", "ffprobe", "write_permissions", "checkpoints"]
    failed = [name for name in required_checks if not report.get(name, {}).get("ok", False)]
    if failed:
        summary = ", ".join(failed)
        raise RuntimeError(f"Restore cannot start because setup is not ready: {summary}\n\n{diagnostic_text(report)}")


def execute_restore(
    input_audio: Path,
    output_audio: Path | None = None,
    steps: int = 50,
    model_mode: str = "twosplit",
    task_mode: str = "bandwidth",
    cutoff_hz: int = 4000,
    inpaint_start_seconds: float | None = None,
    inpaint_end_seconds: float | None = None,
    checkpoint_folder: Path | None = None,
    trust_manual_checkpoints: bool = False,
    on_line: LineCallback | None = None,
    should_cancel: CancelCallback | None = None,
    runner: RestoreRunner = run_restore_config_streaming,
) -> RestoreExecution:
    plan = prepare_restore(
        input_audio=input_audio,
        output_audio=output_audio,
        steps=steps,
        model_mode=model_mode,
        task_mode=task_mode,
        cutoff_hz=cutoff_hz,
        inpaint_start_seconds=inpaint_start_seconds,
        inpaint_end_seconds=inpaint_end_seconds,
        checkpoint_folder=checkpoint_folder,
        trust_manual_checkpoints=trust_manual_checkpoints,
        dry_run=False,
    )

    def log_stream(stream_name: str, line: str) -> None:
        append_log(Path(plan.log_path), f"{stream_name}: {line}")
        if on_line:
            on_line(stream_name, line)

    result = runner(Path(plan.config_path), on_line=log_stream, should_cancel=should_cancel)
    append_block(Path(plan.log_path), "stdout", result.stdout)
    append_block(Path(plan.log_path), "stderr", result.stderr)
    append_log(Path(plan.log_path), f"returncode={result.returncode}")
    if result.cancelled:
        append_log(Path(plan.log_path), "cancelled=true")

    return RestoreExecution(
        plan=plan,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        cancelled=result.cancelled,
    )
