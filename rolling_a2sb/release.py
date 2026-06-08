from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


RELEASE_BLOCKED_TEXT = "Do not publish release artifacts"
MIN_SETUP_EXE_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
BANNED_EVIDENCE_VALUES = {"assumed", "not applicable", "n/a", "na", "todo", "tbd"}
GENERIC_EVIDENCE_VALUES = {"builder", "tester", "test machine", "build machine", "test gpu", "nvidia test gpu"}
REQUIRED_RELEASE_ARTIFACTS = [
    "A2SB-Restorer-Setup.exe",
    "README-WINDOWS.md",
    "LICENSE-NOTICES.txt",
]
ALLOWED_RELEASE_ARTIFACTS = set(REQUIRED_RELEASE_ARTIFACTS)
REQUIRED_LICENSE_NOTICE_TOKENS = {
    "NVIDIA_A2SB_LICENSE.txt": ["NVIDIA", "copyright"],
    "FFMPEG_NOTICE.txt": ["FFmpeg", "BtbN", "LGPL", "https://github.com/BtbN/FFmpeg-Builds"],
    "PYTHON_NOTICE.txt": ["Python", "license", "https://www.python.org"],
}
REQUIRED_RELEASE_DOC_TOKENS = {
    "README-WINDOWS.md": [
        "nvidia/audio_to_audio_schrodinger_bridge",
        "Audio files stay",
        "does not upload user audio",
        "telemetry",
        "Hugging Face",
        "A2SB Restored",
        "Checkpoints",
        "must not be bundled",
    ],
    "LICENSE-NOTICES.txt": [
        "not affiliated with or endorsed by NVIDIA",
        "FFmpeg",
        "Python",
        "audio files stay local",
        "no telemetry",
    ],
}
REQUIRED_EVIDENCE_FIELDS = [
    "Version",
    "Git commit",
    "Build machine",
    "Test machine",
    "Windows version",
    "GPU model",
    "NVIDIA driver version",
    "CUDA reported by PyTorch",
    "Installer filename",
    "Installer SHA256",
    "FFmpeg build filename",
    "FFmpeg source URL",
]
REQUIRED_EVIDENCE_COMMAND_FIELDS = [
    "Runtime setup",
    "Repair runtime",
    "Doctor JSON",
    "Hugging Face checkpoint download",
    "Manual checkpoint selection",
    "CLI smoke restore",
    "Launcher build",
    "Installer build",
    "SHA256 generation",
    "Release validation",
]
REQUIRED_EVIDENCE_FILE_FIELDS = [
    "Doctor JSON path",
    "Doctor report path",
    "Setup status JSON path",
    "Checkpoint manifest path",
    "Restore job folder",
    "Restore log path",
    "Input test audio path",
    "Output WAV path",
    "Screenshot of ready Setup tab",
    "Screenshot of completed Restore tab",
    "Screenshot of Start Menu shortcuts",
    "Installer artifact folder",
    "Input file hash before restore",
    "Input file hash after restore",
    "Release artifacts validated",
]
EVIDENCE_SHA256_FIELDS = [
    "Installer SHA256",
    "Input file hash before restore",
    "Input file hash after restore",
]
REQUIRED_EVIDENCE_PASS_FIELDS = [
    "Clean install completed without admin",
    "First launch required no terminal",
    "Setup/repair required no manual Python, " + "Con" + "da, Git, W" + "SL, Do" + "cker, or YAML editing",
    "Doctor passed in installed runtime",
    "CUDA was visible through PyTorch",
    "Bundled FFmpeg and ffprobe were used",
    "Official two-split checkpoints downloaded from Hugging Face",
    "Restore produced a WAV",
    "Output WAV was 44.1 kHz mono",
    "Path-with-spaces restore passed",
    "Cancel left input and final output safe",
    "Missing checkpoint opened setup flow",
    "Uninstall removed app files",
    "Uninstall preserved user-downloaded models",
    "Release artifacts validated",
]
EVIDENCE_PATH_SUFFIXES = {
    "Doctor JSON path": (".json",),
    "Setup status JSON path": (".json",),
    "Checkpoint manifest path": (".json",),
    "Restore log path": (".log", ".txt"),
    "Input test audio path": (".wav", ".mp3", ".flac"),
    "Output WAV path": (".wav",),
    "Screenshot of ready Setup tab": (".png",),
    "Screenshot of completed Restore tab": (".png",),
    "Screenshot of Start Menu shortcuts": (".png",),
}
COMMAND_OUTPUT_FIELD_PAIRS = {
    "Runtime setup": "Setup status JSON path",
    "Doctor JSON": "Doctor JSON path",
    "Hugging Face checkpoint download": "Checkpoint manifest path",
    "CLI smoke restore": "Restore log path",
    "Launcher build": "Launcher build",
    "Installer build": "Installer filename",
    "SHA256 generation": "Installer artifact folder",
    "Release validation": "Release validation",
}
COMMAND_REQUIRED_TOKENS = {
    "Runtime setup": ("setup_runtime.ps1", "-json"),
    "Repair runtime": ("repair_runtime.ps1", "-json"),
    "Doctor JSON": ("doctor", "--json"),
    "Hugging Face checkpoint download": ("download-model", "--model", "twosplit", "--yes"),
    "Manual checkpoint selection": ("select-checkpoints", "--trust"),
    "CLI smoke restore": ("restore", "--input", "--steps"),
    "Launcher build": ("build_launcher.ps1",),
    "Installer build": ("build_installer.ps1",),
    "SHA256 generation": ("write_sha256sums.ps1", "dist/installer"),
    "Release validation": ("write_sha256sums.ps1", "dist/installer", "-validateonly"),
}


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
    source_root = licenses_dir.parent

    artifacts = collect_release_artifacts(folder)
    if not artifacts:
        errors.append(f"No release artifacts found in {folder}")

    installer_version = installer_release_version(source_root / "installer" / "a2sb-restorer.iss")
    project_version = project_release_version(source_root / "pyproject.toml")
    module_version = package_init_version(source_root / "rolling_a2sb" / "__init__.py")
    if project_version and module_version and project_version != module_version:
        errors.append("Python package version does not match rolling_a2sb.__version__")
    if installer_version and project_version and installer_version != project_version.replace("a0", "-alpha"):
        errors.append("Installer version does not match Python package release label")
    errors.extend(validate_runtime_lockfile(source_root / "requirements" / "lock-win-cu121.txt"))

    artifact_names = {artifact.name for artifact in artifacts}
    for required in REQUIRED_RELEASE_ARTIFACTS:
        if required not in artifact_names:
            errors.append(f"Missing release artifact: {required}")

    for artifact in artifacts:
        if artifact.name not in ALLOWED_RELEASE_ARTIFACTS:
            errors.append(f"Unexpected release artifact: {artifact.name}")
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
            if artifact.name == "README-WINDOWS.md" and "not public-release-ready" in text.lower():
                errors.append("README-WINDOWS.md still says the app is not public-release-ready")
            lowered = text.lower()
            for token in REQUIRED_RELEASE_DOC_TOKENS[artifact.name]:
                if token.lower() not in lowered:
                    errors.append(f"Release artifact is missing required public text: {artifact.name} ({token})")
            source_path = source_root / artifact.name
            if not source_path.exists():
                errors.append(f"Release source file is missing: {artifact.name}")
            elif artifact.read_bytes() != source_path.read_bytes():
                errors.append(f"Release artifact differs from source file: {artifact.name}")

    for notice in REQUIRED_LICENSE_NOTICE_TOKENS:
        path = licenses_dir / notice
        if not path.exists():
            errors.append(f"Missing license notice: {notice}")
            continue
        text = path.read_text(encoding="utf-8")
        if "Placeholder" in text or RELEASE_BLOCKED_TEXT in text:
            errors.append(f"License notice is still a release-blocking placeholder: {notice}")
        lowered = text.lower()
        for token in REQUIRED_LICENSE_NOTICE_TOKENS[notice]:
            if token.lower() not in lowered:
                errors.append(f"License notice is missing required release text: {notice} ({token})")

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

    setup_artifact = folder / "A2SB-Restorer-Setup.exe"
    expected_installer_sha256 = sha256_file(setup_artifact) if setup_artifact.exists() and setup_artifact.is_file() else None
    errors.extend(
        validate_release_evidence(
            source_root / "docs" / "RELEASE_EVIDENCE.md",
            expected_version=installer_version,
            expected_git_commit=git_head_commit(source_root),
            expected_installer_filename="A2SB-Restorer-Setup.exe",
            expected_installer_sha256=expected_installer_sha256,
        )
    )
    return ReleaseCheckResult(ok=not errors, errors=errors)


