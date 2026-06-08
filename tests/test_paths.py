from pathlib import Path

from rolling_a2sb import paths


def test_path_overrides_and_directory_creation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "Data Root With Spaces"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "Log Root With Spaces"))

    created = paths.ensure_app_dirs()

    assert paths.app_data_dir() == (tmp_path / "Data Root With Spaces").resolve()
    assert paths.logs_dir() == (tmp_path / "Log Root With Spaces").resolve()
    assert paths.models_dir().exists()
    assert paths.jobs_dir().exists()
    assert paths.temp_dir().exists()
    assert all(path.exists() for path in created)


def test_engine_root_defaults_to_repo_root() -> None:
    assert (paths.engine_root() / "ensembled_inference_api.py").exists()

