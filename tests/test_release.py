from pathlib import Path

from rolling_a2sb.release import checksum_artifact_names, collect_release_artifacts, validate_release_artifacts, write_sha256sums


def write_notices(licenses_dir: Path, placeholder: bool = False) -> None:
    licenses_dir.mkdir(parents=True, exist_ok=True)
    text = "Placeholder\nDo not publish release artifacts\n" if placeholder else "Final notice text\n"
    for name in [
        "NVIDIA_A2SB_LICENSE.txt",
        "FFMPEG_NOTICE.txt",
        "PYTHON_NOTICE.txt",
    ]:
        (licenses_dir / name).write_text(text, encoding="utf-8")


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
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    with (artifacts / "SHA256SUMS.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"{'0' * 64}  deleted.zip\n")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert not result.ok
    assert "SHA256SUMS.txt references missing artifact: deleted.zip" in result.errors


def test_release_validation_accepts_basic_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    notices = artifacts / "LICENSE-NOTICES.txt"
    setup.write_bytes(b"installer")
    readme.write_text("readme", encoding="utf-8")
    notices.write_text("notices", encoding="utf-8")
    write_sha256sums([setup, readme, notices], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert result.ok
    assert result.errors == []
