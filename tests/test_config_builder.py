from pathlib import Path

import yaml

from rolling_a2sb.config_builder import RestoreConfigRequest, build_restore_config, write_restore_config


def test_twosplit_config_sanitizes_upstream_hpc_defaults(tmp_path: Path) -> None:
    input_audio = tmp_path / "Input Audio" / "song.wav"
    output_audio = tmp_path / "Output Audio" / "song__a2sb.wav"
    checkpoints = [
        tmp_path / "models" / "A2SB_twosplit_0.0_0.5_release.ckpt",
        tmp_path / "models" / "A2SB_twosplit_0.5_1.0_release.ckpt",
    ]
    input_audio.parent.mkdir()
    output_audio.parent.mkdir()

    config = build_restore_config(
        RestoreConfigRequest(
            input_audio=input_audio,
            output_audio=output_audio,
            checkpoint_paths=checkpoints,
            job_dir=tmp_path / "job",
            steps=2,
        )
    )

    rendered = yaml.safe_dump(config, sort_keys=False)
    assert "PATH/TO" not in rendered
    assert "SLURMEnvironment" not in rendered
    assert config["trainer"]["strategy"] == "auto"
    assert config["trainer"]["devices"] == 1
    assert config["trainer"]["num_nodes"] == 1
    assert config["trainer"]["plugins"] is None
    assert config["data"]["num_workers"] == 0
    assert config["data"]["batch_size"] == 1
    assert config["data"]["predict_filelist"][0]["filepath"] == str(input_audio.resolve())
    assert config["model"]["output_audio_filename"] == str(output_audio.resolve())
    assert config["model"]["predict_n_steps"] == 2
    assert config["model"]["pretrained_checkpoints"] == [str(path.resolve()) for path in checkpoints]
    assert config["model"]["t_cutoffs"] == [0.5]


def test_onesplit_config_removes_t_cutoffs(tmp_path: Path) -> None:
    checkpoint = tmp_path / "models" / "A2SB_onesplit_0.0_1.0_release.ckpt"

    config = build_restore_config(
        RestoreConfigRequest(
            input_audio=tmp_path / "song.wav",
            output_audio=tmp_path / "song__a2sb.wav",
            checkpoint_paths=[checkpoint],
            job_dir=tmp_path / "job",
            model_mode="onesplit",
        )
    )

    assert config["model"]["pretrained_checkpoints"] == [str(checkpoint.resolve())]
    assert "t_cutoffs" not in config["model"]


def test_write_restore_config_creates_job_config(tmp_path: Path) -> None:
    config_path = write_restore_config(
        RestoreConfigRequest(
            input_audio=tmp_path / "song.wav",
            output_audio=tmp_path / "song__a2sb.wav",
            checkpoint_paths=[
                tmp_path / "a.ckpt",
                tmp_path / "b.ckpt",
            ],
            job_dir=tmp_path / "job",
        )
    )

    assert config_path == tmp_path / "job" / "restore_config.yaml"
    assert config_path.exists()

