# A2SB Restorer for Windows

Local Windows app for restoring audio with NVIDIA Audio-to-Audio Schrodinger Bridge checkpoints. Install it, pass the Doctor check, download the official model files, drop in audio, and get a restored WAV without Git, Conda, manual Python, YAML editing, WSL, Docker, or terminal commands.

The release artifact set is `A2SB-Restorer-Setup.exe`, `SHA256SUMS.txt`, this Windows README, and `LICENSE-NOTICES.txt`. Checkpoints are downloaded or selected by the user and must not be bundled into the GitHub release.

## Current User Flow

1. Install `A2SB-Restorer-Setup.exe`.
2. Launch `A2SB Restorer` from the Start Menu.
3. Run Doctor from the Setup tab.
4. Download the recommended two-split checkpoints or select a trusted checkpoint folder.
5. Open the Restore tab.
6. Drop or select a WAV, MP3, or FLAC file.
7. Select an output path if the default is not desired.
8. Plan the restore and review the generated job/config/log details.
9. Click Restore to run the shared restore workflow in the background.
10. Watch streamed logs/progress, cancel if needed, and open the output folder after completion.

The GUI restore tab uses the shared product restore path for planning and execution, streams subprocess logs, shows exact step progress when upstream output provides counts, supports cancellation, and enables Open Output Folder after success.

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
