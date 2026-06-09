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
    assert paths.cache_dir().exists()
    assert all(path.exists() for path in created)


def test_data_override_keeps_default_logs_with_data_root(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "Data Root With Spaces"
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(data_dir))
    monkeypatch.delenv("ROLLING_A2SB_LOG_DIR", raising=False)

    assert paths.logs_dir() == data_dir.resolve() / "Logs"


def test_runtime_data_paths_stay_outside_install_dir(tmp_path: Path, monkeypatch) -> None:
    install_dir = tmp_path / "Program Files" / "A2SB Restorer"
    data_dir = tmp_path / "User AppData" / "A2SB Restorer"
    log_dir = tmp_path / "User Logs" / "A2SB Restorer"
    monkeypatch.setenv("ROLLING_A2SB_INSTALL_DIR", str(install_dir))
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(log_dir))

    created = paths.ensure_app_dirs()

    assert paths.app_install_dir() == install_dir.resolve()
    assert paths.models_dir() == data_dir.resolve() / "models"
    assert paths.jobs_dir() == data_dir.resolve() / "jobs"
    assert paths.logs_dir() == log_dir.resolve()
    assert paths.models_dir().is_relative_to(data_dir.resolve())
    assert paths.jobs_dir().is_relative_to(data_dir.resolve())
    assert paths.logs_dir().is_relative_to(log_dir.resolve())
    assert not paths.models_dir().is_relative_to(install_dir.resolve())
    assert not paths.logs_dir().is_relative_to(install_dir.resolve())
    assert all(path.exists() for path in created)


def test_engine_root_defaults_to_repo_root() -> None:
    assert (paths.engine_root() / "ensembled_inference_api.py").exists()
