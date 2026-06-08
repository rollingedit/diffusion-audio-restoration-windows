from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import paths


@dataclass(frozen=True)
class RestoreConfigRequest:
    input_audio: Path
    output_audio: Path
    checkpoint_paths: list[Path]
    job_dir: Path
    steps: int = 50
    model_mode: str = "twosplit"
    base_config: Path | None = None


def load_yaml(path: Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def write_yaml(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    return path


def build_restore_config(request: RestoreConfigRequest) -> dict[str, Any]:
    base_path = request.base_config or paths.upstream_ensemble_config_path()
    config = copy.deepcopy(load_yaml(base_path))

    trainer = config.setdefault("trainer", {})
    trainer["accelerator"] = "gpu"
    trainer["strategy"] = "auto"
    trainer["devices"] = 1
    trainer["num_nodes"] = 1
    trainer["precision"] = "32-true"
    trainer["plugins"] = None
    trainer["use_distributed_sampler"] = False
    trainer["enable_progress_bar"] = True

    model = config.setdefault("model", {})
    model["pretrained_checkpoints"] = [str(Path(path).resolve()) for path in request.checkpoint_paths]
    model["predict_n_steps"] = request.steps
    model["output_audio_filename"] = str(Path(request.output_audio).resolve())

    if request.model_mode == "twosplit":
        if len(request.checkpoint_paths) != 2:
            raise ValueError("twosplit mode requires exactly two checkpoint paths")
        model["t_cutoffs"] = [0.5]
    elif request.model_mode == "onesplit":
        if len(request.checkpoint_paths) != 1:
            raise ValueError("onesplit mode requires exactly one checkpoint path")
        model.pop("t_cutoffs", None)
    else:
        raise ValueError(f"Unsupported model mode: {request.model_mode}")

    data = config.setdefault("data", {})
    data["num_workers"] = 0
    data["batch_size"] = 1
    data["predict_filelist"] = [
        {
            "filepath": str(Path(request.input_audio).resolve()),
            "output_subdir": ".",
        }
    ]
    data.pop("mix_dataset_config", None)

    validate_generated_config(config)
    return config


def write_restore_config(request: RestoreConfigRequest) -> Path:
    config = build_restore_config(request)
    return write_yaml(config, request.job_dir / "restore_config.yaml")


def validate_generated_config(config: dict[str, Any]) -> None:
    rendered = yaml.safe_dump(config, sort_keys=False)
    forbidden = ["PATH/TO", "SLURMEnvironment"]
    for token in forbidden:
        if token in rendered:
            raise ValueError(f"generated config still contains forbidden token: {token}")

    trainer = config.get("trainer", {})
    if trainer.get("strategy") != "auto":
        raise ValueError("generated config must use trainer.strategy=auto")
    if trainer.get("devices") != 1:
        raise ValueError("generated config must use trainer.devices=1")
    if trainer.get("num_nodes") != 1:
        raise ValueError("generated config must use trainer.num_nodes=1")

    data = config.get("data", {})
    if data.get("num_workers") != 0:
        raise ValueError("generated config must use data.num_workers=0")
    if data.get("batch_size") != 1:
        raise ValueError("generated config must use data.batch_size=1")

    predict_filelist = data.get("predict_filelist")
    if not predict_filelist:
        raise ValueError("generated config must include data.predict_filelist")

    checkpoints = config.get("model", {}).get("pretrained_checkpoints")
    if not checkpoints:
        raise ValueError("generated config must include model.pretrained_checkpoints")

