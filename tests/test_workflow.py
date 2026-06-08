from pathlib import Path
import wave

from rolling_a2sb.workflow import prepare_restore, require_runtime_ready


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
