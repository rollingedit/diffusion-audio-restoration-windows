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
        "docs/UPSTREAM_AUDIT.md",
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
    assert "Click Restore to run the shared restore workflow" in text
    assert "supports cancellation" in text
    assert "Open Output Folder after success" in text
    assert "currently plans restore jobs" not in text
    assert "Full GUI execution" not in text


def test_privacy_and_network_statements_are_documented() -> None:
    readme = (ROOT / "README-WINDOWS.md").read_text(encoding="utf-8")
    notices = (ROOT / "docs" / "LICENSE_NOTICES.md").read_text(encoding="utf-8")
    combined = f"{readme}\n{notices}"

    assert "Audio files stay" in combined
    assert "does not upload user audio" in readme
    assert "internet access" in readme.lower()
    assert "telemetry by default" in combined


def test_license_notices_document_attribution_and_non_affiliation() -> None:
    notices = (ROOT / "docs" / "LICENSE_NOTICES.md").read_text(encoding="utf-8")
    release_notes = (ROOT / "LICENSE-NOTICES.txt").read_text(encoding="utf-8")
    installer = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")

    assert "not affiliated with or endorsed by NVIDIA" in notices
    assert "RollingEdit A2SB Restorer is not affiliated with or endorsed by NVIDIA" in release_notes
    assert "preserve NVIDIA copyright" in notices
    assert 'Source: "..\\LICENSE-NOTICES.txt"; DestDir: "{app}"' in installer


def test_windows_readme_is_installed_with_app_payload() -> None:
    installer = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")

    assert 'Source: "..\\README-WINDOWS.md"; DestDir: "{app}"' in installer


def test_ffmpeg_release_source_and_installer_payload_are_documented() -> None:
    notices = (ROOT / "docs" / "LICENSE_NOTICES.md").read_text(encoding="utf-8")
    installer = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")

    assert "BtbN FFmpeg Builds" in notices
    assert "win64-lgpl" in notices
    assert "not nonfree, not GPL" in notices
    assert 'Source: "..\\bin\\ffmpeg.exe"; DestDir: "{app}\\bin"' in installer
    assert 'Source: "..\\bin\\ffprobe.exe"; DestDir: "{app}\\bin"' in installer
    ffmpeg_lines = [line for line in installer.splitlines() if "..\\bin\\ff" in line]
    assert ffmpeg_lines
    assert all("skipifsourcedoesntexist" not in line.lower() for line in ffmpeg_lines)


def test_upstream_audit_documents_bypassed_research_assumptions() -> None:
    text = (ROOT / "docs" / "UPSTREAM_AUDIT.md").read_text(encoding="utf-8")

    assert "ensembled_inference_api.py" in text
    assert "LightningCLI" in text
    assert "shell=True" in text
    assert "PATH/TO" in text
    assert "SLURMEnvironment" in text
    assert "argument-array subprocess execution" in text
