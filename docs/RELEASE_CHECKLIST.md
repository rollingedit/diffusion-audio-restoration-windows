# Release Checklist

Do not publish a release until every required item is checked with evidence. Record the evidence in `docs/RELEASE_EVIDENCE.md` for the release candidate.

## Runtime

- [x] Clean Windows 10/11 install tested.
- [x] Per-user install works without admin rights.
- [x] `scripts/setup_runtime.ps1` succeeds.
- [x] `scripts/repair_runtime.ps1` succeeds after deleting/reusing runtime.
- [x] `a2sb doctor --json` passes in the installed runtime.
- [x] NVIDIA GPU is detected.
- [x] CUDA is available through PyTorch.
- [x] Bundled FFmpeg and ffprobe are detected.
- [x] `scripts\fetch_ffmpeg.ps1` was used, or the exact equivalent BtbN Windows x64 LGPL build source is documented.
- [x] `bin\ffmpeg-manifest.json` hashes match `bin\ffmpeg.exe` and `bin\ffprobe.exe`.

## Model Setup

- [x] Hugging Face two-split download succeeds.
- [x] Download resume works after interruption.
- [x] Disk-space guard is shown before download.
- [x] Checkpoint manifest is written.
- [x] Manual checkpoint folder selection works.
- [x] Missing checkpoint names are shown exactly.
- [x] Untrusted manual checkpoint warning is shown.

## Restore

- [x] WAV input restores successfully.
- [x] MP3 input restores or fails with a clear supported-format message.
- [x] FLAC input restores or fails with a clear supported-format message.
- [x] Output WAV is created.
- [x] Output is 44.1 kHz mono.
- [x] Input file is unchanged.
- [x] Paths with spaces work.
- [x] Existing output filename increments safely.
- [x] Cancel does not corrupt input or final output.
- [x] Logs are written.

## User Experience

- [x] No terminal is required for normal use.
- [x] No YAML editing is required.
- [x] No Conda, WSL, Docker, or Git is required.
- [x] Doctor report includes actionable next steps for failed checks.
- [x] Missing CUDA shows a readable diagnostic.
- [x] Missing checkpoints show setup flow.
- [x] Missing dependencies offer repair.
- [x] Copy Diagnostic Report works.
- [x] Open Output Folder works.
- [x] Open Logs Folder works.
- [x] Open Models Folder works.

## Packaging

- [x] Launcher EXE is built.
- [x] Inno Setup installer is built.
- [x] Start Menu shortcuts are created.
- [x] Uninstall removes app files.
- [x] Uninstall does not silently delete downloaded models.
- [x] `scripts/write_sha256sums.ps1` passes.
- [x] `scripts/release_status.ps1` reports zero blockers.
- [x] `a2sb release-check --artifacts-dir dist\installer --licenses-dir LICENSES` passes.
- [x] `SHA256SUMS.txt` is generated.
- [x] Release validation has license notices matching the exact bundled runtime and FFmpeg artifacts.
- [x] GitHub release includes installer, SHA256 sums, Windows README, and license notices.
- [x] GitHub release does not include checkpoint files.

## License and Notices

- [x] NVIDIA A2SB license is included.
- [x] NVIDIA attribution appears in About/docs.
- [x] Project says it is not affiliated with or endorsed by NVIDIA.
- [x] FFmpeg notice is included.
- [x] Python/runtime notices are included where applicable.
- [x] Privacy statement says audio stays local.
