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
- FFmpeg and ffprobe binaries, if bundled.

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

## Model Files

The installer should not include model checkpoints by default.

Model files are downloaded after user confirmation into:

```text
%LOCALAPPDATA%\RollingEdit\A2SB Restorer\models\
```

Recommended two-split checkpoints total roughly 4.5 GB.

## Logs and Jobs

Logs and job manifests should be written under user app data/log folders, not Program Files.

## What Setup Does Not Install

Setup must not silently install:

- NVIDIA GPU drivers.
- Global Python packages.
- Conda environments.
- WSL.
- Docker.
- Checkpoint files without user confirmation.

