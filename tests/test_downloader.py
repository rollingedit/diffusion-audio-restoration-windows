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
    calls: list[str] = []
    progress: list[str] = []
    target = tmp_path / "models"

    def fake_download(**kwargs) -> str:
        filename = kwargs["filename"]
        calls.append(filename)
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

    assert calls == [
        "ckpt/A2SB_twosplit_0.0_0.5_release.ckpt",
        "ckpt/A2SB_twosplit_0.5_1.0_release.ckpt",
    ]
    assert result.validation.ok
    assert result.manifest_path.exists()
    assert "Downloading checkpoint 1 of 2" in progress[0]
    assert progress[-1] == "Model download complete"


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
