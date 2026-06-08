from pathlib import Path

from rolling_a2sb.release import (
    ALLOWED_RELEASE_ARTIFACTS,
    MIN_SETUP_EXE_BYTES,
    checksum_artifact_hashes,
    checksum_artifact_names,
    collect_release_artifacts,
    git_head_commit,
    installer_release_version,
    parse_checksum_file,
    sha256_file,
    validate_release_artifacts,
    validate_release_evidence,
    write_sha256sums,
)


def write_notices(licenses_dir: Path, placeholder: bool = False) -> None:
    licenses_dir.mkdir(parents=True, exist_ok=True)
    text = "Placeholder\nDo not publish release artifacts\n" if placeholder else "Final notice text\n"
    for name in [
        "NVIDIA_A2SB_LICENSE.txt",
        "FFMPEG_NOTICE.txt",
        "PYTHON_NOTICE.txt",
    ]:
        (licenses_dir / name).write_text(text, encoding="utf-8")


def write_setup_exe(path: Path) -> None:
    path.write_bytes(b"MZ" + b"\0" * (MIN_SETUP_EXE_BYTES - 2))


def write_release_sources(root: Path, readme_text: str = "readme", notices_text: str = "notices") -> None:
    (root / "README-WINDOWS.md").write_text(readme_text, encoding="utf-8")
    (root / "LICENSE-NOTICES.txt").write_text(notices_text, encoding="utf-8")


