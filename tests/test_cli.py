from pathlib import Path
import json
import wave

from rolling_a2sb.cli import main
from rolling_a2sb.release import ReleaseCheckResult


def write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 8000)


def test_probe_cli_json_outputs_audio_info(tmp_path: Path, capsys) -> None:
    audio = tmp_path / "short.wav"
    write_wav(audio)

    exit_code = main(["probe", str(audio), "--json"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"sample_rate": 8000' in output
    assert '"channels": 1' in output


def test_download_model_requires_confirmation(tmp_path: Path, capsys) -> None:
    exit_code = main(["download-model", "--model", "twosplit", "--target-dir", str(tmp_path)])

    assert exit_code == 2
    output = capsys.readouterr().out
    assert '"confirmation_required": true' in output
    assert "nvidia/audio_to_audio_schrodinger_bridge" in output
    assert "A2SB_twosplit_0.0_0.5_release.ckpt" in output
    assert "A2SB_twosplit_0.5_1.0_release.ckpt" in output
    assert "a2sb download-model --model twosplit --yes" in output


def test_download_model_yes_runs_official_download_path(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    target = tmp_path / "models"
    calls: list[dict] = []

    def fake_hf_download(**kwargs) -> str:
        calls.append(kwargs)
        path = target / kwargs["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 16)
        return str(path)

    monkeypatch.setattr("rolling_a2sb.downloader._load_hf_download", lambda: fake_hf_download)
    monkeypatch.setattr("rolling_a2sb.downloader.validate_checkpoint_folder", lambda folder, mode, min_size_bytes, compute_hashes: __import__(
        "rolling_a2sb.checkpoint_manager", fromlist=["validate_checkpoint_folder"]
    ).validate_checkpoint_folder(folder, mode=mode, min_size_bytes=1, compute_hashes=compute_hashes))

    exit_code = main(["download-model", "--model", "twosplit", "--target-dir", str(target), "--yes", "--no-hash", "--force"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Downloading checkpoint 1 of 2" in output
    assert '"ok": true' in output
    assert "checkpoint_manifest.json" in output
    assert [call["filename"] for call in calls] == [
        "ckpt/A2SB_twosplit_0.0_0.5_release.ckpt",
        "ckpt/A2SB_twosplit_0.5_1.0_release.ckpt",
    ]
    assert all(call["resume_download"] is True for call in calls)


def test_select_checkpoints_requires_trust(tmp_path: Path, capsys) -> None:
    exit_code = main(["select-checkpoints", str(tmp_path / "models")])

    assert exit_code == 2
    assert "PyTorch checkpoint files can execute code" in capsys.readouterr().out


def test_select_checkpoints_accepts_trusted_folder(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr("rolling_a2sb.cli.select_manual_checkpoint_folder", lambda folder, mode, trusted, compute_hashes: __import__(
        "rolling_a2sb.checkpoint_manager", fromlist=["select_manual_checkpoint_folder"]
    ).select_manual_checkpoint_folder(folder, mode=mode, trusted=trusted, min_size_bytes=1, compute_hashes=compute_hashes))
    folder = tmp_path / "models"
    write_checkpoint(folder / "A2SB_twosplit_0.0_0.5_release.ckpt")
    write_checkpoint(folder / "A2SB_twosplit_0.5_1.0_release.ckpt")

    exit_code = main(["select-checkpoints", str(folder), "--trust"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"ok": true' in output
    assert "checkpoint_manifest.json" in output


def test_doctor_report_cli_prints_copyable_report(capsys) -> None:
    exit_code = main(["doctor", "--report"])

    assert exit_code in (0, 1)
    output = capsys.readouterr().out
    assert "A2SB Restorer diagnostic report" in output
    assert "app_version:" in output
    assert "readiness:" in output
    assert "overall:" in output
    assert "next:" in output


def write_checkpoint(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * 16)


def test_restore_dry_run_uses_saved_checkpoint_folder_and_writes_log(tmp_path: Path, monkeypatch, capsys) -> None:
    data_dir = tmp_path / "data"
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(log_dir))
    monkeypatch.setattr("rolling_a2sb.cli.check_engine_imports", lambda: {"ok": True, "command": ["python", "-c", "import ensembled_inference_api"]})
    monkeypatch.setattr("rolling_a2sb.workflow.validate_checkpoint_folder", lambda folder, mode: __import__(
        "rolling_a2sb.checkpoint_manager", fromlist=["validate_checkpoint_folder"]
    ).validate_checkpoint_folder(folder, mode=mode, min_size_bytes=1))

    audio = tmp_path / "short.wav"
    write_wav(audio)
    checkpoint_folder = tmp_path / "models"
    write_checkpoint(checkpoint_folder / "A2SB_twosplit_0.0_0.5_release.ckpt")
    write_checkpoint(checkpoint_folder / "A2SB_twosplit_0.5_1.0_release.ckpt")

    exit_code = main(
        [
            "restore",
            "--input",
            str(audio),
            "--checkpoint-folder",
            str(checkpoint_folder),
            "--trust-manual-checkpoints",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"log":' in output
    assert '"prepared_input":' in output
    assert '"partial_output":' in output
    assert '"command":' in output
    assert '"engine_imports":' in output
    assert '"ok": true' in output
    logs = list((data_dir / "jobs").glob("*/restore.log"))
    assert len(logs) == 1
    assert "dry-run" in logs[0].read_text(encoding="utf-8")


def test_restore_manual_checkpoint_requires_trust(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    audio = tmp_path / "short.wav"
    write_wav(audio)

    exit_code = main(["restore", "--input", str(audio), "--checkpoint-folder", str(tmp_path / "models"), "--dry-run"])

    assert exit_code == 2
    assert "PyTorch checkpoint files can execute code" in capsys.readouterr().out


def test_restore_non_dry_run_prints_readiness_failure(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr("rolling_a2sb.cli.prepare_restore", lambda **kwargs: (_ for _ in ()).throw(
        RuntimeError("Restore cannot start because setup is not ready: torch")
    ))
    audio = tmp_path / "short.wav"
    write_wav(audio)

    exit_code = main(["restore", "--input", str(audio)])

    assert exit_code == 1
    assert "Restore cannot start" in capsys.readouterr().out


def test_restore_cli_prints_no_gpu_readiness_failure(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr("rolling_a2sb.cli.execute_restore", lambda **kwargs: (_ for _ in ()).throw(
        RuntimeError(
            "Restore cannot start because setup is not ready: torch\n\n"
            "torch: needs attention\n"
            "  error: CUDA unavailable\n"
            "  next: Run Repair Runtime. If Torch installs but CUDA is unavailable, update the NVIDIA driver.\n"
        )
    ))
    audio = tmp_path / "short.wav"
    write_wav(audio)

    exit_code = main(["restore", "--input", str(audio)])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "CUDA unavailable" in output
    assert "update the NVIDIA driver" in output
    assert "Traceback" not in output


def test_restore_cli_prints_missing_checkpoint_setup_failure(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr("rolling_a2sb.cli.execute_restore", lambda **kwargs: (_ for _ in ()).throw(
        RuntimeError(
            "Restore cannot start because setup is not ready: checkpoints\n\n"
            "checkpoints: needs attention\n"
            "  missing: A2SB_twosplit_0.0_0.5_release.ckpt\n"
            "  next: Download Official Model or select a trusted checkpoint folder.\n"
        )
    ))
    audio = tmp_path / "short.wav"
    write_wav(audio)

    exit_code = main(["restore", "--input", str(audio)])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "A2SB_twosplit_0.0_0.5_release.ckpt" in output
    assert "Download Official Model" in output
    assert "Traceback" not in output


def test_restore_nonzero_process_prints_user_error(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    audio = tmp_path / "short.wav"
    write_wav(audio)

    from rolling_a2sb.workflow import RestoreExecution, RestorePreparation

    plan = RestorePreparation(
        job_id="job",
        job_dir=str(tmp_path / "job"),
        log_path=str(tmp_path / "restore.log"),
        input_audio=str(audio),
        prepared_input_audio=str(audio),
        audio_converted=False,
        output_audio=str(tmp_path / "out.wav"),
        partial_output_audio=str(tmp_path / "out.wav.partial"),
        config_path=str(tmp_path / "restore.yaml"),
        command=["python", "engine.py"],
    )
    execution = RestoreExecution(
        plan=plan,
        returncode=1,
        stdout="",
        stderr="Traceback (most recent call last):\n  File \"engine.py\", line 10\nRuntimeError: CUDA out of memory",
        cancelled=False,
    )
    monkeypatch.setattr("rolling_a2sb.cli.execute_restore", lambda **kwargs: execution)

    exit_code = main(["restore", "--input", str(audio)])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "GPU memory" in output
    assert "File \"engine.py\"" not in output


def test_reset_models_clears_checkpoint_settings(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    from rolling_a2sb.settings import update_settings

    update_settings(checkpoint_folder="models", checkpoint_manifest="manifest.json", trusted_manual_checkpoint_folder=True)

    exit_code = main(["reset-models"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"checkpoint_folder": null' in output


def test_cleanup_models_requires_force_and_lists_app_owned_files(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    models = tmp_path / "data" / "models"
    checkpoint = models / "ckpt" / "A2SB_twosplit_0.0_0.5_release.ckpt"
    write_checkpoint(checkpoint)

    exit_code = main(["cleanup-models"])

    assert exit_code == 2
    output = capsys.readouterr().out
    assert '"confirmation_required": true' in output
    assert "a2sb cleanup-models --force" in output
    data = json.loads(output)
    assert str(checkpoint.resolve()) in data["files"]
    assert checkpoint.exists()


def test_cleanup_models_force_deletes_app_owned_files(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    models = tmp_path / "data" / "models"
    checkpoint = models / "A2SB_onesplit_0.0_1.0_release.ckpt"
    write_checkpoint(checkpoint)

    exit_code = main(["cleanup-models", "--force"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"deleted": true' in output
    assert not checkpoint.exists()


def test_release_check_cli_prints_validation_errors(tmp_path: Path, monkeypatch, capsys) -> None:
    artifacts = tmp_path / "dist" / "installer"
    licenses = tmp_path / "LICENSES"
    calls: list[tuple[Path, Path]] = []

    def fake_validate(artifacts_dir: Path, licenses_dir: Path) -> ReleaseCheckResult:
        calls.append((artifacts_dir, licenses_dir))
        return ReleaseCheckResult(ok=False, errors=["missing installer"])

    monkeypatch.setattr("rolling_a2sb.cli.validate_release_artifacts", fake_validate)

    exit_code = main(["release-check", "--artifacts-dir", str(artifacts), "--licenses-dir", str(licenses)])

    assert exit_code == 1
    assert calls == [(artifacts, licenses)]
    output = json.loads(capsys.readouterr().out)
    assert output == {"ok": False, "errors": ["missing installer"]}


def test_release_check_cli_can_regenerate_sha256_before_validation(tmp_path: Path, monkeypatch, capsys) -> None:
    artifacts = tmp_path / "dist" / "installer"
    licenses = tmp_path / "LICENSES"
    artifact = artifacts / "A2SB-Restorer-Setup.exe"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"installer")
    calls: list[list[Path]] = []

    def fake_write(files: list[Path], output_path: Path) -> Path:
        calls.append(files)
        output_path.write_text("checksum\n", encoding="utf-8")
        return output_path

    monkeypatch.setattr("rolling_a2sb.cli.write_sha256sums", fake_write)
    monkeypatch.setattr("rolling_a2sb.cli.validate_release_artifacts", lambda artifacts_dir, licenses_dir: ReleaseCheckResult(ok=True, errors=[]))

    exit_code = main(["release-check", "--artifacts-dir", str(artifacts), "--licenses-dir", str(licenses), "--write-sha256"])

    assert exit_code == 0
    assert calls == [[artifact]]
    assert json.loads(capsys.readouterr().out) == {"ok": True, "errors": []}


def test_release_status_cli_prints_blockers_without_failing(tmp_path: Path, monkeypatch, capsys) -> None:
    artifacts = tmp_path / "dist" / "installer"
    licenses = tmp_path / "LICENSES"

    monkeypatch.setattr(
        "rolling_a2sb.cli.release_status_summary",
        lambda artifacts_dir, licenses_dir: {
            "ok": False,
            "artifacts_dir": str(artifacts_dir),
            "licenses_dir": str(licenses_dir),
            "artifact_count": 0,
            "artifacts": [],
            "blocker_count": 1,
            "blockers": ["missing installer"],
            "next_command": "a2sb release-check --artifacts-dir dist/installer --licenses-dir LICENSES",
        },
    )

    exit_code = main(["release-status", "--artifacts-dir", str(artifacts), "--licenses-dir", str(licenses)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert output["blocker_count"] == 1
    assert output["blockers"] == ["missing installer"]
