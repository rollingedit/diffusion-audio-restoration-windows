# What Setup Installs

This document is the user-facing dependency disclosure for the Windows installer.

## App Files

The installer should install:

- `A2SB Restorer.exe`
- RollingEdit A2SB Python package.
- NVIDIA A2SB engine files from this repo.
- Windows-safe configs.
- Runtime setup and repair scripts.
- Documentation and license notices.
- FFmpeg and ffprobe binaries from the approved redistributable Windows x64 LGPL build.

Downloaded checkpoints are stored in the user app-data model folder. They are not removed by uninstall unless the user runs an explicit model cleanup action.

## Private Runtime

The app uses a private Python runtime owned by the app. It should not install packages into the user's global Python.

Planned runtime path:

```text
%LOCALAPPDATA%\Programs\RollingEdit\A2SB Restorer\runtime\
```

Core runtime packages include:

- PyTorch CUDA 12.1 wheels.
- Torchaudio CUDA 12.1 wheels.
- Lightning.
- NumPy.
- Librosa.
- SoundFile.
- Hugging Face Hub.
- PySide6.

The installer and launcher start runtime setup if the private runtime is missing. Setup records doctor readiness in `runtime\setup-status.json`, but missing checkpoints or other readiness warnings should not prevent the GUI from opening so the user can finish setup. If dependency installation itself fails, the launcher should show a visible error and the Start Menu Repair Runtime shortcut should rerun setup in repair mode.

## Model Files

The installer should not include model checkpoints by default.

Model files are downloaded after user confirmation into:

```text
%LOCALAPPDATA%\RollingEdit\A2SB Restorer\models\
```

Recommended two-split checkpoints total roughly 4.5 GB.

## Logs and Jobs

Logs and job manifests should be written under user app data/log folders, not Program Files.

## Caches

Restore subprocesses should use app-owned cache folders under user app data:

```text
%LOCALAPPDATA%\RollingEdit\A2SB Restorer\cache\
```

The app sets Hugging Face, Torch, matplotlib, and XDG cache environment variables for restore workers so model/runtime cache files stay in the app-owned location.

## What Setup Does Not Install

Setup must not silently install:

- NVIDIA GPU drivers.
- Global Python packages.
- Conda environments.
- WSL.
- Docker.
- Checkpoint files without user confirmation.

Uninstall should remove installed app files and the private runtime under the install folder. It must not silently delete user-downloaded model checkpoints under user app data.
