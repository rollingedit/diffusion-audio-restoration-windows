from pathlib import Path

from rolling_a2sb.release import (
    ALLOWED_RELEASE_ARTIFACTS,
    MIN_SETUP_EXE_BYTES,
    checksum_artifact_hashes,
    checksum_artifact_names,
    collect_release_artifacts,
    parse_checksum_file,
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


def write_release_evidence(root: Path, blockers: str = "- None") -> Path:
    evidence = root / "docs" / "RELEASE_EVIDENCE.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        "\n".join(
            [
                "# Release Evidence",
                "",
                "## Release Candidate",
                "",
                "- Version: 0.1.0-alpha",
                "- Git commit: abc123",
                "- Build machine: builder",
                "- Test machine: tester",
                "- Windows version: Windows 11 23H2",
                "- GPU model: NVIDIA test GPU",
                "- NVIDIA driver version: 555.55",
                "- CUDA reported by PyTorch: 12.1",
                "- Installer filename: A2SB-Restorer-Setup.exe",
                "- Installer SHA256: " + "a" * 64,
                "- FFmpeg build filename: ffmpeg-master-latest-win64-lgpl.zip",
                "- FFmpeg source URL: https://github.com/BtbN/FFmpeg-Builds",
                "",
                "## Evidence Files",
                "",
                "- Doctor JSON path: evidence/doctor.json",
                "- Checkpoint manifest path: evidence/checkpoint_manifest.json",
                "- Restore log path: evidence/restore.log",
                "- Output WAV path: evidence/out.wav",
                "- Input file hash before restore: " + "b" * 64,
                "- Input file hash after restore: " + "b" * 64,
                "- Release artifacts validated: yes",
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
    assert "Release evidence must mark release artifacts validation as passed" in errors


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
    write_release_evidence(tmp_path)
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert result.ok
    assert result.errors == []
