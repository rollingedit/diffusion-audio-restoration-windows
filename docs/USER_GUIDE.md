# A2SB Restorer User Guide

This document describes the intended public Windows user flow. It should be updated as the GUI and installer are implemented.

## Install

1. Download `A2SB-Restorer-Setup.exe` from the GitHub release.
2. Run the installer.
3. Launch `A2SB Restorer` from the Start Menu.

The app should install per-user by default and should not require administrator rights.

## First Launch

On first launch, the app should check:

- Python runtime.
- PyTorch and CUDA.
- NVIDIA GPU/driver visibility.
- FFmpeg/ffprobe.
- Writable app data, model, log, and job folders.
- A2SB checkpoint files.

If model checkpoints are missing, choose one of:

- Download Recommended Model.
- Use Existing Checkpoint Folder.

The recommended model is the official NVIDIA two-split A2SB checkpoint set from Hugging Face:

- `ckpt/A2SB_twosplit_0.0_0.5_release.ckpt`
- `ckpt/A2SB_twosplit_0.5_1.0_release.ckpt`

The Restore tab also exposes `onesplit` as an advanced model mode. Keep `twosplit` as the default until a real two-split smoke restore has passed; use `onesplit` only with the matching official one-split checkpoint.

## Restore Audio

1. Drag a WAV, MP3, or FLAC file into the app, or choose one with the file picker.
2. Confirm the output folder.
3. Click Restore.
4. Wait for the job to complete.
5. Click Open Output Folder.

The default output path should be:

```text
<input folder>\A2SB Restored\<input name>__a2sb.wav
```

The original input file must never be modified.

## Logs and Diagnostics

Use Open Logs or Copy Diagnostic Report when reporting failures. Logs should include tracebacks and subprocess output; the main UI should show readable summaries.
