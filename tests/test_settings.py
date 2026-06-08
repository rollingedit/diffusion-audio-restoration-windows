from pathlib import Path

from rolling_a2sb.settings import (
    AppSettings,
    load_settings,
    remember_input,
    reset_model_settings,
    save_settings,
    update_settings,
)


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    save_settings(AppSettings(checkpoint_folder="models", checkpoint_manifest="manifest.json"), path)

    loaded = load_settings(path)

    assert loaded.checkpoint_folder == "models"
    assert loaded.checkpoint_manifest == "manifest.json"


def test_update_and_reset_model_settings(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    update_settings(path, checkpoint_folder="models", checkpoint_manifest="manifest.json", trusted_manual_checkpoint_folder=True)

    reset = reset_model_settings(path)

    assert reset.checkpoint_folder is None
    assert reset.checkpoint_manifest is None
    assert reset.trusted_manual_checkpoint_folder is False


def test_remember_input_keeps_recent_unique_paths(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"

    remember_input(first, path=path)
    settings = remember_input(second, path=path)
    settings = remember_input(first, path=path)

    assert settings.recent_inputs == [str(first.resolve()), str(second.resolve())]

