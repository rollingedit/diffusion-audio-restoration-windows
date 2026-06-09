import json
from pathlib import Path

from rolling_a2sb.job import create_restore_job, default_output_path, partial_output_path, safe_stem


def test_safe_stem_removes_windows_invalid_filename_chars() -> None:
    assert safe_stem(Path('bad<>:"|?*.wav')) == "bad_______"


def test_default_output_path_uses_a2sb_restored_folder(tmp_path: Path) -> None:
    input_audio = tmp_path / "Track One.wav"

    output = default_output_path(input_audio)

    assert output == tmp_path / "A2SB Restored" / "Track One__a2sb_highfreq.wav"


def test_default_output_path_increments_existing_output(tmp_path: Path) -> None:
    input_audio = tmp_path / "song.wav"
    existing = tmp_path / "A2SB Restored" / "song__a2sb_highfreq.wav"
    existing.parent.mkdir()
    existing.write_text("exists", encoding="utf-8")

    output = default_output_path(input_audio)

    assert output == tmp_path / "A2SB Restored" / "song__a2sb_highfreq-2.wav"


def test_default_output_path_uses_inpaint_suffix(tmp_path: Path) -> None:
    input_audio = tmp_path / "song.wav"

    output = default_output_path(input_audio, task_mode="inpaint")

    assert output == tmp_path / "A2SB Restored" / "song__a2sb_inpaint.wav"


def test_create_restore_job_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    input_audio = tmp_path / "input.wav"
    input_audio.write_bytes(b"")

    job = create_restore_job(input_audio, steps=2)
    manifest = Path(job.job_dir) / "job.json"

    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["input_audio"] == str(input_audio.resolve())
    assert data["steps"] == 2
    assert data["model_mode"] == "twosplit"
    assert Path(data["output_audio"]).name == "input__a2sb_highfreq.wav"
    assert Path(data["partial_output_audio"]).name == "input__a2sb_highfreq.wav.partial"


def test_create_restore_job_defaults_output_near_input_and_logs_in_app_data(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "App Data"
    log_dir = tmp_path / "Logs"
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(log_dir))
    input_dir = tmp_path / "Session With Spaces"
    input_audio = input_dir / "take.wav"
    input_dir.mkdir()
    input_audio.write_bytes(b"")

    job = create_restore_job(input_audio, steps=2)

    assert Path(job.output_audio).parent == (input_dir / "A2SB Restored").resolve()
    assert Path(job.output_audio).name == "take__a2sb_highfreq.wav"
    assert Path(job.job_dir).is_relative_to((data_dir / "jobs").resolve())
    assert Path(job.log_path).parent == Path(job.job_dir)
    assert not Path(job.output_audio).is_relative_to(data_dir.resolve())


def test_create_restore_job_supports_unicode_paths_where_practical(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    input_dir = tmp_path / "audio cafe \u97f3"
    input_audio = input_dir / "take \u00e9lan.wav"
    input_dir.mkdir()
    input_audio.write_bytes(b"")

    job = create_restore_job(input_audio, steps=2)
    manifest = Path(job.job_dir) / "job.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert data["input_audio"] == str(input_audio.resolve())
    assert Path(data["output_audio"]).name == "take \u00e9lan__a2sb_highfreq.wav"


def test_partial_output_path_can_live_in_job_dir(tmp_path: Path) -> None:
    output = tmp_path / "A2SB Restored" / "song__a2sb_highfreq.wav"
    job_dir = tmp_path / "jobs" / "123"

    partial = partial_output_path(output, job_dir)

    assert partial == job_dir / "song__a2sb_highfreq.wav.partial"
