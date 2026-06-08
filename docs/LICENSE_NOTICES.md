# License Notices

This project wraps NVIDIA Audio-to-Audio Schrodinger Bridge / A2SB for a Windows-first local application.

## NVIDIA A2SB

Upstream repository:

```text
https://github.com/NVIDIA/diffusion-audio-restoration
```

Official checkpoints:

```text
https://huggingface.co/nvidia/audio_to_audio_schrodinger_bridge
```

The app must preserve NVIDIA copyright and license notices. The project is not affiliated with or endorsed by NVIDIA.

The release package should include:

```text
LICENSES/NVIDIA_A2SB_LICENSE.txt
```

## Checkpoints

The installer should not include NVIDIA checkpoint files by default. The app should download them from NVIDIA's official Hugging Face repository after user confirmation, or let the user select a trusted local checkpoint folder.

PyTorch `.ckpt` files can execute code when loaded. Manual checkpoint selection must require trust confirmation.

## FFmpeg

If FFmpeg binaries are redistributed, include a notice and comply with the selected build's license obligations.

The release package should include:

```text
LICENSES/FFMPEG_NOTICE.txt
```

## Python Runtime

If a Python runtime is bundled or installed into the private app runtime, include applicable Python and dependency notices where required.

The release package should include:

```text
LICENSES/PYTHON_NOTICE.txt
```

## Privacy

Audio files stay local. The app should only connect to the internet for dependency installation and model checkpoint download when the user chooses that option.

The app should not include telemetry by default. Any future telemetry, update check, or usage reporting must be opt-in and documented before public release.
