# A2SB Restorer for Windows

Local Windows app. One installer. Guided setup. Drag in audio. Get a restored WAV.

A2SB Restorer exists because NVIDIA's Audio-to-Audio Schrodinger Bridge is powerful research code, but normal Windows users should not have to install Git, Python, Conda, CUDA packages, FFmpeg, edit YAML, find checkpoint filenames, or run terminal commands just to try audio restoration.

This project turns that research workflow into a Windows desktop product flow:

```text
Download A2SB-Restorer-Setup.exe
Install
Launch A2SB Restorer
Run Doctor
Download the official NVIDIA checkpoints
Drop/select audio
Click Restore
Open the restored WAV
```

The app keeps the hard parts inside the setup and GUI: private Python runtime bootstrap, pinned CUDA/PyTorch dependencies, FFmpeg/ffprobe, model checkpoint setup, runtime diagnostics, generated configs, restore logs, progress, and output folders.

It is built for people who want the result, not a research-repo setup chore.

## What It Does

A2SB Restorer uses NVIDIA A2SB to restore 44.1 kHz music audio locally on Windows. The app currently exposes two practical restore modes:

- **Bandwidth extension**: restore missing high-frequency content.
- **Inpainting**: repair a selected missing or damaged time segment.

The normal user flow is intentionally direct:

1. Install `A2SB-Restorer-Setup.exe`.
2. Launch `A2SB Restorer`.
3. Run the Setup tab Doctor check.
4. Download the recommended official two-split checkpoints from Hugging Face, or select an existing trusted checkpoint folder.
5. Open the Restore tab.
6. Drop or select a WAV, MP3, or FLAC input.
7. Choose bandwidth extension or inpainting.
8. Click Restore.
9. Open the output folder when the restored WAV is finished.

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
