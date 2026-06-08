# Release Checklist

Do not publish a release until every required item is checked with evidence.

## Runtime

- [ ] Clean Windows 10/11 install tested.
- [ ] Per-user install works without admin rights.
- [ ] `scripts/setup_runtime.ps1` succeeds.
- [ ] `scripts/repair_runtime.ps1` succeeds after deleting/reusing runtime.
- [ ] `a2sb doctor --json` passes in the installed runtime.
- [ ] NVIDIA GPU is detected.
- [ ] CUDA is available through PyTorch.
- [ ] Bundled FFmpeg and ffprobe are detected.

## Model Setup

- [ ] Hugging Face two-split download succeeds.
- [ ] Download resume works after interruption.
- [ ] Disk-space guard is shown before download.
- [ ] Checkpoint manifest is written.
- [ ] Manual checkpoint folder selection works.
- [ ] Missing checkpoint names are shown exactly.
- [ ] Untrusted manual checkpoint warning is shown.

## Restore

- [ ] WAV input restores successfully.
- [ ] MP3 input restores or fails with a clear supported-format message.
- [ ] FLAC input restores or fails with a clear supported-format message.
- [ ] Output WAV is created.
- [ ] Output is 44.1 kHz mono.
- [ ] Input file is unchanged.
- [ ] Paths with spaces work.
- [ ] Existing output filename increments safely.
- [ ] Cancel does not corrupt input or final output.
- [ ] Logs are written.

## User Experience

- [ ] No terminal is required for normal use.
- [ ] No YAML editing is required.
- [ ] No Conda, WSL, Docker, or Git is required.
- [ ] Missing CUDA shows a readable diagnostic.
- [ ] Missing checkpoints show setup flow.
- [ ] Missing dependencies offer repair.
- [ ] Copy Diagnostic Report works.
- [ ] Open Output Folder works.
- [ ] Open Logs Folder works.
- [ ] Open Models Folder works.

## Packaging

- [ ] Launcher EXE is built.
- [ ] Inno Setup installer is built.
- [ ] Start Menu shortcuts are created.
- [ ] Uninstall removes app files.
- [ ] Uninstall does not silently delete downloaded models.
- [ ] `scripts/write_sha256sums.ps1` passes.
- [ ] `SHA256SUMS.txt` is generated.
- [ ] Release validation has no placeholder license notices.
- [ ] GitHub release includes installer, SHA256 sums, Windows README, and license notices.
- [ ] GitHub release does not include checkpoint files.

## License and Notices

- [ ] NVIDIA A2SB license is included.
- [ ] NVIDIA attribution appears in About/docs.
- [ ] Project says it is not affiliated with or endorsed by NVIDIA.
- [ ] FFmpeg notice is included.
- [ ] Python/runtime notices are included where applicable.
- [ ] Privacy statement says audio stays local.
