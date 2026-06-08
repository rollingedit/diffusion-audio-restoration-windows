from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import paths

HF_REPO_ID = "nvidia/audio_to_audio_schrodinger_bridge"

TWOSPLIT = [
    "ckpt/A2SB_twosplit_0.0_0.5_release.ckpt",
    "ckpt/A2SB_twosplit_0.5_1.0_release.ckpt",
]

ONESPLIT = [
    "ckpt/A2SB_onesplit_0.0_1.0_release.ckpt",
]

MODEL_FILES = {
    "twosplit": TWOSPLIT,
    "onesplit": ONESPLIT,
}

MIN_CKPT_SIZE_BYTES = 2_000_000_000


@dataclass(frozen=True)
class CheckpointFile:
    name: str
    path: Path
    size_bytes: int
    sha256: str | None = None


@dataclass(frozen=True)
class CheckpointValidation:
    ok: bool
    mode: str
    files: list[CheckpointFile]
    missing: list[str]
    errors: list[str]


def required_files(mode: str) -> list[str]:
    try:
        return MODEL_FILES[mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported model mode: {mode}") from exc


def expected_basename(filename: str) -> str:
    return Path(filename).name


def scan_checkpoint_folder(folder: Path, mode: str = "twosplit") -> list[Path]:
    folder = Path(folder)
    matches: list[Path] = []
    for rel_name in required_files(mode):
        basename = expected_basename(rel_name)
        direct = folder / rel_name
        nested = folder / basename
        if direct.exists():
            matches.append(direct)
        elif nested.exists():
            matches.append(nested)
    return matches


def validate_checkpoint_folder(
    folder: Path,
    mode: str = "twosplit",
    min_size_bytes: int = MIN_CKPT_SIZE_BYTES,
    compute_hashes: bool = False,
) -> CheckpointValidation:
    folder = Path(folder)
    files: list[CheckpointFile] = []
    missing: list[str] = []
    errors: list[str] = []

    for rel_name in required_files(mode):
        basename = expected_basename(rel_name)
        candidates = [folder / rel_name, folder / basename]
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if path is None:
            missing.append(basename)
            continue

        if path.suffix.lower() != ".ckpt":
            errors.append(f"{path} is not a .ckpt file")
            continue

        if not path.is_file():
            errors.append(f"{path} is not a file")
            continue

        size = path.stat().st_size
        if size < min_size_bytes:
            errors.append(f"{path.name} is too small: {size} bytes")
            continue

        digest = sha256_file(path) if compute_hashes else None
        files.append(CheckpointFile(name=basename, path=path.resolve(), size_bytes=size, sha256=digest))

    return CheckpointValidation(
        ok=not missing and not errors,
        mode=mode,
        files=files,
        missing=missing,
        errors=errors,
    )


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_from_validation(validation: CheckpointValidation, source: str = f"huggingface:{HF_REPO_ID}") -> dict:
    return {
        "model_mode": validation.mode,
        "source": source,
        "revision": "main",
        "files": [
            {
                "name": file.name,
                "path": str(file.path),
                "size_bytes": file.size_bytes,
                "sha256": file.sha256,
            }
            for file in validation.files
        ],
    }


def save_manifest(manifest: dict, path: Path | None = None) -> Path:
    target = path or (paths.models_dir() / "checkpoint_manifest.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def checkpoint_paths_from_validation(validation: CheckpointValidation) -> list[Path]:
    if not validation.ok:
        details = "; ".join(validation.errors + [f"missing {name}" for name in validation.missing])
        raise ValueError(f"Checkpoint validation failed: {details}")
    ordered: list[Path] = []
    by_name = {file.name: file.path for file in validation.files}
    for rel_name in required_files(validation.mode):
        ordered.append(by_name[expected_basename(rel_name)])
    return ordered


def trusted_manual_checkpoint_warning() -> str:
    return (
        "PyTorch checkpoint files can execute code when loaded. Only use checkpoint "
        "files from NVIDIA's official Hugging Face repository or another source you trust."
    )


def select_manual_checkpoint_folder(
    folder: Path,
    mode: str = "twosplit",
    trusted: bool = False,
    min_size_bytes: int = MIN_CKPT_SIZE_BYTES,
    compute_hashes: bool = True,
) -> tuple[CheckpointValidation, Path]:
    if not trusted:
        raise PermissionError(trusted_manual_checkpoint_warning())

    validation = validate_checkpoint_folder(
        folder,
        mode=mode,
        min_size_bytes=min_size_bytes,
        compute_hashes=compute_hashes,
    )
    if not validation.ok:
        details = "; ".join(validation.errors + [f"missing {name}" for name in validation.missing])
        raise ValueError(f"Checkpoint validation failed: {details}")

    manifest = manifest_from_validation(validation, source="manual-trusted")
    manifest_path = save_manifest(manifest, Path(folder) / "checkpoint_manifest.json")

    from .settings import update_settings

    update_settings(
        model_mode=mode,
        checkpoint_folder=str(Path(folder).resolve()),
        checkpoint_manifest=str(manifest_path.resolve()),
        trusted_manual_checkpoint_folder=True,
    )
    return validation, manifest_path
