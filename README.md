# A2SB Restorer for Windows

A2SB Restorer is a Windows desktop app for NVIDIA A2SB audio restoration. It gives the research model a normal app flow: install, run setup checks, download the official checkpoints, select audio, restore, and open the finished WAV.

The app is built for local restoration on Windows with an NVIDIA CUDA GPU. Audio stays on the machine. The installer owns the runtime. The GUI handles setup, checkpoint selection, restore modes, progress, logs, diagnostics, and output folders.

Under the hood, this fork keeps NVIDIA A2SB as the restoration engine and adds the Windows application layer around it. That layer converts the original Linux-oriented research workflow into a packaged desktop experience with a private Python runtime, pinned CUDA/PyTorch stack, native runtime bootstrap, Windows-safe configs, model management, and a PySide6 GUI.

The normal path is:

```text
Open the latest GitHub release
Download A2SB-Restorer-Setup.exe
Double-click A2SB-Restorer-Setup.exe
Launch A2SB Restorer
Run Doctor
Download the official NVIDIA checkpoints
Drop/select audio
Click Restore
Open the restored WAV
```

The result is a Windows workflow where the app handles the Linux-style research setup path: runtime creation, native dependencies, CUDA/PyTorch packages, checkpoint discovery, config generation, restore execution, and diagnostics.

## Download

For normal use, open the [latest GitHub release](../../releases/latest) and download this file:

```text
A2SB-Restorer-Setup.exe
```

Then double-click `A2SB-Restorer-Setup.exe` and follow the installer. The other release files are supporting files:

- `SHA256SUMS.txt`: checksum file for verifying downloads.
- `README-WINDOWS.md`: Windows release notes and usage details.
- `LICENSE-NOTICES.txt`: required license and attribution notices.

Do not download source ZIPs or clone the repo unless you are developing the project.

## Windows App Layer

The NVIDIA model/code is the core restoration engine. This fork adds the Windows desktop product layer around it:

