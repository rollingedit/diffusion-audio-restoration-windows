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

Public Windows releases should bundle FFmpeg and ffprobe from the BtbN FFmpeg Builds project, using the Windows x64 LGPL static release build family.

Planned build family:

```text
https://github.com/BtbN/FFmpeg-Builds
win64-lgpl release build, not nonfree, not GPL
```

The app only needs local audio probing/conversion for WAV, MP3, and FLAC restore preparation. Do not switch to a GPL or nonfree FFmpeg build unless the release license posture is reviewed first.

Before public release, replace the placeholder notice with the exact FFmpeg version/build filename, upstream source URL, license text, source-code offer or link, and any required redistribution notices for the bundled binaries.

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
