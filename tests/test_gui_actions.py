from pathlib import Path
import wave

from rolling_a2sb.gui_actions import (
    about_text,
    audio_probe_text,
    doctor_report_text,
    download_plan_text,
    download_recommended_model_text,
    execute_restore_text,
    latest_restore_log_text,
    model_download_confirmation_text,
    is_checkpoint_setup_error,
    parse_restore_step_progress,
    prepare_restore_dry_run,
    repair_runtime_text,
    restore_plan_text,
    select_checkpoint_folder_text,
)
from rolling_a2sb.subprocess_runner import CommandResult


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
    text = doctor_report_text()

    assert "A2SB Restorer diagnostic report" in text
    assert "readiness:" in text
    assert "overall:" in text


def test_about_text_contains_attribution_and_non_affiliation() -> None:
    text = about_text()

    assert "NVIDIA Audio-to-Audio Schrodinger Bridge" in text
    assert "not affiliated with or endorsed by NVIDIA" in text
    assert "Audio stays local" in text
    assert "License notices" in text


def test_download_plan_text_contains_official_repo(tmp_path: Path) -> None:
    text = download_plan_text(target_dir=tmp_path / "models")

    assert "nvidia/audio_to_audio_schrodinger_bridge" in text
    assert "A2SB_twosplit_0.0_0.5_release.ckpt" in text


def test_model_download_confirmation_text_explains_source_size_and_location(tmp_path: Path) -> None:
    text = model_download_confirmation_text(target_dir=tmp_path / "models")

    assert '"confirmation_required": true' in text
    assert "nvidia/audio_to_audio_schrodinger_bridge" in text
    assert "A2SB_twosplit_0.0_0.5_release.ckpt" in text
    assert "A2SB_twosplit_0.5_1.0_release.ckpt" in text
    assert '"required_bytes":' in text
    assert '"local_storage_location":' in text
    assert '"internet_required": true' in text


def test_model_download_confirmation_text_supports_onesplit_advanced_mode(tmp_path: Path) -> None:
    text = model_download_confirmation_text(mode="onesplit", target_dir=tmp_path / "models")

    assert '"model": "onesplit"' in text
    assert "A2SB_onesplit_0.0_1.0_release.ckpt" in text
    assert "A2SB_twosplit" not in text


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


def test_repair_runtime_text_runs_repair_script_without_shell(monkeypatch) -> None:
    seen = {}

    def fake_run_command_streaming(args, cwd, on_line=None):
        seen["args"] = list(args)
        seen["cwd"] = cwd
        if on_line:
            on_line("stdout", "repairing")
        return CommandResult(returncode=0, stdout='{"ok":true}\n', stderr="")

    monkeypatch.setattr("rolling_a2sb.gui_actions.run_command_streaming", fake_run_command_streaming)
    lines = []

    text = repair_runtime_text(on_line=lambda stream, line: lines.append((stream, line)))

    assert seen["args"][:4] == ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File"]
    assert str(seen["args"][4]).endswith("scripts\\repair_runtime.ps1")
    assert "-Json" in seen["args"]
    assert lines == [("stdout", "repairing")]
    assert '"ok": true' in text
    assert '"returncode": 0' in text


def test_parse_restore_step_progress_recognizes_common_step_lines() -> None:
    assert parse_restore_step_progress("step 3/50") == (3, 50)
    assert parse_restore_step_progress("sampling step 4 of 20") == (4, 20)
    assert parse_restore_step_progress("  7/10 [00:01<00:02]") == (7, 10)


def test_parse_restore_step_progress_ignores_invalid_lines() -> None:
    assert parse_restore_step_progress("loading model") is None
    assert parse_restore_step_progress("step 12/10") is None
    assert parse_restore_step_progress("step 1/0") is None


def test_checkpoint_setup_error_detection() -> None:
    assert is_checkpoint_setup_error("Model checkpoints are missing\nmissing a.ckpt")
    assert is_checkpoint_setup_error("Checkpoint validation failed: missing b.ckpt")
    assert not is_checkpoint_setup_error("NVIDIA CUDA is not available")


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


def test_execute_restore_text_forwards_stream_lines(tmp_path: Path, monkeypatch) -> None:
    from rolling_a2sb.workflow import RestoreExecution, RestorePreparation

    plan = RestorePreparation(
        job_id="job",
        job_dir=str(tmp_path / "job"),
        log_path=str(tmp_path / "restore.log"),
        input_audio=str(tmp_path / "in.wav"),
        prepared_input_audio=str(tmp_path / "in.wav"),
        audio_converted=False,
        output_audio=str(tmp_path / "out.wav"),
        partial_output_audio=str(tmp_path / "out.partial"),
        config_path=str(tmp_path / "restore.yaml"),
        command=["python", "engine.py"],
    )
    seen: list[tuple[str, str]] = []

    def fake_execute_restore(**kwargs):
        kwargs["on_line"]("stdout", "loading model")
        return RestoreExecution(plan=plan, returncode=0, stdout="loading model\n", stderr="", cancelled=False)

    monkeypatch.setattr("rolling_a2sb.gui_actions.execute_restore", fake_execute_restore)

    execute_restore_text(tmp_path / "in.wav", on_line=lambda stream, line: seen.append((stream, line)))

    assert seen == [("stdout", "loading model")]


def test_execute_restore_text_forwards_cancel_callback(tmp_path: Path, monkeypatch) -> None:
    from rolling_a2sb.workflow import RestoreExecution, RestorePreparation

    plan = RestorePreparation(
        job_id="job",
        job_dir=str(tmp_path / "job"),
        log_path=str(tmp_path / "restore.log"),
        input_audio=str(tmp_path / "in.wav"),
        prepared_input_audio=str(tmp_path / "in.wav"),
        audio_converted=False,
        output_audio=str(tmp_path / "out.wav"),
        partial_output_audio=str(tmp_path / "out.partial"),
        config_path=str(tmp_path / "restore.yaml"),
        command=["python", "engine.py"],
    )
    seen = {"cancel": False}

    def fake_execute_restore(**kwargs):
        seen["cancel"] = kwargs["should_cancel"]()
        return RestoreExecution(plan=plan, returncode=1, stdout="", stderr="", cancelled=True)

    monkeypatch.setattr("rolling_a2sb.gui_actions.execute_restore", fake_execute_restore)

    text = execute_restore_text(tmp_path / "in.wav", should_cancel=lambda: True)

    assert seen["cancel"] is True
    assert '"cancelled": true' in text


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


def test_select_checkpoint_folder_text_accepts_onesplit_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr("rolling_a2sb.gui_actions.select_manual_checkpoint_folder", lambda folder, mode, trusted: __import__(
        "rolling_a2sb.checkpoint_manager", fromlist=["select_manual_checkpoint_folder"]
    ).select_manual_checkpoint_folder(folder, mode=mode, trusted=trusted, min_size_bytes=1, compute_hashes=False))
    folder = tmp_path / "models"
    write_checkpoint(folder / "A2SB_onesplit_0.0_1.0_release.ckpt")

    text = select_checkpoint_folder_text(folder, mode="onesplit", trusted=True)

    assert '"ok": true' in text
    assert '"mode": "onesplit"' in text
    assert "A2SB_onesplit_0.0_1.0_release.ckpt" in text
