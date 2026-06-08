from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


RELEASE_BLOCKED_TEXT = "Do not publish release artifacts"
REQUIRED_RELEASE_ARTIFACTS = [
    "A2SB-Restorer-Setup.exe",
    "README-WINDOWS.md",
    "LICENSE-NOTICES.txt",
]


@dataclass(frozen=True)
class ReleaseCheckResult:
    ok: bool
    errors: list[str]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256sums(files: list[Path], output_path: Path) -> Path:
    if not files:
        raise ValueError("No files were provided for SHA256SUMS generation.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for file_path in files:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Release artifact does not exist: {path}")
        digest = sha256_file(path)
        lines.append(f"{digest}  {path.name}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def collect_release_artifacts(folder: Path) -> list[Path]:
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted(path for path in folder.iterdir() if path.is_file() and path.name != "SHA256SUMS.txt")


def validate_release_artifacts(folder: Path, licenses_dir: Path) -> ReleaseCheckResult:
    errors: list[str] = []
    folder = Path(folder)
    licenses_dir = Path(licenses_dir)

    artifacts = collect_release_artifacts(folder)
    if not artifacts:
        errors.append(f"No release artifacts found in {folder}")

    artifact_names = {artifact.name for artifact in artifacts}
    for required in REQUIRED_RELEASE_ARTIFACTS:
        if required not in artifact_names:
            errors.append(f"Missing release artifact: {required}")

    for artifact in artifacts:
        if artifact.suffix.lower() == ".ckpt":
            errors.append(f"Checkpoint file must not be a release artifact: {artifact.name}")
        if artifact.name.lower().endswith((".pt", ".pth", ".safetensors")):
            errors.append(f"Model weight file must not be a release artifact: {artifact.name}")

    for notice in [
        "NVIDIA_A2SB_LICENSE.txt",
        "FFMPEG_NOTICE.txt",
        "PYTHON_NOTICE.txt",
    ]:
        path = licenses_dir / notice
        if not path.exists():
            errors.append(f"Missing license notice: {notice}")
            continue
        text = path.read_text(encoding="utf-8")
        if "Placeholder" in text or RELEASE_BLOCKED_TEXT in text:
            errors.append(f"License notice is still a release-blocking placeholder: {notice}")

    checksums = folder / "SHA256SUMS.txt"
    if artifacts and not checksums.exists():
        errors.append("SHA256SUMS.txt is missing")

    return ReleaseCheckResult(ok=not errors, errors=errors)
