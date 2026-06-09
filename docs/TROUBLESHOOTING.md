# Troubleshooting

## Doctor Says Torch Is Missing

Run Repair Runtime.

For development:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_runtime.ps1
```

The full runtime install downloads PyTorch CUDA wheels and can take time.

For a copyable report:

```powershell
a2sb doctor --report
```

The report includes `next:` lines for failed checks.

## Doctor Says CUDA Is Not Available

This app targets NVIDIA CUDA GPUs. Check:

- The machine has an NVIDIA GPU.
- The NVIDIA driver is installed and current.
- `nvidia-smi` runs in PowerShell.
- The app runtime installed the CUDA PyTorch wheels.

The app should not silently install GPU drivers.

## Doctor Says Checkpoints Are Missing

Use Download Official Model or select a trusted checkpoint folder.

Required two-split files:

```text
A2SB_twosplit_0.0_0.5_release.ckpt
A2SB_twosplit_0.5_1.0_release.ckpt
```

Manual `.ckpt` files must come from a trusted source. PyTorch checkpoint files can execute code when loaded.

## FFmpeg Or ffprobe Is Missing

The release build should bundle FFmpeg and ffprobe. Development builds may use a globally installed FFmpeg.

If probing MP3/FLAC fails, verify:

```powershell
ffmpeg -version
ffprobe -version
```

## Paths With Spaces Fail

This is a bug. Product code must use argument arrays and absolute paths, not shell strings. Capture the diagnostic report and job log.

## Restore Runs Out Of Memory

Try:

- Fewer restore steps.
- A shorter audio file.
- Closing other GPU-heavy applications.

The app should show this as a readable CUDA memory error, not a raw traceback.

## Release Validation Fails

Before publishing, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/write_sha256sums.ps1 -ArtifactsDir dist\installer
```

This command must fail if:

- No release artifacts exist.
- `SHA256SUMS.txt` is missing.
- A checkpoint/model weight file is in the release folder.
- License notice files do not match the exact bundled runtime or FFmpeg artifacts.

Update notice files with the exact source, version, and redistribution details before public release.