def validate_release_evidence(
    evidence_path: Path,
    expected_version: str | None = None,
    expected_git_commit: str | None = None,
    expected_installer_filename: str | None = None,
    expected_installer_sha256: str | None = None,
) -> list[str]:
    path = Path(evidence_path)
    if not path.exists():
        return [f"Release evidence file is missing: {path}"]

    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    values: dict[str, str] = {}
    required_fields = (
        REQUIRED_EVIDENCE_FIELDS
        + REQUIRED_EVIDENCE_COMMAND_FIELDS
        + REQUIRED_EVIDENCE_FILE_FIELDS
        + REQUIRED_EVIDENCE_PASS_FIELDS
    )
    for field in required_fields:
        pattern = re.compile(rf"^- {re.escape(field)}:[ \t]*(.*)$", re.MULTILINE)
        match = pattern.search(text)
        if not match or not match.group(1).strip():
            errors.append(f"Release evidence field is incomplete: {field}")
        elif match:
            values[field] = match.group(1).strip()
            if values[field].strip().lower() in BANNED_EVIDENCE_VALUES:
                errors.append(f"Release evidence field uses a placeholder value: {field}")

    for field in EVIDENCE_SHA256_FIELDS:
        value = values.get(field)
        if value and not SHA256_RE.match(value):
            errors.append(f"Release evidence field must be a SHA256 digest: {field}")
    errors.extend(validate_release_environment_values(values))
    for field, suffixes in EVIDENCE_PATH_SUFFIXES.items():
        value = values.get(field, "").lower()
        if value and not value.endswith(suffixes):
            errors.append(f"Release evidence path has unexpected file type: {field}")
    artifact_folder = values.get("Installer artifact folder", "").replace("\\", "/").rstrip("/").lower()
    if artifact_folder and not artifact_folder.endswith("dist/installer"):
        errors.append("Release evidence installer artifact folder must be dist/installer")
    for field in REQUIRED_EVIDENCE_COMMAND_FIELDS:
        command_evidence = values.get(field, "")
        if command_evidence and ("exit 0" not in command_evidence.lower() or command_evidence.count(";") < 2):
            errors.append(f"Release evidence command must include command, exit 0, and output path: {field}")
    errors.extend(validate_evidence_command_consistency(values))
    if expected_version and values.get("Version") != expected_version:
        errors.append("Release evidence version does not match installer version")
    if values.get("Git commit") and not GIT_SHA_RE.match(values["Git commit"]):
        errors.append("Release evidence Git commit must be a 7-40 character hex SHA")
    if expected_git_commit and values.get("Git commit") != expected_git_commit[: len(values.get("Git commit", ""))]:
        errors.append("Release evidence Git commit does not match repository HEAD")
    ffmpeg_filename = values.get("FFmpeg build filename", "").lower()
    if ffmpeg_filename and not ("win64" in ffmpeg_filename and "lgpl" in ffmpeg_filename and ffmpeg_filename.endswith(".zip")):
        errors.append("Release evidence FFmpeg build filename must be a Windows x64 LGPL ZIP")
    ffmpeg_source_url = values.get("FFmpeg source URL", "")
    if ffmpeg_source_url and not ffmpeg_source_url.startswith("https://github.com/BtbN/FFmpeg-Builds"):
        errors.append("Release evidence FFmpeg source URL must use the approved BtbN FFmpeg Builds source")
    before_hash = values.get("Input file hash before restore")
    after_hash = values.get("Input file hash after restore")
    if before_hash and after_hash and before_hash.lower() != after_hash.lower():
        errors.append("Release evidence input hash changed during restore")
    for field in REQUIRED_EVIDENCE_PASS_FIELDS:
        if values.get(field, "").lower() not in {"yes", "true", "passed"}:
            errors.append(f"Release evidence must mark required result as passed: {field}")
    if expected_installer_filename and values.get("Installer filename") != expected_installer_filename:
        errors.append("Release evidence installer filename does not match staged artifact")
    if expected_installer_sha256 and values.get("Installer SHA256", "").lower() != expected_installer_sha256.lower():
        errors.append("Release evidence installer SHA256 does not match staged artifact")

    blockers = re.search(r"## Blockers\s*(.*)\Z", text, flags=re.DOTALL)
    blocker_lines = []
    if blockers:
        blocker_lines = [line.strip() for line in blockers.group(1).splitlines() if line.strip().startswith("-")]
    if blocker_lines != ["- None"]:
        errors.append('Release evidence blockers must be exactly "- None" before public release')
    return errors


