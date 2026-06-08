from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from . import paths
from .checkpoint_manager import (
    HF_REPO_ID,
    MODEL_FILES,
    CheckpointValidation,
    manifest_from_validation,
    save_manifest,
    validate_checkpoint_folder,
)
from .settings import update_settings

ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class DownloadPlan:
    mode: str
    repo_id: str
    filenames: list[str]
    target_dir: Path
    required_bytes: int
    free_bytes: int
    enough_space: bool


@dataclass(frozen=True)
class DownloadResult:
    mode: str
    files: list[Path]
    validation: CheckpointValidation
    manifest_path: Path


def checkpoint_filenames(mode: str) -> list[str]:
    try:
        return MODEL_FILES[mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported model mode: {mode}") from exc


def estimate_required_bytes(mode: str) -> int:
    # Each official A2SB checkpoint is about 2.26 GB. Use a conservative
    # estimate with room for partial files and metadata.
    return len(checkpoint_filenames(mode)) * 2_600_000_000


def build_download_plan(mode: str = "twosplit", target_dir: Path | None = None) -> DownloadPlan:
    target = target_dir or paths.models_dir()
    target.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(target).free
    required = estimate_required_bytes(mode)
    return DownloadPlan(
        mode=mode,
        repo_id=HF_REPO_ID,
        filenames=checkpoint_filenames(mode),
        target_dir=target,
        required_bytes=required,
        free_bytes=free,
        enough_space=free >= required,
    )


def download_model(
    mode: str = "twosplit",
    target_dir: Path | None = None,
    progress: ProgressCallback | None = None,
    compute_hashes: bool = True,
    force: bool = False,
    min_size_bytes: int = 2_000_000_000,
    hf_download: Callable[..., str] | None = None,
) -> DownloadResult:
    plan = build_download_plan(mode=mode, target_dir=target_dir)
    if not plan.enough_space and not force:
        raise OSError(
            f"Not enough free disk space for {mode} checkpoints. "
            f"Need about {plan.required_bytes} bytes, have {plan.free_bytes} bytes."
        )

    downloader = hf_download or _load_hf_download()
    downloaded: list[Path] = []
    for index, filename in enumerate(plan.filenames, start=1):
        _emit(progress, f"Downloading checkpoint {index} of {len(plan.filenames)}: {Path(filename).name}")
        path = downloader(
            repo_id=plan.repo_id,
            filename=filename,
            local_dir=str(plan.target_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        downloaded.append(Path(path))

    _emit(progress, "Verifying checkpoints")
    validation = validate_checkpoint_folder(
        plan.target_dir,
        mode=mode,
        min_size_bytes=min_size_bytes,
        compute_hashes=compute_hashes,
    )
    if not validation.ok:
        details = "; ".join(validation.errors + [f"missing {name}" for name in validation.missing])
        raise ValueError(f"Downloaded checkpoint validation failed: {details}")

    manifest = manifest_from_validation(validation)
    manifest_path = save_manifest(manifest, plan.target_dir / "checkpoint_manifest.json")
    update_settings(
        model_mode=mode,
        checkpoint_folder=str(plan.target_dir.resolve()),
        checkpoint_manifest=str(manifest_path.resolve()),
        trusted_manual_checkpoint_folder=False,
    )
    _emit(progress, "Model download complete")
    return DownloadResult(mode=mode, files=downloaded, validation=validation, manifest_path=manifest_path)


def _load_hf_download() -> Callable[..., str]:
    try:
        from huggingface_hub import hf_hub_download
    except Exception as exc:
        raise ImportError("huggingface-hub is required to download model checkpoints") from exc
    return hf_hub_download


def _emit(progress: ProgressCallback | None, message: str) -> None:
    if progress:
        progress(message)
