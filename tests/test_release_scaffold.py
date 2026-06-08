from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_scripts_exist() -> None:
    for rel_path in [
        "scripts/setup_runtime.ps1",
        "scripts/repair_runtime.ps1",
        "scripts/doctor.ps1",
        "scripts/smoke_restore.ps1",
        "scripts/build_launcher.ps1",
        "scripts/build_installer.ps1",
        "scripts/write_sha256sums.ps1",
    ]:
        assert (ROOT / rel_path).exists(), rel_path


def test_release_docs_exist() -> None:
    for rel_path in [
        "README-WINDOWS.md",
        "LICENSE-NOTICES.txt",
        "docs/USER_GUIDE.md",
        "docs/TROUBLESHOOTING.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/LICENSE_NOTICES.md",
        "docs/WHAT_SETUP_INSTALLS.md",
    ]:
        assert (ROOT / rel_path).exists(), rel_path


def test_license_placeholders_are_release_blockers() -> None:
    for rel_path in [
        "LICENSES/NVIDIA_A2SB_LICENSE.txt",
        "LICENSES/FFMPEG_NOTICE.txt",
        "LICENSES/PYTHON_NOTICE.txt",
    ]:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "Placeholder" in text
        assert "Do not publish release artifacts" in text


def test_release_checklist_requires_no_checkpoint_release_assets() -> None:
    text = (ROOT / "docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "GitHub release does not include checkpoint files" in text
    assert "No terminal is required for normal use" in text


def test_windows_readme_documents_release_blockers() -> None:
    text = (ROOT / "README-WINDOWS.md").read_text(encoding="utf-8")

    assert "not public-release-ready yet" in text
    assert "nvidia/audio_to_audio_schrodinger_bridge" in text
    assert "must not be bundled" in text