def write_release_evidence(
    root: Path,
    blockers: str = "- None",
    installer_filename: str = "A2SB-Restorer-Setup.exe",
    installer_sha256: str | None = None,
) -> Path:
    evidence = root / "docs" / "RELEASE_EVIDENCE.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    installer_sha256 = installer_sha256 or "a" * 64
    evidence.write_text(
        "\n".join(
            [
                "# Release Evidence",
                "",
                "## Release Candidate",
                "",
                "- Version: 0.1.0-alpha",
                "- Git commit: abc1234",
                "- Build machine: builder",
                "- Test machine: tester",
                "- Windows version: Windows 11 23H2",
                "- GPU model: NVIDIA test GPU",
                "- NVIDIA driver version: 555.55",
                "- CUDA reported by PyTorch: 12.1",
                f"- Installer filename: {installer_filename}",
                f"- Installer SHA256: {installer_sha256}",
                "- FFmpeg build filename: ffmpeg-master-latest-win64-lgpl.zip",
                "- FFmpeg source URL: https://github.com/BtbN/FFmpeg-Builds",
                "",
                "## Commands",
                "",
                "- Runtime setup: powershell -ExecutionPolicy Bypass -File scripts/setup_runtime.ps1 -Json; exit 0; evidence/setup_status.json",
                "- Repair runtime: powershell -ExecutionPolicy Bypass -File scripts/repair_runtime.ps1 -Json; exit 0; evidence/repair_status.json",
                "- Doctor JSON: .venv/Scripts/python.exe -m rolling_a2sb.cli doctor --json; exit 0; evidence/doctor.json",
                "- Hugging Face checkpoint download: a2sb download-model --model twosplit --yes; exit 0; evidence/checkpoint_manifest.json",
                "- Manual checkpoint selection: a2sb select-checkpoints evidence/models --trust; exit 0; evidence/manual_manifest.json",
                "- CLI smoke restore: a2sb restore --input evidence/input.wav --steps 2; exit 0; evidence/restore.log",
                "- Launcher build: powershell -ExecutionPolicy Bypass -File scripts/build_launcher.ps1; exit 0; dist/A2SB Restorer/A2SB Restorer.exe",
                "- Installer build: powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1; exit 0; dist/installer/A2SB-Restorer-Setup.exe",
                "- SHA256 generation: powershell -ExecutionPolicy Bypass -File scripts/write_sha256sums.ps1 -ArtifactsDir dist/installer; exit 0; dist/installer/SHA256SUMS.txt",
                "- Release validation: powershell -ExecutionPolicy Bypass -File scripts/write_sha256sums.ps1 -ArtifactsDir dist/installer -ValidateOnly; exit 0; evidence/release_validation.txt",
                "",
                "## Evidence Files",
                "",
                "- Doctor JSON path: evidence/doctor.json",
                "- Doctor report path: evidence/doctor.txt",
                "- Setup status JSON path: evidence/setup_status.json",
                "- Checkpoint manifest path: evidence/checkpoint_manifest.json",
                "- Restore job folder: evidence/jobs/20260608-120000",
                "- Restore log path: evidence/restore.log",
                "- Input test audio path: evidence/input.wav",
                "- Output WAV path: evidence/out.wav",
                "- Screenshot of ready Setup tab: evidence/setup-ready.png",
                "- Screenshot of completed Restore tab: evidence/restore-complete.png",
                "- Screenshot of Start Menu shortcuts: evidence/start-menu.png",
                "- Installer artifact folder: dist/installer",
                "- Input file hash before restore: " + "b" * 64,
                "- Input file hash after restore: " + "b" * 64,
                "- Release artifacts validated: yes",
                "- Clean install completed without admin: yes",
                "- First launch required no terminal: yes",
                "- Setup/repair required no manual Python, Conda, Git, WSL, Docker, or YAML editing: yes",
                "- Doctor passed in installed runtime: yes",
                "- CUDA was visible through PyTorch: yes",
                "- Bundled FFmpeg and ffprobe were used: yes",
                "- Official two-split checkpoints downloaded from Hugging Face: yes",
                "- Restore produced a WAV: yes",
                "- Output WAV was 44.1 kHz mono: yes",
                "- Path-with-spaces restore passed: yes",
                "- Cancel left input and final output safe: yes",
                "- Missing checkpoint opened setup flow: yes",
                "- Uninstall removed app files: yes",
                "- Uninstall preserved user-downloaded models: yes",
                "",
                "## Blockers",
                "",
                blockers,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return evidence


def test_allowed_release_artifacts_match_public_payload() -> None:
    assert ALLOWED_RELEASE_ARTIFACTS == {
        "A2SB-Restorer-Setup.exe",
        "README-WINDOWS.md",
        "LICENSE-NOTICES.txt",
    }


def test_write_sha256sums(tmp_path: Path) -> None:
    artifact = tmp_path / "A2SB-Restorer-Setup.exe"
    artifact.write_bytes(b"installer")

    output = write_sha256sums([artifact], tmp_path / "SHA256SUMS.txt")

    text = output.read_text(encoding="utf-8")
    assert "A2SB-Restorer-Setup.exe" in text
    assert len(text.split()[0]) == 64


def test_collect_release_artifacts_excludes_sha_file(tmp_path: Path) -> None:
    artifact = tmp_path / "A2SB-Restorer-Setup.exe"
    sums = tmp_path / "SHA256SUMS.txt"
    artifact.write_bytes(b"installer")
    sums.write_text("hash  file\n", encoding="utf-8")

    assert collect_release_artifacts(tmp_path) == [artifact]


def test_checksum_artifact_names_parses_generated_checksum_file(tmp_path: Path) -> None:
    checksums = tmp_path / "SHA256SUMS.txt"
    checksums.write_text(
        "0" * 64 + "  A2SB-Restorer-Setup.exe\n" + "1" * 64 + "  *README-WINDOWS.md\n",
        encoding="utf-8",
    )

    assert checksum_artifact_names(checksums) == {"A2SB-Restorer-Setup.exe", "README-WINDOWS.md"}


def test_checksum_artifact_hashes_preserves_expected_hashes(tmp_path: Path) -> None:
    checksums = tmp_path / "SHA256SUMS.txt"
    checksums.write_text(
        "0" * 64 + "  A2SB-Restorer-Setup.exe\n" + "1" * 64 + "  *README-WINDOWS.md\n",
        encoding="utf-8",
    )

    assert checksum_artifact_hashes(checksums) == {
        "A2SB-Restorer-Setup.exe": "0" * 64,
        "README-WINDOWS.md": "1" * 64,
    }


def test_parse_checksum_file_reports_malformed_lines_invalid_hashes_and_duplicates(tmp_path: Path) -> None:
    checksums = tmp_path / "SHA256SUMS.txt"
    checksums.write_text(
        "not-a-hash  A2SB-Restorer-Setup.exe\n"
        "malformed\n"
        + "1" * 64
        + "  README-WINDOWS.md\n"
        + "2" * 64
        + "  README-WINDOWS.md\n",
        encoding="utf-8",
    )

    entries, errors = parse_checksum_file(checksums)

    assert entries == {
        "A2SB-Restorer-Setup.exe": "not-a-hash",
        "README-WINDOWS.md": "1" * 64,
    }
    assert "SHA256SUMS.txt line 1 has invalid SHA256 digest" in errors
    assert "SHA256SUMS.txt line 2 is malformed" in errors
    assert "SHA256SUMS.txt has duplicate artifact entry: README-WINDOWS.md" in errors


def test_validate_release_evidence_accepts_completed_evidence(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path)

    assert validate_release_evidence(evidence) == []


def test_validate_release_evidence_rejects_blank_fields_and_open_blockers(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path, blockers="- CUDA smoke test still missing")
    text = evidence.read_text(encoding="utf-8").replace("- GPU model: NVIDIA test GPU", "- GPU model:")
    evidence.write_text(text, encoding="utf-8")

    errors = validate_release_evidence(evidence)

    assert "Release evidence field is incomplete: GPU model" in errors
    assert 'Release evidence blockers must be exactly "- None" before public release' in errors


def test_validate_release_evidence_rejects_placeholder_field_values(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path)
    text = evidence.read_text(encoding="utf-8").replace("- Test machine: tester", "- Test machine: assumed")
    evidence.write_text(text, encoding="utf-8")

    errors = validate_release_evidence(evidence)

    assert "Release evidence field uses a placeholder value: Test machine" in errors


def test_validate_release_evidence_rejects_incomplete_command_records(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path)
    text = evidence.read_text(encoding="utf-8").replace(
        "- Doctor JSON: .venv/Scripts/python.exe -m rolling_a2sb.cli doctor --json; exit 0; evidence/doctor.json",
        "- Doctor JSON: .venv/Scripts/python.exe -m rolling_a2sb.cli doctor --json",
    )
    evidence.write_text(text, encoding="utf-8")

    errors = validate_release_evidence(evidence)

    assert "Release evidence command must include command, exit 0, and output path: Doctor JSON" in errors


def test_validate_release_evidence_rejects_weak_hash_and_validation_values(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path)
    text = evidence.read_text(encoding="utf-8")
    text = text.replace("- Installer SHA256: " + "a" * 64, "- Installer SHA256: not-a-hash")
    text = text.replace("- Input file hash after restore: " + "b" * 64, "- Input file hash after restore: " + "c" * 64)
    text = text.replace("- Release artifacts validated: yes", "- Release artifacts validated: not yet")
    evidence.write_text(text, encoding="utf-8")

    errors = validate_release_evidence(evidence)

    assert "Release evidence field must be a SHA256 digest: Installer SHA256" in errors
    assert "Release evidence input hash changed during restore" in errors
    assert "Release evidence must mark required result as passed: Release artifacts validated" in errors


def test_validate_release_evidence_rejects_installer_artifact_mismatch(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path, installer_filename="wrong.exe", installer_sha256="c" * 64)

    errors = validate_release_evidence(
        evidence,
        expected_installer_filename="A2SB-Restorer-Setup.exe",
        expected_installer_sha256="d" * 64,
    )

    assert "Release evidence installer filename does not match staged artifact" in errors
    assert "Release evidence installer SHA256 does not match staged artifact" in errors


def test_validate_release_evidence_rejects_version_and_commit_mismatch(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path)
    text = evidence.read_text(encoding="utf-8")
    text = text.replace("- Version: 0.1.0-alpha", "- Version: 9.9.9")
    text = text.replace("- Git commit: abc1234", "- Git commit: not-a-sha")
    evidence.write_text(text, encoding="utf-8")

    errors = validate_release_evidence(evidence, expected_version="0.1.0-alpha")

    assert "Release evidence version does not match installer version" in errors
    assert "Release evidence Git commit must be a 7-40 character hex SHA" in errors


def test_validate_release_evidence_rejects_git_head_mismatch(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path)

    errors = validate_release_evidence(evidence, expected_git_commit="def5678")

    assert "Release evidence Git commit does not match repository HEAD" in errors


def test_validate_release_evidence_rejects_bad_ffmpeg_provenance(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path)
    text = evidence.read_text(encoding="utf-8")
    text = text.replace(
        "- FFmpeg build filename: ffmpeg-master-latest-win64-lgpl.zip",
        "- FFmpeg build filename: ffmpeg-gpl.exe",
    )
    text = text.replace(
        "- FFmpeg source URL: https://github.com/BtbN/FFmpeg-Builds",
        "- FFmpeg source URL: https://example.com/ffmpeg",
    )
    evidence.write_text(text, encoding="utf-8")

    errors = validate_release_evidence(evidence)

    assert "Release evidence FFmpeg build filename must be a Windows x64 LGPL ZIP" in errors
    assert "Release evidence FFmpeg source URL must use the approved BtbN FFmpeg Builds source" in errors


def test_installer_release_version_reads_inno_define(tmp_path: Path) -> None:
    installer = tmp_path / "a2sb-restorer.iss"
    installer.write_text('#define MyAppVersion "0.2.0"\n', encoding="utf-8")

    assert installer_release_version(installer) == "0.2.0"


def test_git_head_commit_reads_loose_ref(tmp_path: Path) -> None:
    commit = "a" * 40
    ref = tmp_path / ".git" / "refs" / "heads" / "main"
    ref.parent.mkdir(parents=True)
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    ref.write_text(commit + "\n", encoding="utf-8")

    assert git_head_commit(tmp_path) == commit


def test_git_head_commit_reads_packed_ref(tmp_path: Path) -> None:
    commit = "b" * 40
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "packed-refs").write_text(f"# pack-refs\n{commit} refs/heads/main\n", encoding="utf-8")

    assert git_head_commit(tmp_path) == commit


def test_validate_release_evidence_rejects_unpassed_required_results(tmp_path: Path) -> None:
    evidence = write_release_evidence(tmp_path)
    text = evidence.read_text(encoding="utf-8")
    text = text.replace("- Restore produced a WAV: yes", "- Restore produced a WAV: no")
    text = text.replace(
        "- Setup/repair required no manual Python, Conda, Git, WSL, Docker, or YAML editing: yes",
        "- Setup/repair required no manual Python, Conda, Git, WSL, Docker, or YAML editing:",
    )
    evidence.write_text(text, encoding="utf-8")

    errors = validate_release_evidence(evidence)

    assert "Release evidence field is incomplete: Setup/repair required no manual Python, Conda, Git, WSL, Docker, or YAML editing" in errors
    assert "Release evidence must mark required result as passed: Restore produced a WAV" in errors


def test_release_validation_blocks_checkpoint_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    (artifacts / "model.ckpt").write_bytes(b"bad")
    (artifacts / "SHA256SUMS.txt").write_text("hash  model.ckpt\n", encoding="utf-8")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert any("Checkpoint file" in error for error in result.errors)


def test_release_validation_blocks_model_weight_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    setup.write_bytes(b"installer")
    for name in ["model.pt", "model.pth", "model.safetensors"]:
        (artifacts / name).write_bytes(b"bad")
    write_sha256sums(list(artifacts.iterdir()), artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert sum("Model weight file" in error for error in result.errors) == 3


def test_release_validation_blocks_placeholder_notices(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    setup.write_bytes(b"installer")
    write_sha256sums([setup], artifacts / "SHA256SUMS.txt")
    write_notices(licenses, placeholder=True)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert any("placeholder" in error for error in result.errors)


def test_release_validation_requires_readme_and_license_notices_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    setup.write_bytes(b"installer")
    write_sha256sums([setup], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "Missing release artifact: README-WINDOWS.md" in result.errors
    assert "Missing release artifact: LICENSE-NOTICES.txt" in result.errors


def test_release_validation_blocks_tiny_setup_artifact(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    setup.write_bytes(b"MZtiny")
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_release_sources(tmp_path)
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "A2SB-Restorer-Setup.exe is too small to be a real installer artifact" in result.errors


def test_release_validation_blocks_non_windows_setup_artifact(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    setup.write_bytes(b"NO" + b"\0" * (MIN_SETUP_EXE_BYTES - 2))
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_release_sources(tmp_path)
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "A2SB-Restorer-Setup.exe is not a Windows executable" in result.errors


def test_release_validation_requires_checksum_entries_for_all_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    setup.write_bytes(b"installer")
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_release_sources(tmp_path)
    write_sha256sums([setup, readme], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "SHA256SUMS.txt is missing artifact entry: LICENSE-NOTICES.txt" in result.errors


def test_release_validation_blocks_placeholder_release_notice_artifact(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    setup.write_bytes(b"installer")
    readme.write_text("readme", encoding="utf-8")
    notices.write_text(
        "A2SB Restorer License Notices\n\n"
        "This file is a release-source placeholder.\n\n"
        "Do not publish release artifacts\n",
        encoding="utf-8",
    )
    write_release_sources(tmp_path, notices_text=notices.read_text(encoding="utf-8"))
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "Release artifact still contains blocking placeholder text: LICENSE-NOTICES.txt" in result.errors


def test_release_validation_blocks_placeholder_windows_readme_artifact(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    setup.write_bytes(b"installer")
    readme.write_text("Do not publish release artifacts\n", encoding="utf-8")
    notices.write_text("final notices", encoding="utf-8")
    write_release_sources(tmp_path, readme_text=readme.read_text(encoding="utf-8"), notices_text="final notices")
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "Release artifact still contains blocking placeholder text: README-WINDOWS.md" in result.errors


def test_release_validation_rejects_stale_checksum_entries(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    setup.write_bytes(b"installer")
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_release_sources(tmp_path)
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    with (artifacts / "SHA256SUMS.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"{'0' * 64}  deleted.zip\n")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "SHA256SUMS.txt references missing artifact: deleted.zip" in result.errors


def test_release_validation_rejects_checksum_mismatch(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    write_setup_exe(setup)
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_release_sources(tmp_path)
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    readme.write_text("tampered readme", encoding="utf-8")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "SHA256SUMS.txt hash does not match artifact: README-WINDOWS.md" in result.errors


def test_release_validation_rejects_invalid_checksum_file_format(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    write_setup_exe(setup)
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_release_sources(tmp_path)
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    with (artifacts / "SHA256SUMS.txt").open("a", encoding="utf-8") as handle:
        handle.write("not-a-valid-checksum-line\n")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "SHA256SUMS.txt line 4 is malformed" in result.errors


def test_release_validation_rejects_unexpected_extra_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    debug_log = artifacts / "debug.log"
    write_setup_exe(setup)
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_release_sources(tmp_path)
    debug_log.write_text("internal diagnostics", encoding="utf-8")
    write_sha256sums([setup, readme, notices, debug_log], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "Unexpected release artifact: debug.log" in result.errors


def test_release_validation_rejects_staged_docs_that_differ_from_sources(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "LICENSES"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    write_setup_exe(setup)
    (tmp_path / "README-WINDOWS.md").write_text("source readme", encoding="utf-8")
    (tmp_path / "LICENSE-NOTICES.txt").write_text("source notices", encoding="utf-8")
    readme.write_text("changed readme", encoding="utf-8")
    notices.write_text("source notices", encoding="utf-8")
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "Release artifact differs from source file: README-WINDOWS.md" in result.errors


def test_release_validation_requires_source_docs_for_staged_docs(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "LICENSES"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    write_setup_exe(setup)
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "Release source file is missing: README-WINDOWS.md" in result.errors
    assert "Release source file is missing: LICENSE-NOTICES.txt" in result.errors


def test_release_validation_accepts_basic_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    write_setup_exe(setup)
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_release_sources(tmp_path)
    write_release_evidence(tmp_path, installer_sha256=sha256_file(setup))
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert result.ok
    assert result.errors == []
