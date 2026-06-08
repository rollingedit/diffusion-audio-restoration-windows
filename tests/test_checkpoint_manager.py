from pathlib import Path

import pytest

from rolling_a2sb.checkpoint_manager import (
    checkpoint_paths_from_validation,
    required_files,
    select_manual_checkpoint_folder,
    trusted_manual_checkpoint_warning,
    validate_checkpoint_folder,
)


def write_checkpoint(path: Path, size: int = 16) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_required_files_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        required_files("bad-mode")


def test_missing_twosplit_files_reports_exact_names(tmp_path: Path) -> None:
    result = validate_checkpoint_folder(tmp_path, min_size_bytes=1)

    assert not result.ok
    assert result.missing == [
        "A2SB_twosplit_0.0_0.5_release.ckpt",
        "A2SB_twosplit_0.5_1.0_release.ckpt",
    ]


def test_twosplit_accepts_nested_hf_layout(tmp_path: Path) -> None:
    first = tmp_path / "ckpt" / "A2SB_twosplit_0.0_0.5_release.ckpt"
    second = tmp_path / "ckpt" / "A2SB_twosplit_0.5_1.0_release.ckpt"
    write_checkpoint(first)
    write_checkpoint(second)

    result = validate_checkpoint_folder(tmp_path, min_size_bytes=1)

    assert result.ok
    assert [file.name for file in result.files] == [
        "A2SB_twosplit_0.0_0.5_release.ckpt",
        "A2SB_twosplit_0.5_1.0_release.ckpt",
    ]
    assert checkpoint_paths_from_validation(result) == [first.resolve(), second.resolve()]


def test_too_small_checkpoint_is_rejected(tmp_path: Path) -> None:
    write_checkpoint(tmp_path / "A2SB_twosplit_0.0_0.5_release.ckpt", size=2)
    write_checkpoint(tmp_path / "A2SB_twosplit_0.5_1.0_release.ckpt", size=2)

    result = validate_checkpoint_folder(tmp_path, min_size_bytes=1024)

    assert not result.ok
    assert result.errors
    assert "too small" in result.errors[0]


def test_manual_checkpoint_warning_mentions_trust() -> None:
    warning = trusted_manual_checkpoint_warning()

    assert "execute code" in warning
    assert "trust" in warning


def test_select_manual_checkpoint_folder_requires_trust(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        select_manual_checkpoint_folder(tmp_path, trusted=False, min_size_bytes=1)


def test_select_manual_checkpoint_folder_writes_manifest_and_settings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    folder = tmp_path / "models"
    write_checkpoint(folder / "A2SB_twosplit_0.0_0.5_release.ckpt")
    write_checkpoint(folder / "A2SB_twosplit_0.5_1.0_release.ckpt")

    validation, manifest = select_manual_checkpoint_folder(folder, trusted=True, min_size_bytes=1, compute_hashes=True)

    assert validation.ok
    assert manifest.exists()
    assert "manual-trusted" in manifest.read_text(encoding="utf-8")
    from rolling_a2sb.settings import load_settings

    settings = load_settings()
    assert settings.checkpoint_folder == str(folder.resolve())
    assert settings.trusted_manual_checkpoint_folder is True
