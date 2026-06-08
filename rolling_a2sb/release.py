from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


RELEASE_BLOCKED_TEXT = "Do not publish release artifacts"
MIN_SETUP_EXE_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
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
        if artifact.name == "A2SB-Restorer-Setup.exe":
            if artifact.stat().st_size < MIN_SETUP_EXE_BYTES:
                errors.append("A2SB-Restorer-Setup.exe is too small to be a real installer artifact")
            with artifact.open("rb") as handle:
                if handle.read(2) != b"MZ":
                    errors.append("A2SB-Restorer-Setup.exe is not a Windows executable")
        if artifact.suffix.lower() == ".ckpt":
            errors.append(f"Checkpoint file must not be a release artifact: {artifact.name}")
        if artifact.name.lower().endswith((".pt", ".pth", ".safetensors")):
            errors.append(f"Model weight file must not be a release artifact: {artifact.name}")
        if artifact.name in {"README-WINDOWS.md", "LICENSE-NOTICES.txt"}:
            text = artifact.read_text(encoding="utf-8", errors="replace")
            if "release-source placeholder" in text or RELEASE_BLOCKED_TEXT in text:
                errors.append(f"Release artifact still contains blocking placeholder text: {artifact.name}")

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
    elif artifacts:
        checksum_entries, checksum_errors = parse_checksum_file(checksums)
        errors.extend(checksum_errors)
        checksum_names = set(checksum_entries)
        for artifact in artifacts:
            if artifact.name not in checksum_names:
                errors.append(f"SHA256SUMS.txt is missing artifact entry: {artifact.name}")
            elif checksum_entries[artifact.name].lower() != sha256_file(artifact):
                errors.append(f"SHA256SUMS.txt hash does not match artifact: {artifact.name}")
        artifact_names = {artifact.name for artifact in artifacts}
        for entry in sorted(checksum_names - artifact_names):
            errors.append(f"SHA256SUMS.txt references missing artifact: {entry}")

    return ReleaseCheckResult(ok=not errors, errors=errors)


def parse_checksum_file(checksums_path: Path) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    errors: list[str] = []
    for line_number, line in enumerate(Path(checksums_path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            digest = parts[0].strip()
            name = parts[1].strip().lstrip("*")
            if not SHA256_RE.match(digest):
                errors.append(f"SHA256SUMS.txt line {line_number} has invalid SHA256 digest")
            if not name:
                errors.append(f"SHA256SUMS.txt line {line_number} has no artifact name")
            elif name in entries:
                errors.append(f"SHA256SUMS.txt has duplicate artifact entry: {name}")
            else:
                entries[name] = digest
        else:
            errors.append(f"SHA256SUMS.txt line {line_number} is malformed")
    return entries, errors


def checksum_artifact_hashes(checksums_path: Path) -> dict[str, str]:
    entries, _ = parse_checksum_file(checksums_path)
    return entries


def checksum_artifact_names(checksums_path: Path) -> set[str]:
    return set(checksum_artifact_hashes(checksums_path))
