# A2SB Restorer for Windows

A2SB Restorer is a Windows desktop app for NVIDIA A2SB audio restoration. Install it, run the Doctor check, download the official checkpoints, choose audio, restore, and open the finished WAV.

The app keeps restoration local and wraps the A2SB engine in a Windows application layer: private runtime bootstrap, pinned CUDA/PyTorch stack, Microsoft VC++ runtime setup, FFmpeg/ffprobe, checkpoint management, Windows-safe config generation, GUI restore controls, streamed logs, diagnostics, and release validation.

The Windows app workflow replaces the Linux-style research setup path: runtime creation, native dependencies, CUDA/PyTorch packages, checkpoint discovery, config generation, restore execution, and diagnostics are handled by the installer and GUI.

The release artifact set is `A2SB-Restorer-Setup.exe`, `SHA256SUMS.txt`, this Windows README, and `LICENSE-NOTICES.txt`. Checkpoints are downloaded or selected by the user and must not be bundled into the GitHub release.

## Download This File

For normal use, open the [latest GitHub release](../../releases/latest), then download and run:

```text
A2SB-Restorer-Setup.exe
```

Double-click `A2SB-Restorer-Setup.exe` to install the app. The other release files are supporting files: `SHA256SUMS.txt` verifies downloads, `README-WINDOWS.md` explains the Windows release, and `LICENSE-NOTICES.txt` contains required notices.

Do not download the source ZIPs or clone the repo unless you are working on the code.

## Current User Flow

1. Open the [latest GitHub release](../../releases/latest).
2. Download `A2SB-Restorer-Setup.exe`.
3. Double-click `A2SB-Restorer-Setup.exe`.
4. Launch `A2SB Restorer` from the Start Menu.
5. Run Doctor from the Setup tab.
6. Download the recommended two-split checkpoints or select a trusted checkpoint folder.
7. Open the Restore tab.
8. Drop or select a WAV, MP3, or FLAC file.
9. Select an output path if the default is not desired.
10. Plan the restore and review the generated job/config/log details.
11. Click Restore to run the shared restore workflow in the background.
12. Watch streamed logs/progress, cancel if needed, and open the output folder after completion.

The GUI restore tab uses the shared product restore path for planning and execution, streams subprocess logs, shows exact step progress when upstream output provides counts, supports cancellation, and enables Open Output Folder after success.

## What The Windows Layer Adds

- App-owned Python bootstrap and private runtime instead of global Python mutation.
- Pinned CUDA/PyTorch dependency installation for the current Windows target.
- Microsoft Visual C++ Redistributable bootstrap for PyTorch native DLLs.
- Bundled FFmpeg/ffprobe for local audio probing and preparation.
- Runtime Doctor with readable next steps for dependency, CUDA, driver, FFmpeg, writable-folder, and checkpoint failures.
- Official NVIDIA Hugging Face checkpoint download/validation and trusted manual checkpoint selection.
- Windows-safe generated configs with absolute paths, single-GPU runtime settings, and no research-cluster assumptions.
- GUI restore planning, execution, streamed logs, cancellation, and output-folder actions.
- Inno Setup installer, launcher EXE, Start Menu shortcuts, update behavior, uninstall behavior, release checks, and smoke validation.

## Runtime Bootstrap

The app owns its runtime. Setup downloads the official Python.org Python 3.10.11 x64 installer when needed, verifies its Authenticode signature, installs it into the app-owned `python310\` folder with PATH, launcher, shortcuts, and file associations disabled, and then creates the private `runtime\` virtual environment from that interpreter.

This is intentionally separate from the user's global Python installs.

Setup also installs or repairs Microsoft's official Visual C++ Redistributable x64 because PyTorch native DLLs require it on clean Windows machines.

## Model Files

The app uses the official Hugging Face repository:

```text
nvidia/audio_to_audio_schrodinger_bridge
```

Default two-split files:

```text
ckpt/A2SB_twosplit_0.0_0.5_release.ckpt
ckpt/A2SB_twosplit_0.5_1.0_release.ckpt
```

Checkpoints are downloaded or selected by the user. They must not be bundled into the GitHub release by default.

## Local Files

The installer should use per-user locations. Models, logs, jobs, and settings belong under user app data, not Program Files. Restored audio defaults next to the input under:

```text
<input folder>\A2SB Restored\
```

Original audio inputs must never be modified.

## Privacy and Network Use

Audio files stay on the user's PC. The app does not upload user audio, model outputs, logs, or diagnostic reports.

Internet access is used only when the user chooses an action that needs it, such as installing runtime dependencies during setup or downloading official model checkpoints from Hugging Face. Manual checkpoint selection does not require internet access.

The app should not include telemetry by default. Any future telemetry or update-check behavior must be opt-in and documented before public release.

## Validation Summary

This release candidate was validated before publishing:

- Full test suite: `225 passed`.
- `scripts\release_status.ps1`: zero blockers.
- `rolling_a2sb.cli release-check --artifacts-dir dist\installer --licenses-dir LICENSES`: passed.
- Windows Sandbox clean bootstrap smoke: installer exit `0`, required app files present, private `python310\` bootstrap present, private `runtime\Scripts\python.exe` present, CUDA/PyTorch dependency installation completed, setup status `ok=true`.
- Manual installed-runtime NVIDIA GPU smoke: Doctor passed, CUDA was visible through PyTorch, official two-split checkpoints validated, and a path-with-spaces WAV restored to a 44.1 kHz mono WAV.

The Sandbox smoke proves clean installer/bootstrap behavior, including the NVIDIA-oriented PyTorch CUDA software stack. It is not the CUDA compute proof: Windows Sandbox virtual GPU support is graphics virtualization, and the Sandbox run did not expose the host NVIDIA CUDA device to PyTorch. The manual installed-runtime NVIDIA GPU smoke proves CUDA restore behavior.

## NVIDIA Credit and Disclaimers

This is a RollingEdit Windows productization fork around NVIDIA's A2SB research project:

```text
https://github.com/NVIDIA/diffusion-audio-restoration
```

Official checkpoints are from:

```text
https://huggingface.co/nvidia/audio_to_audio_schrodinger_bridge
```

A2SB Restorer is not affiliated with, sponsored by, or endorsed by NVIDIA. NVIDIA A2SB source code and checkpoints remain subject to NVIDIA's licenses and terms. This app is experimental and intended for non-commercial/research use consistent with the included notices.

## Release Validation

Before publishing, run:

```powershell
a2sb release-check --artifacts-dir dist\installer --licenses-dir LICENSES
```

The GitHub release should include the installer, checksum file, Windows README, and license notices. It should not include checkpoint files.
