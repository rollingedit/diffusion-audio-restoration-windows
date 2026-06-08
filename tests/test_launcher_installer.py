from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_launcher_uses_runtime_python_and_app_module() -> None:
    text = (ROOT / "launcher" / "launcher.py").read_text(encoding="utf-8")

    assert "runtime" in text
    assert "rolling_a2sb.app" in text
    assert "shell=False" in text


def test_launcher_surfaces_setup_failures_for_windowed_exe() -> None:
    text = (ROOT / "launcher" / "launcher.py").read_text(encoding="utf-8")

    assert "MessageBoxW" in text
    assert "A2SB Restorer setup failed" in text
    assert "Repair Runtime" in text


def test_inno_installer_is_per_user_and_has_shortcuts() -> None:
    text = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")

    assert "PrivilegesRequired=lowest" in text
    assert "A2SB Restorer" in text
    assert "A2SB Doctor" in text
    assert "Repair Runtime" in text
    assert "Open Models Folder" in text
    assert "Open Logs Folder" in text


def test_inno_installer_does_not_include_checkpoint_patterns() -> None:
    text = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")

    assert "*.ckpt" not in text
    assert "models\\*" not in text


def test_inno_uninstall_does_not_delete_user_model_data() -> None:
    text = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")

    assert "UninstallDisplayName={#MyAppName}" in text
    assert r"UninstallDisplayIcon={app}\{#MyAppExeName}" in text
    uninstall_section = text.split("[UninstallDelete]", 1)[1]
    assert "{app}\\runtime" in uninstall_section
    assert "models" not in uninstall_section.lower()
    assert "RollingEdit\\A2SB` Restorer\\models" not in uninstall_section


def test_launcher_spec_uses_one_folder_not_one_file_torch_bundle() -> None:
    text = (ROOT / "launcher" / "launcher.spec").read_text(encoding="utf-8")

    assert "COLLECT(" in text
    assert "exclude_binaries=True" in text
    assert "torch" not in text.lower()


def test_launcher_build_outputs_to_installer_payload_location() -> None:
    text = (ROOT / "scripts" / "build_launcher.ps1").read_text(encoding="utf-8")

    assert '$DistDir = Join-Path $AppRoot "dist"' in text
    assert '$ExpectedExe = Join-Path $DistDir "A2SB Restorer\\A2SB Restorer.exe"' in text
    assert '--distpath $DistDir --workpath $WorkDir' in text
    assert "did not produce expected one-folder app" in text


def test_installer_build_requires_launcher_output_before_packaging() -> None:
    text = (ROOT / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")

    assert 'dist\\A2SB Restorer\\A2SB Restorer.exe' in text
    assert "Run scripts\\build_launcher.ps1 first" in text
    assert text.index("Launcher EXE missing") < text.index("Get-Command ISCC.exe")


def test_installer_build_requires_ffmpeg_binaries_before_packaging() -> None:
    text = (ROOT / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")

    assert 'bin\\ffmpeg.exe' in text
    assert 'bin\\ffprobe.exe' in text
    assert "approved redistributable ffmpeg.exe" in text
    assert "approved redistributable ffprobe.exe" in text
    assert text.index("FFmpeg binary missing") < text.index("Get-Command ISCC.exe")
    assert text.index("ffprobe binary missing") < text.index("Get-Command ISCC.exe")


def test_inno_runs_real_runtime_setup_not_dry_run() -> None:
    text = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8")
    run_section = text.split("[Run]", 1)[1].split("[UninstallDelete]", 1)[0]

    assert "setup_runtime.ps1" in run_section
    assert "-DryRun" not in run_section
