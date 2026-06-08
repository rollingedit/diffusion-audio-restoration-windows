from __future__ import annotations

import json
from pathlib import Path

from .audio_probe import audio_info_dict, probe_audio
from .checkpoint_manager import select_manual_checkpoint_folder
from .downloader import build_download_plan, download_model
from .runtime_check import diagnostic_text, doctor
from .workflow import RestorePreparation as DryRunRestorePlan
from .workflow import prepare_restore


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


def model_download_confirmation_text(mode: str = "twosplit", target_dir: Path | None = None) -> str:
    plan = build_download_plan(mode=mode, target_dir=target_dir)
    return json.dumps(
        {
            "confirmation_required": True,
            "official_source": plan.repo_id,
            "model": plan.mode,
            "files": plan.filenames,
            "local_storage_location": str(plan.target_dir),
            "required_bytes": plan.required_bytes,
            "free_bytes": plan.free_bytes,
            "enough_space": plan.enough_space,
            "internet_required": True,
        },
        indent=2,
    )


def download_recommended_model_text(mode: str = "twosplit", target_dir: Path | None = None) -> str:
    progress: list[str] = []
    result = download_model(
        mode=mode,
        target_dir=target_dir,
        progress=progress.append,
    )
    return json.dumps(
        {
            "ok": result.validation.ok,
            "mode": result.mode,
            "manifest": str(result.manifest_path),
            "files": [str(path) for path in result.files],
            "progress": progress,
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
    return prepare_restore(
        input_audio=input_audio,
        output_audio=output_audio,
        steps=steps,
        model_mode=model_mode,
        checkpoint_folder=checkpoint_folder,
        trust_manual_checkpoints=trust_manual_checkpoints,
        dry_run=True,
    )


def restore_plan_text(plan: DryRunRestorePlan) -> str:
    return json.dumps(plan.__dict__, indent=2)
