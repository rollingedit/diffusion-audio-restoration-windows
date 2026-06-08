import re
from pathlib import Path

import rolling_a2sb


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_scripts_exist() -> None:
    for rel_path in [
        "scripts/setup_runtime.ps1",
        "scripts/repair_runtime.ps1",
        "scripts/doctor.ps1",
        "scripts/smoke_restore.ps1",
        "scripts/build_launcher.ps1",
        "scripts/build_installer.ps1",
        "scripts/generate_icon.ps1",
        "scripts/release_status.ps1",
        "scripts/write_sha256sums.ps1",
    ]:
        assert (ROOT / rel_path).exists(), rel_path


def test_cuda_runtime_lockfile_is_pinned() -> None:
    text = (ROOT / "requirements" / "lock-win-cu121.txt").read_text(encoding="utf-8")

    for requirement in ["torch==2.2.2+cu121", "torchaudio==2.2.2+cu121", "numpy==1.26.4"]:
        assert requirement in text
    assert "https://download.pytorch.org/whl/cu121" in text


def test_generated_installer_icon_exists() -> None:
    icon = ROOT / "installer" / "assets" / "app.ico"

    assert icon.exists()
    assert icon.read_bytes().startswith(b"\x00\x00\x01\x00")


def test_github_workflows_are_safe_and_non_publishing() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release_validate = (ROOT / ".github" / "workflows" / "release-validate.yml").read_text(encoding="utf-8")

    assert "python -m pytest" in ci
    assert "pull_request:" in ci
    assert "push:" in ci
    assert "workflow_dispatch:" in release_validate
    assert "-ValidateOnly" in release_validate
    assert "write_sha256sums.ps1" in release_validate

    release_lower = release_validate.lower()
    assert "upload-artifact" not in release_lower
    assert "gh release" not in release_lower
    assert "softprops/action-gh-release" not in release_lower
    assert "contents: write" not in release_lower


def test_release_docs_exist() -> None:
    for rel_path in [
        "README-WINDOWS.md",
        "LICENSE-NOTICES.txt",
        "docs/USER_GUIDE.md",
        "docs/TROUBLESHOOTING.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/RELEASE_EVIDENCE.md",
        "docs/LICENSE_NOTICES.md",
        "docs/WHAT_SETUP_INSTALLS.md",
        "docs/UPSTREAM_AUDIT.md",
    ]:
        assert (ROOT / rel_path).exists(), rel_path


def test_package_and_installer_versions_match_release_label() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    installer = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")
    project_version = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)
    installer_version = re.search(r'^#define MyAppVersion "([^"]+)"$', installer, flags=re.MULTILINE)

    assert project_version is not None
    assert installer_version is not None
    assert rolling_a2sb.__version__ == project_version.group(1)
    assert installer_version.group(1) == project_version.group(1).replace("a0", "-alpha")


def test_inno_installer_has_public_support_metadata() -> None:
    installer = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")

    assert '#define MyAppURL "https://github.com/rollingedit/diffusion-audio-restoration-windows"' in installer
    assert "AppPublisherURL={#MyAppURL}" in installer
    assert "AppSupportURL={#MyAppURL}/issues" in installer
    assert "AppUpdatesURL={#MyAppURL}/releases" in installer


def test_license_notices_are_not_placeholders() -> None:
    required_tokens = {
        "LICENSES/NVIDIA_A2SB_LICENSE.txt": ["NVIDIA", "copyright", "not affiliated"],
        "LICENSES/FFMPEG_NOTICE.txt": ["FFmpeg", "BtbN", "LGPL", "https://github.com/BtbN/FFmpeg-Builds"],
        "LICENSES/PYTHON_NOTICE.txt": ["Python", "license", "https://www.python.org"],
    }
    for rel_path, tokens in required_tokens.items():
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "Placeholder" not in text
        assert "Do not publish release artifacts" not in text
        for token in tokens:
            assert token in text


def test_release_checklist_requires_no_checkpoint_release_assets() -> None:
    text = (ROOT / "docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "GitHub release does not include checkpoint files" in text
    assert "No terminal is required for normal use" in text
    assert "docs/RELEASE_EVIDENCE.md" in text


def test_release_evidence_template_requires_real_smoke_proof() -> None:
    text = (ROOT / "docs" / "RELEASE_EVIDENCE.md").read_text(encoding="utf-8")

    for required in [
        "Git commit:",
        "Windows version:",
        "GPU model:",
        "NVIDIA driver version:",
        "CUDA reported by PyTorch:",
        "Installer SHA256:",
        "Doctor JSON path:",
        "Checkpoint manifest path:",
        "Restore log path:",
        "Output WAV path:",
        "Input file hash before restore:",
        "Input file hash after restore:",
        "Release artifacts validated:",
        "Public release is blocked while any item is listed here.",
    ]:
        assert required in text

    assert "Do not replace checklist items with \"assumed\"" in text


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
    assert "RollingEdit A2SB Restorer" in release_notes
    assert "not affiliated with or endorsed by NVIDIA" in release_notes
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
