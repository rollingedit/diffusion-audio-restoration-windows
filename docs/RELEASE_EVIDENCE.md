# Release Evidence

Complete this file before any public release. Do not replace checklist items with "assumed", "not applicable", or links to passing unit tests when the checklist requires a real installed-app smoke test.

## Release Candidate

- Version:
- Git commit:
- Build machine:
- Test machine:
- Windows version:
- GPU model:
- NVIDIA driver version:
- CUDA reported by PyTorch:
- Installer filename:
- Installer SHA256:
- FFmpeg build filename:
- FFmpeg source URL:

## Commands

Record the exact command, exit code, and output path for each command.

- Runtime setup:
- Repair runtime:
- Doctor JSON:
- Hugging Face checkpoint download:
- Manual checkpoint selection:
- CLI smoke restore:
- Launcher build:
- Installer build:
- SHA256 generation:
- Release validation:

## Evidence Files

Store generated evidence outside the repo unless it is intentionally committed.

- Doctor JSON path:
- Doctor report path:
- Setup status JSON path:
- Checkpoint manifest path:
- Restore job folder:
- Restore log path:
- Input test audio path:
- Output WAV path:
- Screenshot of ready Setup tab:
- Screenshot of completed Restore tab:
- Screenshot of Start Menu shortcuts:
- Installer artifact folder:

## Required Results

- Clean install completed without admin:
- First launch required no terminal:
- Setup/repair required no manual Python, Conda, Git, WSL, Docker, or YAML editing:
- Doctor passed in installed runtime:
- CUDA was visible through PyTorch:
- Bundled FFmpeg and ffprobe were used:
- Official two-split checkpoints downloaded from Hugging Face:
- Restore produced a WAV:
- Output WAV was 44.1 kHz mono:
- Input file hash before restore:
- Input file hash after restore:
- Path-with-spaces restore passed:
- Cancel left input and final output safe:
- Missing checkpoint opened setup flow:
- Uninstall removed app files:
- Uninstall preserved user-downloaded models:
- Release artifacts validated:

## Blockers

List every blocker that remains. Public release is blocked while any item is listed here.

- 
