from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import paths


@dataclass(frozen=True)
class AppSettings:
    model_mode: str = "twosplit"
    checkpoint_folder: str | None = None
    checkpoint_manifest: str | None = None
    trusted_manual_checkpoint_folder: bool = False
    recent_inputs: list[str] = field(default_factory=list)


def load_settings(path: Path | None = None) -> AppSettings:
    target = path or paths.settings_path()
    if not target.exists():
        return AppSettings()
    data = json.loads(target.read_text(encoding="utf-8"))
    allowed = {field.name for field in AppSettings.__dataclass_fields__.values()}
    filtered = {key: value for key, value in data.items() if key in allowed}
    return AppSettings(**filtered)


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    target = path or paths.settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
    return target


def update_settings(path: Path | None = None, **changes: Any) -> AppSettings:
    current = load_settings(path)
    data = asdict(current)
    data.update(changes)
    updated = AppSettings(**data)
    save_settings(updated, path)
    return updated


def remember_input(input_path: Path, limit: int = 10, path: Path | None = None) -> AppSettings:
    current = load_settings(path)
    resolved = str(Path(input_path).resolve())
    recent = [item for item in current.recent_inputs if item != resolved]
    recent.insert(0, resolved)
    return update_settings(path, recent_inputs=recent[:limit])


def reset_model_settings(path: Path | None = None) -> AppSettings:
    current = load_settings(path)
    updated = AppSettings(
        model_mode=current.model_mode,
        checkpoint_folder=None,
        checkpoint_manifest=None,
        trusted_manual_checkpoint_folder=False,
        recent_inputs=current.recent_inputs,
    )
    save_settings(updated, path)
    return updated


def effective_checkpoint_folder(settings: AppSettings | None = None, explicit_folder: Path | None = None) -> Path:
    if explicit_folder:
        return Path(explicit_folder).expanduser().resolve()

    current = settings or load_settings()
    if current.checkpoint_folder:
        saved = Path(current.checkpoint_folder).expanduser()
        if saved.exists():
            return saved.resolve()

    return paths.models_dir()
