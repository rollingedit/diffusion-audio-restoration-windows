from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir, user_log_dir

APP_NAME = "A2SB Restorer"
APP_AUTHOR = "RollingEdit"


def app_install_dir() -> Path:
    override = os.environ.get("ROLLING_A2SB_INSTALL_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def app_data_dir() -> Path:
    override = os.environ.get("ROLLING_A2SB_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(user_data_dir(APP_NAME, APP_AUTHOR))


def logs_dir() -> Path:
    override = os.environ.get("ROLLING_A2SB_LOG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.environ.get("ROLLING_A2SB_DATA_DIR"):
        return app_data_dir() / "Logs"
    return Path(user_log_dir(APP_NAME, APP_AUTHOR))


def models_dir() -> Path:
    return app_data_dir() / "models"


def jobs_dir() -> Path:
    return app_data_dir() / "jobs"


def temp_dir() -> Path:
    return app_data_dir() / "temp"


def cache_dir() -> Path:
    return app_data_dir() / "cache"


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def ffmpeg_path() -> Path:
    return app_install_dir() / "bin" / "ffmpeg.exe"


def ffprobe_path() -> Path:
    return app_install_dir() / "bin" / "ffprobe.exe"


def engine_root() -> Path:
    return app_install_dir()


def upstream_ensemble_config_path() -> Path:
    return app_install_dir() / "configs" / "ensemble_2split_sampling.yaml"


def windows_config_dir() -> Path:
    return app_install_dir() / "configs" / "windows"


def ensure_app_dirs() -> list[Path]:
    dirs = [app_data_dir(), models_dir(), logs_dir(), jobs_dir(), temp_dir(), cache_dir()]
    for path in dirs:
        path.mkdir(parents=True, exist_ok=True)
    return dirs