- Windows-first private runtime bootstrap that does not use or modify global Python.
- Official Python.org Python 3.10 bootstrap into an app-owned `python310\` folder.
- Private `runtime\` virtual environment creation and pinned CUDA/PyTorch dependency installation.
- Microsoft Visual C++ Redistributable bootstrap for PyTorch native DLL loading on clean Windows installs.
- Bundled FFmpeg and ffprobe handling for local audio probing/preparation.
- Runtime Doctor checks for Python, imports, Torch/CUDA, NVIDIA driver visibility, FFmpeg, writable folders, and checkpoints.
- Hugging Face checkpoint manager for the official NVIDIA model files, including validation and reuse of existing valid checkpoints.
- Trust-gated manual checkpoint selection because PyTorch checkpoint loading can execute code.
- Windows-safe config generation with absolute paths, single-GPU runtime settings, no `PATH/TO` placeholders, and no research-cluster assumptions.
- Shared restore workflow that prepares inputs, creates job manifests, writes logs, invokes NVIDIA inference from the correct app root, and preserves original audio.
- PySide6 GUI with Setup, Restore, progress/logs, output-folder actions, model/log folder actions, and user-readable errors.
- Launcher EXE that waits for setup/repair and then starts the GUI through the private runtime.
- Inno Setup installer with per-user install, Start Menu shortcuts, app icon, update behavior, uninstall behavior, and no checkpoint bundling.
- Release validation tooling, installed-app smoke scripts, Sandbox bootstrap smoke, checksum generation, license notices, and release evidence.

## What It Does

A2SB Restorer uses NVIDIA A2SB to restore 44.1 kHz music audio locally on Windows. The app currently exposes two practical restore modes:

- **Bandwidth extension**: restore missing high-frequency content.
- **Inpainting**: repair a selected missing or damaged time segment.

The normal user flow is intentionally direct:

1. Open the [latest GitHub release](../../releases/latest).
2. Download `A2SB-Restorer-Setup.exe`.
3. Double-click `A2SB-Restorer-Setup.exe`.
4. Launch `A2SB Restorer`.
5. Run the Setup tab Doctor check.
6. Download the recommended official two-split checkpoints from Hugging Face, or select an existing trusted checkpoint folder.
7. Open the Restore tab.
8. Drop or select a WAV, MP3, or FLAC input.
9. Choose bandwidth extension or inpainting.
10. Click Restore.
11. Open the output folder when the restored WAV is finished.

Restored files default to an `A2SB Restored` folder next to the input file. Original input audio is not modified.

## Why It Exists

The tedious part is not only model inference. It is everything around it:

- Installing a compatible Python runtime without touching the user's global Python.
- Getting the right CUDA PyTorch stack.
- Keeping FFmpeg available.
- Downloading the right checkpoint files from the official NVIDIA Hugging Face repository.
- Avoiding YAML edits and path placeholders.
- Explaining CUDA, driver, dependency, and checkpoint failures in plain language.
- Producing an obvious output WAV and useful logs.

A2SB Restorer automates that whole path while keeping the release flow app-like:

```text
Installer
-> private app runtime
-> Doctor check
-> checkpoint setup
-> GUI restore job
-> restored WAV and logs
```

## Automatic Setup

The installer and launcher use a private app-owned runtime. They do not install packages into the user's global Python.

If a runtime is missing, setup downloads the official Python.org Python 3.10.11 x64 installer, verifies its Authenticode signature, installs it into the app-owned `python310\` folder with PATH, launcher, shortcuts, and file associations disabled, and then creates the private `runtime\` virtual environment from that interpreter.

Runtime dependencies are installed into:

```text
%LOCALAPPDATA%\Programs\RollingEdit\A2SB Restorer\runtime\
```

The app runtime is pinned for the current A2SB Windows release target:

- Python 3.10 private runtime.
- PyTorch `2.2.2+cu121`.
- Torchaudio `2.2.2+cu121`.
- Lightning `2.3.3`.
- NumPy below 2.
- PySide6 GUI packages.
- Bundled FFmpeg and ffprobe.
- Microsoft Visual C++ Redistributable x64 for PyTorch native DLLs.

The bootstrap runtime is intentionally private and compatibility-oriented. Users do not need to manage it.

## Model Files

The installer does not bundle NVIDIA checkpoints.

The app downloads official checkpoint files only after user confirmation from:

```text
nvidia/audio_to_audio_schrodinger_bridge
```

Recommended two-split checkpoint files:

```text
ckpt/A2SB_twosplit_0.0_0.5_release.ckpt
ckpt/A2SB_twosplit_0.5_1.0_release.ckpt
```

Users can also select an existing local checkpoint folder. Manual PyTorch checkpoint selection requires explicit trust confirmation because PyTorch checkpoint loading can execute code.

## Safety And Privacy

Audio stays on the user's PC. The app does not upload user audio, restored outputs, logs, diagnostic reports, or model files.

Network access is used for setup/download actions the user chooses:

- Installing runtime dependencies.
- Downloading official model checkpoints from Hugging Face.

There is no telemetry by default.

The app is designed so failed runs do not modify the input file. Restore output is written separately, with logs and job details available for diagnostics.

## Requirements

- Windows 10/11 x64.
- NVIDIA CUDA-capable GPU.
- Compatible NVIDIA driver.
- Internet access for first runtime setup and official checkpoint download.

CPU restoration is not presented as a supported real restore path.

## Release Files

The GitHub release should include:

- `A2SB-Restorer-Setup.exe`
- `SHA256SUMS.txt`
- `README-WINDOWS.md`
- `LICENSE-NOTICES.txt`


## Validation For This Release

The current release candidate was validated on Windows before publishing:

- Full unit/integration suite: `225 passed`.
- Release status gate: zero blockers.
- Release artifact gate: `rolling_a2sb.cli release-check --artifacts-dir dist\installer --licenses-dir LICENSES` passed.
- Installer build: `A2SB-Restorer-Setup.exe` built with Inno Setup.
- Windows Sandbox clean bootstrap smoke: installer exited `0`, required app files were present, app-owned `python310\` bootstrap existed, app-owned `runtime\Scripts\python.exe` existed, CUDA/PyTorch dependency installation completed, and setup status was `ok=true`.
- Manual installed-runtime NVIDIA GPU smoke on a Windows CUDA test machine: Doctor passed, CUDA was visible through PyTorch, official two-split checkpoints validated, and a path-with-spaces WAV restore completed to a 44.1 kHz mono output.

The Sandbox smoke proves clean-machine installer/bootstrap behavior, including the NVIDIA-oriented PyTorch CUDA software stack. It is not the CUDA compute proof: Windows Sandbox virtual GPU support is graphics virtualization, and the Sandbox run did not expose the host NVIDIA CUDA device to PyTorch. The CUDA proof is the manual installed-runtime NVIDIA GPU smoke.

## NVIDIA Credit And Status

This project is a RollingEdit Windows productization fork around NVIDIA's A2SB research project:

```text
https://github.com/NVIDIA/diffusion-audio-restoration
```

Original paper:

```text
A2SB: Audio-to-Audio Schrodinger Bridges
https://arxiv.org/abs/2501.11311
```

Official NVIDIA project page:

```text
https://research.nvidia.com/labs/adlr/A2SB/
```

Official checkpoints:

```text
https://huggingface.co/nvidia/audio_to_audio_schrodinger_bridge
```

A2SB Restorer is not affiliated with, sponsored by, or endorsed by NVIDIA. NVIDIA A2SB source code and checkpoints remain subject to NVIDIA's licenses and terms. This Windows app is experimental and intended for non-commercial/research use consistent with the included NVIDIA license notices.

## Citation

If you use A2SB in research, cite the original NVIDIA work:

```bibtex
@article{kong2025a2sb,
  title={A2SB: Audio-to-Audio Schrodinger Bridges},
  author={Kong, Zhifeng and Shih, Kevin J and Nie, Weili and Vahdat, Arash and Lee, Sang-gil and Santos, Joao Felipe and Jukic, Ante and Valle, Rafael and Catanzaro, Bryan},
  journal={arXiv preprint arXiv:2501.11311},
  year={2025}
}
```

## License

See:

- `LICENSE`
- `LICENSE-NOTICES.txt`
- `LICENSES/NVIDIA_A2SB_LICENSE.txt`
- `LICENSES/FFMPEG_NOTICE.txt`
- `LICENSES/PYTHON_NOTICE.txt`
- `docs/LICENSE_NOTICES.md`

The NVIDIA A2SB code and model checkpoints are non-commercial. FFmpeg, Python, and dependency notices are included for the redistributed/runtime components.
