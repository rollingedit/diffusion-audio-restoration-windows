from pathlib import Path

from rolling_a2sb.release import collect_release_artifacts, validate_release_artifacts, write_sha256sums


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


def test_release_validation_accepts_basic_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    licenses = tmp_path / "licenses"
    artifacts.mkdir()
    setup = artifacts / "A2SB-Restorer-Setup.exe"
    readme = artifacts / "README-WINDOWS.md"
    setup.write_bytes(b"installer")
    readme.write_text("readme", encoding="utf-8")
    write_sha256sums([setup, readme], artifacts / "SHA256SUMS.txt")
    write_notices(licenses)

    result = validate_release_artifacts(artifacts, licenses)

    assert result.ok
    assert result.errors == []

