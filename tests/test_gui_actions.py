from pathlib import Path
import wave

from rolling_a2sb.gui_actions import (
    audio_probe_text,
    doctor_report_text,
    download_plan_text,
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


def test_audio_probe_text_reports_wav(tmp_path: Path) -> None:
    audio = tmp_path / "short.wav"
    write_wav(audio)

    text = audio_probe_text(audio)

    assert '"sample_rate": 8000' in text
    assert '"channels": 1' in text


def test_prepare_restore_dry_run_returns_plan_and_log(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr("rolling_a2sb.gui_actions.validate_checkpoint_folder", lambda folder, mode: __import__(
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