def validate_release_environment_values(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for field in ["Build machine", "Test machine", "GPU model"]:
        value = values.get(field, "").strip()
        if value.lower() in GENERIC_EVIDENCE_VALUES or len(value) < 8:
            errors.append(f"Release evidence field is too generic: {field}")

    windows_version = values.get("Windows version", "")
    if windows_version and not re.search(r"\bWindows\s+(10|11)\b", windows_version, flags=re.IGNORECASE):
        errors.append("Release evidence Windows version must name Windows 10 or Windows 11")

    gpu_model = values.get("GPU model", "")
    if gpu_model and not re.search(r"\b(NVIDIA|RTX|GTX|Quadro|Tesla)\b", gpu_model, flags=re.IGNORECASE):
        errors.append("Release evidence GPU model must name an NVIDIA GPU")

    driver_version = values.get("NVIDIA driver version", "")
    if driver_version and not re.search(r"\d{3,}\.\d+", driver_version):
        errors.append("Release evidence NVIDIA driver version must look like a driver version")

    cuda_version = values.get("CUDA reported by PyTorch", "")
    if cuda_version and not re.search(r"\d+\.\d+", cuda_version):
        errors.append("Release evidence CUDA version must look like a numeric CUDA version")
    return errors


def validate_evidence_command_consistency(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for command_field, required_tokens in COMMAND_REQUIRED_TOKENS.items():
        command_text, _ = split_command_evidence(values.get(command_field, ""))
        normalized_command = normalize_evidence_path(command_text)
        for token in required_tokens:
            if token not in normalized_command:
                errors.append(f"Release evidence command is not the expected release command: {command_field}")
                break

    for command_field, evidence_field in COMMAND_OUTPUT_FIELD_PAIRS.items():
        command_evidence = values.get(command_field)
        if not command_evidence:
            continue
        command_text, output_path = split_command_evidence(command_evidence)
        if not output_path:
            continue
        if evidence_field == "Launcher build":
            if not output_path.replace("\\", "/").endswith("dist/A2SB Restorer/A2SB Restorer.exe"):
                errors.append("Release evidence launcher build output must be dist/A2SB Restorer/A2SB Restorer.exe")
            continue
        if evidence_field == "Installer filename":
            if Path(output_path.replace("\\", "/")).name != values.get(evidence_field):
                errors.append("Release evidence installer build output does not match installer filename")
            continue
        if evidence_field == "Installer artifact folder":
            if not output_path.replace("\\", "/").endswith("dist/installer/SHA256SUMS.txt"):
                errors.append("Release evidence SHA256 generation output must be dist/installer/SHA256SUMS.txt")
            continue
        if evidence_field == "Release validation":
            if "-validateonly" not in command_text.lower():
                errors.append("Release evidence validation command must use -ValidateOnly")
            continue
        if values.get(evidence_field) and normalize_evidence_path(output_path) != normalize_evidence_path(values[evidence_field]):
            errors.append(f"Release evidence command output does not match evidence path: {command_field}")

    sha_command, _ = split_command_evidence(values.get("SHA256 generation", ""))
    if "-validateonly" in sha_command.lower():
        errors.append("Release evidence SHA256 generation command must not use -ValidateOnly")
    return errors


def split_command_evidence(command_evidence: str) -> tuple[str, str]:
    parts = [part.strip() for part in command_evidence.split(";")]
    if len(parts) < 3:
        return command_evidence.strip(), ""
    return parts[0], parts[-1]


def normalize_evidence_path(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").lower()


def installer_release_version(installer_path: Path) -> str | None:
    path = Path(installer_path)
    if not path.exists():
        return None
    match = re.search(r'^#define MyAppVersion "([^"]+)"$', path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    return match.group(1) if match else None


def project_release_version(pyproject_path: Path) -> str | None:
    path = Path(pyproject_path)
    if not path.exists():
        return None
    match = re.search(r'^version = "([^"]+)"$', path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    return match.group(1) if match else None


def package_init_version(init_path: Path) -> str | None:
    path = Path(init_path)
    if not path.exists():
        return None
    match = re.search(r'^__version__ = "([^"]+)"$', path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    return match.group(1) if match else None


def validate_runtime_lockfile(lockfile_path: Path) -> list[str]:
    path = Path(lockfile_path)
    if not path.exists():
        return ["Runtime lockfile is missing: requirements/lock-win-cu121.txt"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if "Placeholder" in text or RELEASE_BLOCKED_TEXT in text:
        errors.append("Runtime lockfile is still a release-blocking placeholder")
    lower_lines = {line.strip().lower() for line in text.splitlines()}
    for requirement in ["torch==2.2.2+cu121", "torchaudio==2.2.2+cu121", "numpy==1.26.4"]:
        if requirement not in lower_lines:
            errors.append(f"Runtime lockfile is missing pinned requirement: {requirement}")
    return errors


def git_head_commit(source_root: Path) -> str | None:
    git_dir = Path(source_root) / ".git"
    head_path = git_dir / "HEAD"
    if not head_path.exists():
        return None
    head = head_path.read_text(encoding="utf-8").strip()
    if GIT_SHA_RE.match(head):
        return head.lower()
    prefix = "ref: "
    if not head.startswith(prefix):
        return None
    ref_name = head[len(prefix) :]
    ref_path = git_dir / ref_name
    if ref_path.exists():
        ref = ref_path.read_text(encoding="utf-8").strip()
        return ref.lower() if GIT_SHA_RE.match(ref) else None
    packed_refs = git_dir / "packed-refs"
    if packed_refs.exists():
        for line in packed_refs.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith(("#", "^")):
                continue
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref_name and GIT_SHA_RE.match(parts[0]):
                return parts[0].lower()
    return None


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
