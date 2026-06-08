from pathlib import Path
import wave

from rolling_a2sb.gui_actions import (
    audio_probe_text,
    doctor_report_text,
    download_plan_text,
    download_recommended_model_text,
    execute_restore_text,
    latest_restore_log_text,
    model_download_confirmation_text,
    prepare_restore_dry_run,
    restore_plan_text,
    select_checkpoint_folder_text,
)


def write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 8000)


def write_checkpoint(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * 16)


def test_doctor_report_text_contains_header() -> None:
    assert "A2SB Restorer diagnostic report" in doctor_report_text()


def test_download_plan_text_contains_official_repo(tmp_path: Path) -> None:
    text = download_plan_text(target_dir=tmp_path / "models")

    assert "nvidia/audio_to_audio_schrodinger_bridge" in text
    assert "A2SB_twosplit_0.0_0.5_release.ckpt" in text


def test_model_download_confirmation_text_explains_source_size_and_location(tmp_path: Path) -> None:
    text = model_download_confirmation_text(target_dir=tmp_path / "models")

    assert '"confirmation_required": true' in text
    assert "nvidia/audio_to_audio_schrodinger_bridge" in text
    assert '"required_bytes":' in text
    assert '"local_storage_location":' in text
    assert '"internet_required": true' in text


def test_download_recommended_model_text_reports_progress(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))

    class Validation:
        ok = True

    class Result:
        mode = "twosplit"
        validation = Validation()
        manifest_path = tmp_path / "models" / "checkpoint_manifest.json"
        files = [tmp_path / "models" / "a.ckpt"]

    def fake_download_model(mode, target_dir, progress):
        progress("Downloading checkpoint 1 of 2")
        progress("Model download complete")
        return Result()

    monkeypatch.setattr("rolling_a2sb.gui_actions.download_model", fake_download_model)

    text = download_recommended_model_text(target_dir=tmp_path / "models")

    assert '"ok": true' in text
    assert "checkpoint_manifest.json" in text
    assert "Model download complete" in text


def test_audio_probe_text_reports_wav(tmp_path: Path) -> None:
    audio = tmp_path / "short.wav"
    write_wav(audio)

    text = audio_probe_text(audio)

    assert '"sample_rate": 8000' in text
    assert '"channels": 1' in text


def test_latest_restore_log_text_reports_empty_folder(tmp_path: Path) -> None:
    assert latest_restore_log_text(tmp_path / "jobs") == "No restore logs found."


def test_latest_restore_log_text_reads_newest_log(tmp_path: Path) -> None:
    old_log = tmp_path / "jobs" / "old" / "restore.log"
    new_log = tmp_path / "jobs" / "new" / "restore.log"
    old_log.parent.mkdir(parents=True)
    new_log.parent.mkdir(parents=True)
    old_log.write_text("old", encoding="utf-8")
    new_log.write_text("new", encoding="utf-8")

    text = latest_restore_log_text(tmp_path / "jobs")

    assert "Latest restore log:" in text
    assert "new" in text


def test_prepare_restore_dry_run_returns_plan_and_log(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr("rolling_a2sb.workflow.validate_checkpoint_folder", lambda folder, mode: __import__(
        "rolling_a2sb.checkpoint_manager", fromlist=["validate_checkpoint_folder"]
    ).validate_checkpoint_folder(folder, mode=mode, min_size_bytes=1))

    audio = tmp_path / "short.wav"
    checkpoints = tmp_path / "models"
    write_wav(audio)
    write_checkpoint(checkpoints / "A2SB_twosplit_0.0_0.5_release.ckpt")
    write_checkpoint(checkpoints / "A2SB_twosplit_0.5_1.0_release.ckpt")

    plan = prepare_restore_dry_run(
        audio,
        checkpoint_folder=checkpoints,
        trust_manual_checkpoints=True,
        steps=2,
    )

    assert Path(plan.log_path).exists()
    assert plan.prepared_input_audio
    assert plan.partial_output_audio.endswith(".partial")
    assert "ensembled_inference_api.py" in " ".join(plan.command)
    assert '"partial_output_audio":' in restore_plan_text(plan)


def test_execute_restore_text_reports_output_and_log(tmp_path: Path, monkeypatch) -> None:
    from rolling_a2sb.workflow import RestoreExecution, RestorePreparation

    plan = RestorePreparation(
        job_id="job",
        job_dir=str(tmp_path / "job"),
        log_path=str(tmp_path / "restore.log"),
        input_audio=str(tmp_path / "in.wav"),
        prepared_input_audio=str(tmp_path / "in.wav"),
        audio_converted=False,
        output_audio=str(tmp_path / "A2SB Restored" / "out.wav"),
        partial_output_audio=str(tmp_path / "out.partial"),
        config_path=str(tmp_path / "restore.yaml"),
        command=["python", "engine.py"],
    )
    execution = RestoreExecution(plan=plan, returncode=0, stdout="done", stderr="", cancelled=False)
    monkeypatch.setattr("rolling_a2sb.gui_actions.execute_restore", lambda **kwargs: execution)

    text = execute_restore_text(tmp_path / "in.wav")

    assert '"ok": true' in text
    assert '"output":' in text
    assert "A2SB Restored" in text
    assert '"log":' in text


def test_select_checkpoint_folder_text_requires_trust(tmp_path: Path) -> None:
    try:
        select_checkpoint_folder_text(tmp_path / "models", trusted=False)
    except PermissionError as exc:
        assert "execute code" in str(exc)
    else:
        raise AssertionError("manual checkpoint selection should require trust")


def test_select_checkpoint_folder_text_accepts_trusted_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr("rolling_a2sb.gui_actions.select_manual_checkpoint_folder", lambda folder, mode, trusted: __import__(
        "rolling_a2sb.checkpoint_manager", fromlist=["select_manual_checkpoint_folder"]
    ).select_manual_checkpoint_folder(folder, mode=mode, trusted=trusted, min_size_bytes=1, compute_hashes=False))
    folder = tmp_path / "models"
    write_checkpoint(folder / "A2SB_twosplit_0.0_0.5_release.ckpt")
    write_checkpoint(folder / "A2SB_twosplit_0.5_1.0_release.ckpt")

    text = select_checkpoint_folder_text(folder, trusted=True)

    assert '"ok": true' in text
    assert "checkpoint_manifest.json" in text
