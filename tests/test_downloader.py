from pathlib import Path

from rolling_a2sb.downloader import build_download_plan, download_model


def test_build_download_plan_for_twosplit(tmp_path: Path) -> None:
    plan = build_download_plan(mode="twosplit", target_dir=tmp_path)

    assert plan.repo_id == "nvidia/audio_to_audio_schrodinger_bridge"
    assert len(plan.filenames) == 2
    assert plan.required_bytes == 5_200_000_000
    assert plan.target_dir == tmp_path


def test_download_model_uses_hf_download_and_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    calls: list[dict] = []
    progress: list[str] = []
    target = tmp_path / "models"

    def fake_download(**kwargs) -> str:
        filename = kwargs["filename"]
        calls.append(kwargs)
        path = target / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 16)
        return str(path)

    result = download_model(
        mode="twosplit",
        target_dir=target,
        progress=progress.append,
        force=True,
        compute_hashes=True,
        min_size_bytes=1,
        hf_download=fake_download,
    )

    assert [call["filename"] for call in calls] == [
        "ckpt/A2SB_twosplit_0.0_0.5_release.ckpt",
        "ckpt/A2SB_twosplit_0.5_1.0_release.ckpt",
    ]
    assert all(call["repo_id"] == "nvidia/audio_to_audio_schrodinger_bridge" for call in calls)
    assert all(call["local_dir"] == str(target) for call in calls)
    assert all(call["resume_download"] is True for call in calls)
    assert all(call["local_dir_use_symlinks"] is False for call in calls)
    assert result.validation.ok
    assert result.manifest_path.exists()
    assert "Downloading checkpoint 1 of 2" in progress[0]
    assert progress[-1] == "Model download complete"
    assert calls
    assert __import__("os").environ["HF_HUB_DISABLE_PROGRESS_BARS"] == "1"
    assert __import__("os").environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] == "1"


def test_download_model_reuses_existing_valid_checkpoints(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    target = tmp_path / "models"
    progress: list[str] = []
    for filename in [
        "ckpt/A2SB_twosplit_0.0_0.5_release.ckpt",
        "ckpt/A2SB_twosplit_0.5_1.0_release.ckpt",
    ]:
        path = target / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 16)

    def fail_download(**kwargs) -> str:
        raise AssertionError("existing valid checkpoints should not be downloaded again")

    result = download_model(
        mode="twosplit",
        target_dir=target,
        progress=progress.append,
        compute_hashes=False,
        min_size_bytes=1,
        hf_download=fail_download,
    )

    assert result.validation.ok
    assert result.manifest_path.exists()
    assert progress == ["Model checkpoints already present"]


def test_download_model_finds_existing_checkpoints_before_download(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    target = tmp_path / "models"
    discovered = data_dir / "models"
    progress: list[str] = []
    byte_progress: list[tuple[int, int, str]] = []
    for filename in [
        "ckpt/A2SB_twosplit_0.0_0.5_release.ckpt",
        "ckpt/A2SB_twosplit_0.5_1.0_release.ckpt",
    ]:
        path = discovered / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 16)

    def fail_download(**kwargs) -> str:
        raise AssertionError("discovered valid checkpoints should not be downloaded again")

    result = download_model(
        mode="twosplit",
        target_dir=target,
        progress=progress.append,
        byte_progress=lambda current, total, label: byte_progress.append((current, total, label)),
        compute_hashes=False,
        min_size_bytes=1,
        hf_download=fail_download,
    )

    assert result.validation.ok
    assert not (target / "ckpt" / "A2SB_twosplit_0.0_0.5_release.ckpt").exists()
    assert not (target / "ckpt" / "A2SB_twosplit_0.5_1.0_release.ckpt").exists()
    assert result.manifest_path.parent == discovered
    assert any("Found existing checkpoint folder" in message for message in progress)
    assert progress[-1] == "Using existing checkpoints; no download needed"
    assert byte_progress == []


def test_download_model_reports_aggregate_stream_progress(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    target = tmp_path / "models"
    byte_progress: list[tuple[int, int, str]] = []

    def fake_stream_download(filename, plan, byte_progress, chunk_size=1024 * 1024) -> str:
        path = target / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        byte_progress(0, 100, Path(filename).name)
        byte_progress(50, 100, Path(filename).name)
        byte_progress(100, 100, Path(filename).name)
        path.write_bytes(b"x" * 16)
        return str(path)

    monkeypatch.setattr("rolling_a2sb.downloader._stream_download_file", fake_stream_download)

    result = download_model(
        mode="twosplit",
        target_dir=target,
        force=True,
        compute_hashes=False,
        min_size_bytes=1,
        byte_progress=lambda current, total, label: byte_progress.append((current, total, label)),
    )

    assert result.validation.ok
    assert byte_progress == [
        (0, 200, "A2SB_twosplit_0.0_0.5_release.ckpt"),
        (50, 200, "A2SB_twosplit_0.0_0.5_release.ckpt"),
        (100, 200, "A2SB_twosplit_0.0_0.5_release.ckpt"),
        (100, 200, "A2SB_twosplit_0.5_1.0_release.ckpt"),
        (150, 200, "A2SB_twosplit_0.5_1.0_release.ckpt"),
        (200, 200, "A2SB_twosplit_0.5_1.0_release.ckpt"),
    ]


def test_download_model_retries_transient_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ROLLING_A2SB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROLLING_A2SB_LOG_DIR", str(tmp_path / "logs"))
    attempts: dict[str, int] = {}
    progress: list[str] = []
    target = tmp_path / "models"

    def flaky_download(**kwargs) -> str:
        filename = kwargs["filename"]
        attempts[filename] = attempts.get(filename, 0) + 1
        if attempts[filename] == 1:
            raise ConnectionError("temporary network failure")
        path = target / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 16)
        return str(path)

    result = download_model(
        mode="twosplit",
        target_dir=target,
        progress=progress.append,
        force=True,
        compute_hashes=False,
        min_size_bytes=1,
        hf_download=flaky_download,
        retries=2,
    )

    assert result.validation.ok
    assert all(count == 2 for count in attempts.values())
    assert any("retrying 2 of 2" in message for message in progress)


def test_download_model_rejects_zero_retries(tmp_path: Path) -> None:
    try:
        download_model(target_dir=tmp_path, force=True, hf_download=lambda **kwargs: "", retries=0)
    except ValueError as exc:
        assert "retries" in str(exc)
    else:
        raise AssertionError("download retries must be positive")
