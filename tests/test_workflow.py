from pathlib import Path
import wave

from rolling_a2sb.subprocess_runner import CommandResult
from rolling_a2sb.workflow import RestorePreparation, execute_restore, prepare_restore, require_runtime_ready


def write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 8000)


def write_checkpoint(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * 16)


def test_prepare_restore_shared_workflow_writes_config_and_log(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr("rolling_a2sb.workflow.validate_checkpoint_folder", lambda folder, mode: __import__(
        "rolling_a2sb.checkpoint_manager", fromlist=["validate_checkpoint_folder"]
    ).validate_checkpoint_folder(folder, mode=mode, min_size_bytes=1))

    audio = tmp_path / "input.wav"
    checkpoints = tmp_path / "models"
    write_wav(audio)
    write_checkpoint(checkpoints / "A2SB_twosplit_0.0_0.5_release.ckpt")
    write_checkpoint(checkpoints / "A2SB_twosplit_0.5_1.0_release.ckpt")

    plan = prepare_restore(
        input_audio=audio,
        checkpoint_folder=checkpoints,
        trust_manual_checkpoints=True,
        steps=2,
        dry_run=True,
    )

    assert Path(plan.config_path).exists()
    assert Path(plan.log_path).exists()
    assert plan.prepared_input_audio
    assert plan.audio_converted
    assert "dry-run" in Path(plan.log_path).read_text(encoding="utf-8")


def test_prepare_restore_handles_paths_with_spaces_and_preserves_original(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "App Data With Spaces"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "Log Root With Spaces"))
    monkeypatch.setattr("rolling_a2sb.workflow.validate_checkpoint_folder", lambda folder, mode: __import__(
        "rolling_a2sb.checkpoint_manager", fromlist=["validate_checkpoint_folder"]
    ).validate_checkpoint_folder(folder, mode=mode, min_size_bytes=1))

    audio_dir = tmp_path / "Input Folder With Spaces"
    audio = audio_dir / "short take.wav"
    checkpoints = tmp_path / "Model Folder With Spaces"
    audio_dir.mkdir()
    write_wav(audio)
    before = audio.read_bytes()
    write_checkpoint(checkpoints / "A2SB_twosplit_0.0_0.5_release.ckpt")
    write_checkpoint(checkpoints / "A2SB_twosplit_0.5_1.0_release.ckpt")

    plan = prepare_restore(
        input_audio=audio,
        checkpoint_folder=checkpoints,
        trust_manual_checkpoints=True,
        steps=2,
        dry_run=True,
    )

    assert audio.read_bytes() == before
    assert "Input Folder With Spaces" in plan.input_audio
    assert "A2SB Restored" in plan.output_audio
    assert "App Data With Spaces" in plan.job_dir
    assert Path(plan.partial_output_audio).parent == Path(plan.job_dir)
    assert Path(plan.config_path).exists()


def test_prepare_restore_requires_trust_for_manual_checkpoints(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))

    try:
        prepare_restore(
            input_audio=tmp_path / "input.wav",
            checkpoint_folder=tmp_path / "models",
            trust_manual_checkpoints=False,
            dry_run=True,
        )
    except PermissionError as exc:
        assert "execute code" in str(exc)
    else:
        raise AssertionError("manual checkpoint restore should require trust")


def test_require_runtime_ready_blocks_failed_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        "rolling_a2sb.workflow.doctor",
        lambda mode: {
            "ok": False,
            "python": {"ok": True},
            "imports": {"ok": True},
            "torch": {"ok": False, "error": "CUDA unavailable", "next_action": "Update driver."},
            "ffmpeg": {"ok": True},
            "ffprobe": {"ok": True},
            "write_permissions": {"ok": True},
            "checkpoints": {"ok": True},
        },
    )

    try:
        require_runtime_ready()
    except RuntimeError as exc:
        message = str(exc)
        assert "Restore cannot start" in message
        assert "torch" in message
        assert "next: Update driver." in message
    else:
        raise AssertionError("restore should be blocked when runtime checks fail")


def test_require_runtime_ready_reports_no_gpu_path(monkeypatch) -> None:
    monkeypatch.setattr(
        "rolling_a2sb.workflow.doctor",
        lambda mode: {
            "ok": False,
            "python": {"ok": True},
            "imports": {"ok": True},
            "torch": {
                "ok": False,
                "cuda_available": False,
                "error": "CUDA unavailable",
                "next_action": "Run Repair Runtime. If Torch installs but CUDA is unavailable, update the NVIDIA driver.",
            },
            "ffmpeg": {"ok": True},
            "ffprobe": {"ok": True},
            "write_permissions": {"ok": True},
            "checkpoints": {"ok": True},
        },
    )

    try:
        require_runtime_ready()
    except RuntimeError as exc:
        message = str(exc)
        assert "Restore cannot start" in message
        assert "torch" in message
        assert "CUDA unavailable" in message
        assert "update the NVIDIA driver" in message
    else:
        raise AssertionError("restore should be blocked when CUDA is unavailable")


def test_require_runtime_ready_reports_missing_checkpoint_setup_path(monkeypatch) -> None:
    monkeypatch.setattr(
        "rolling_a2sb.workflow.doctor",
        lambda mode: {
            "ok": False,
            "python": {"ok": True},
            "imports": {"ok": True},
            "torch": {"ok": True, "cuda_available": True},
            "ffmpeg": {"ok": True},
            "ffprobe": {"ok": True},
            "write_permissions": {"ok": True},
            "checkpoints": {
                "ok": False,
                "missing": ["A2SB_twosplit_0.0_0.5_release.ckpt"],
                "next_action": "Download Official Model or select a trusted checkpoint folder.",
            },
        },
    )

    try:
        require_runtime_ready()
    except RuntimeError as exc:
        message = str(exc)
        assert "Restore cannot start" in message
        assert "checkpoints" in message
        assert "A2SB_twosplit_0.0_0.5_release.ckpt" in message
        assert "Download Official Model" in message
        assert "Traceback" not in message
    else:
        raise AssertionError("restore should be blocked when checkpoints are missing")


def test_execute_restore_runs_shared_plan_and_writes_result_log(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "restore.log"
    plan = RestorePreparation(
        job_id="job",
        job_dir=str(tmp_path / "job"),
        log_path=str(log_path),
        input_audio=str(tmp_path / "input.wav"),
        prepared_input_audio=str(tmp_path / "input.wav"),
        audio_converted=False,
        output_audio=str(tmp_path / "out.wav"),
        partial_output_audio=str(tmp_path / "out.wav.partial"),
        config_path=str(tmp_path / "restore.yaml"),
        command=["python", "engine.py"],
    )
    monkeypatch.setattr("rolling_a2sb.workflow.prepare_restore", lambda **kwargs: plan)

    def fake_runner(config_path, on_line, should_cancel):
        on_line("stdout", "loading model")
        on_line("stderr", "step 1")
        return CommandResult(returncode=0, stdout="done\n", stderr="", cancelled=False)

    execution = execute_restore(tmp_path / "input.wav", runner=fake_runner)

    assert execution.returncode == 0
    text = log_path.read_text(encoding="utf-8")
    assert "stdout: loading model" in text
    assert "stderr: step 1" in text
    assert "returncode=0" in text
