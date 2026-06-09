from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import quote

from . import paths
from .checkpoint_manager import (
    HF_REPO_ID,
    MODEL_FILES,
    CheckpointValidation,
    expected_basename,
    manifest_from_validation,
    save_manifest,
    validate_checkpoint_folder,
)
from .settings import update_settings

ProgressCallback = Callable[[str], None]
ByteProgressCallback = Callable[[int, int, str], None]


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
    byte_progress: ByteProgressCallback | None = None,
    compute_hashes: bool = True,
    force: bool = False,
    min_size_bytes: int = 2_000_000_000,
    hf_download: Callable[..., str] | None = None,
    retries: int = 3,
) -> DownloadResult:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    if retries < 1:
        raise ValueError("retries must be at least 1")

    plan = build_download_plan(mode=mode, target_dir=target_dir)
    downloaded: list[Path] = []

    if not force:
        existing_result = reuse_existing_model(
            mode=mode,
            target_dir=plan.target_dir,
            progress=progress,
            byte_progress=byte_progress,
            min_size_bytes=min_size_bytes,
        )
        if existing_result is not None:
            return existing_result

    if not plan.enough_space and not force:
        raise OSError(
            f"Not enough free disk space for {mode} checkpoints. "
            f"Need about {plan.required_bytes} bytes, have {plan.free_bytes} bytes."
        )

    downloader = hf_download
    downloaded_before_file = 0
    for index, filename in enumerate(plan.filenames, start=1):
        _emit(progress, f"Downloading checkpoint {index} of {len(plan.filenames)}: {Path(filename).name}")
        if downloader is None:
            file_total_holder = {"total": 0}

            def aggregate_progress(current: int, total: int, label: str) -> None:
                file_total_holder["total"] = max(file_total_holder["total"], total)
                overall_total = _download_progress_total(plan, total)
                _emit_bytes(byte_progress, min(downloaded_before_file + current, overall_total), overall_total, label)

            path = _stream_download_with_retries(
                filename=filename,
                plan=plan,
                retries=retries,
                progress=progress,
                byte_progress=aggregate_progress,
            )
            downloaded_before_file += file_total_holder["total"] or Path(path).stat().st_size
        else:
            path = _download_with_retries(
                downloader,
                filename=filename,
                plan=plan,
                retries=retries,
                progress=progress,
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

    manifest_path = _save_official_model_settings(mode, plan.target_dir, validation)
    _emit(progress, "Model download complete")
    return DownloadResult(mode=mode, files=downloaded, validation=validation, manifest_path=manifest_path)


def reuse_existing_model(
    mode: str = "twosplit",
    target_dir: Path | None = None,
    progress: ProgressCallback | None = None,
    byte_progress: ByteProgressCallback | None = None,
    min_size_bytes: int = 2_000_000_000,
) -> DownloadResult | None:
    plan = build_download_plan(mode=mode, target_dir=target_dir)
    existing = validate_checkpoint_folder(
        plan.target_dir,
        mode=mode,
        min_size_bytes=min_size_bytes,
        compute_hashes=False,
    )
    if existing.ok:
        manifest_path = _save_official_model_settings(mode, plan.target_dir, existing)
        _emit(progress, "Model checkpoints already present")
        return DownloadResult(mode=mode, files=[file.path for file in existing.files], validation=existing, manifest_path=manifest_path)

    return _reuse_discovered_checkpoints(
        plan=plan,
        progress=progress,
        byte_progress=byte_progress,
        min_size_bytes=min_size_bytes,
    )


def _load_hf_download() -> Callable[..., str]:
    try:
        from huggingface_hub import hf_hub_download
    except Exception as exc:
        raise ImportError("huggingface-hub is required to download model checkpoints") from exc
    return hf_hub_download


def _download_with_retries(
    downloader: Callable[..., str],
    filename: str,
    plan: DownloadPlan,
    retries: int,
    progress: ProgressCallback | None,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return downloader(
                repo_id=plan.repo_id,
                filename=filename,
                local_dir=str(plan.target_dir),
                local_dir_use_symlinks=False,
                resume_download=True,
            )
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            _emit(progress, f"Download failed for {Path(filename).name}; retrying {attempt + 1} of {retries}: {exc}")
    raise RuntimeError(f"Failed to download {filename} after {retries} attempts: {last_error}") from last_error


def _stream_download_with_retries(
    filename: str,
    plan: DownloadPlan,
    retries: int,
    progress: ProgressCallback | None,
    byte_progress: ByteProgressCallback | None,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return _stream_download_file(filename=filename, plan=plan, byte_progress=byte_progress)
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            _emit(progress, f"Download failed for {Path(filename).name}; retrying {attempt + 1} of {retries}: {exc}")
    raise RuntimeError(f"Failed to download {filename} after {retries} attempts: {last_error}") from last_error


def _stream_download_file(
    filename: str,
    plan: DownloadPlan,
    byte_progress: ByteProgressCallback | None,
    chunk_size: int = 1024 * 1024,
) -> str:
    try:
        import requests
    except Exception as exc:
        raise ImportError("requests is required to download model checkpoints") from exc

    target = plan.target_dir / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    url = f"https://huggingface.co/{plan.repo_id}/resolve/main/{quote(filename)}"
    headers: dict[str, str] = {}
    start = partial.stat().st_size if partial.exists() else 0
    if start:
        headers["Range"] = f"bytes={start}-"

    with requests.get(url, stream=True, headers=headers, timeout=(15, 60), allow_redirects=True) as response:
        if response.status_code not in (200, 206):
            raise RuntimeError(f"HTTP {response.status_code} from Hugging Face for {Path(filename).name}")
        if response.status_code == 200 and start:
            start = 0
        total = _response_total_bytes(response, start)
        mode = "ab" if start and response.status_code == 206 else "wb"
        downloaded = start
        _emit_bytes(byte_progress, downloaded, total, Path(filename).name)
        with partial.open(mode) as handle:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded += len(chunk)
                _emit_bytes(byte_progress, downloaded, total, Path(filename).name)

    partial.replace(target)
    _emit_bytes(byte_progress, target.stat().st_size, total, Path(filename).name)
    return str(target)


def _response_total_bytes(response, start: int) -> int:
    content_range = response.headers.get("Content-Range", "")
    if "/" in content_range:
        try:
            return int(content_range.rsplit("/", 1)[1])
        except ValueError:
            pass
    content_length = response.headers.get("Content-Length")
    if content_length and content_length.isdigit():
        return start + int(content_length)
    return 0


def _download_progress_total(plan: DownloadPlan, current_file_total: int) -> int:
    if current_file_total <= 0:
        return plan.required_bytes
    return current_file_total * len(plan.filenames)


def _reuse_discovered_checkpoints(
    plan: DownloadPlan,
    progress: ProgressCallback | None,
    byte_progress: ByteProgressCallback | None,
    min_size_bytes: int,
) -> DownloadResult | None:
    candidates = _discover_existing_checkpoint_files(plan, min_size_bytes=min_size_bytes)
    if len(candidates) != len(plan.filenames):
        return None

    discovered_folder = _common_checkpoint_folder(candidates.values(), plan.mode, min_size_bytes)
    if discovered_folder is not None:
        validation = validate_checkpoint_folder(
            discovered_folder,
            mode=plan.mode,
            min_size_bytes=min_size_bytes,
            compute_hashes=False,
        )
        manifest_path = _save_official_model_settings(plan.mode, discovered_folder, validation)
        _emit(progress, f"Found existing checkpoint folder: {discovered_folder}")
        _emit(progress, "Using existing checkpoints; no download needed")
        return DownloadResult(
            mode=plan.mode,
            files=[file.path for file in validation.files],
            validation=validation,
            manifest_path=manifest_path,
        )

    copied: list[Path] = []
    for filename in plan.filenames:
        source = candidates[expected_basename(filename)]
        target = plan.target_dir / filename
        if source.resolve() == target.resolve():
            copied.append(target)
            continue
        _emit(progress, f"Found existing checkpoint: {source}")
        _emit(progress, f"Copying existing checkpoint into model folder: {target.name}")
        _copy_file_with_progress(source, target, byte_progress)
        copied.append(target)

    validation = validate_checkpoint_folder(
        plan.target_dir,
        mode=plan.mode,
        min_size_bytes=min_size_bytes,
        compute_hashes=False,
    )
    if not validation.ok:
        return None

    manifest_path = _save_official_model_settings(plan.mode, plan.target_dir, validation)
    _emit(progress, "Using existing checkpoints; no download needed")
    return DownloadResult(mode=plan.mode, files=copied, validation=validation, manifest_path=manifest_path)


def _common_checkpoint_folder(files: Iterable[Path], mode: str, min_size_bytes: int) -> Path | None:
    roots: set[Path] = set()
    for file in files:
        parent = file.parent
        root = parent.parent if parent.name.lower() == "ckpt" else parent
        roots.add(root.resolve())
    if len(roots) != 1:
        return None
    root = next(iter(roots))
    validation = validate_checkpoint_folder(root, mode=mode, min_size_bytes=min_size_bytes, compute_hashes=False)
    return root if validation.ok else None


def _discover_existing_checkpoint_files(plan: DownloadPlan, min_size_bytes: int) -> dict[str, Path]:
    found: dict[str, Path] = {}
    expected = {expected_basename(filename) for filename in plan.filenames}
    for root in _candidate_checkpoint_roots(plan.target_dir):
        if not root.exists():
            continue
        for basename in expected - set(found):
            direct_candidates = [root / basename, root / "ckpt" / basename]
            match = next((candidate for candidate in direct_candidates if _looks_like_checkpoint(candidate, min_size_bytes)), None)
            if match is None:
                match = next((candidate for candidate in root.rglob(basename) if _looks_like_checkpoint(candidate, min_size_bytes)), None)
            if match is not None:
                found[basename] = match.resolve()
        if len(found) == len(expected):
            break
    return found


def _candidate_checkpoint_roots(target_dir: Path) -> Iterable[Path]:
    roots = [
        target_dir,
        paths.models_dir(),
        paths.app_data_dir() / "models",
        paths.app_install_dir() / ".local_app_data" / paths.APP_NAME / "models",
        paths.app_install_dir() / ".local_downloads",
    ]
    for drive in "DEFGHIJKLMNOPQRSTUVWXYZ":
        roots.extend(
            [
                Path(f"{drive}:\\_github\\diffusion-audio-restoration-windows\\.local_app_data\\{paths.APP_NAME}\\models"),
                Path(f"{drive}:\\_github\\diffusion-audio-restoration-windows\\.local_downloads"),
            ]
        )
    for env_name in ["HF_HOME", "HUGGINGFACE_HUB_CACHE"]:
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value).expanduser())

    seen: set[Path] = set()
    for root in roots:
        resolved = Path(root).expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield resolved


def _looks_like_checkpoint(path: Path, min_size_bytes: int) -> bool:
    return path.is_file() and path.suffix.lower() == ".ckpt" and path.stat().st_size >= min_size_bytes


def _copy_file_with_progress(source: Path, target: Path, byte_progress: ByteProgressCallback | None) -> None:
    total = source.stat().st_size
    copied = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    with source.open("rb") as reader, partial.open("wb") as writer:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            writer.write(chunk)
            copied += len(chunk)
            _emit_bytes(byte_progress, copied, total, source.name)
    partial.replace(target)


def _save_official_model_settings(mode: str, target_dir: Path, validation: CheckpointValidation) -> Path:
    manifest = manifest_from_validation(validation)
    manifest_path = save_manifest(manifest, target_dir / "checkpoint_manifest.json")
    update_settings(
        model_mode=mode,
        checkpoint_folder=str(target_dir.resolve()),
        checkpoint_manifest=str(manifest_path.resolve()),
        trusted_manual_checkpoint_folder=False,
    )
    return manifest_path


def _emit(progress: ProgressCallback | None, message: str) -> None:
    if progress:
        progress(message)


def _emit_bytes(progress: ByteProgressCallback | None, current: int, total: int, label: str) -> None:
    if progress:
        progress(current, total, label)
