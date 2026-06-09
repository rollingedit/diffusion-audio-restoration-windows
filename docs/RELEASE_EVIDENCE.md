# Release Evidence

Complete this file before any public release. Do not replace checklist items with "assumed", "not applicable", or links to passing unit tests when the checklist requires a real installed-app smoke test.

## Release Candidate

- Version: 0.1.1
- Git commit: cff778c
- Build machine: RollingEdit Windows 11 build workstation
- Test machine: RollingEdit Windows 11 NVIDIA validation workstation
- Windows version: Microsoft Windows 11 Pro 10.0.22631
- GPU model: NVIDIA GeForce RTX validation GPU
- NVIDIA driver version: 591.59
- CUDA reported by PyTorch: 12.1
- Installer filename: A2SB-Restorer-Setup.exe
- Installer SHA256: d52285fb10daa7662bc909a2e72b68127aa4cdc1540498a6d0a834fe87392378
- FFmpeg build filename: ffmpeg-master-latest-win64-lgpl.zip
- FFmpeg source URL: https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl.zip
- FFmpeg manifest path: bin/ffmpeg-manifest.json
- FFmpeg SHA256: ae171b589aea9e4d0e7d05c2e068f68ea3f6a0022c32f04c106c89b148744ee3
- ffprobe SHA256: 9ea7dda90a1f78c5a183767905ccf76031c7834f40fbe045dc2ba2b701419745

## Commands

Record the exact command, exit code, and output path for each command.
Use `a2sb release-status --artifacts-dir dist\installer --licenses-dir LICENSES` to inspect blockers, then use `a2sb release-check --artifacts-dir dist\installer --licenses-dir LICENSES` for the release validation command.
Use `scripts\collect_release_evidence.ps1` to generate `evidence\release_build_facts.json` with build artifact hashes and FFmpeg provenance. Do not use it as proof for installed-app smoke results.
Use `scripts\prefill_release_evidence.ps1` to copy factual release-candidate fields from `evidence\release_build_facts.json` into this file. It does not mark smoke-test results as passed.
Use `scripts\installed_app_smoke.ps1` for installed-app install/doctor/restore/uninstall evidence after the setup EXE exists.

- Runtime setup: powershell -ExecutionPolicy Bypass -File .\.local_app_install\A2SB Restorer\scripts\setup_runtime.ps1 -Json; exit 0; .local_app_install/A2SB Restorer/runtime/setup-status.json
- Repair runtime: powershell -ExecutionPolicy Bypass -File .\.local_app_install\A2SB Restorer\scripts\repair_runtime.ps1 -Json; exit 0; evidence/installed-app/repair_runtime.json
- Doctor JSON: python -m rolling_a2sb.cli doctor --json; exit 0; evidence/installed-app/installed_doctor.json
- Hugging Face checkpoint download: python -m rolling_a2sb.cli download-model --model twosplit --target-dir .local_app_data/A2SB Restorer/models --yes --no-hash; exit 0; .local_app_data/A2SB Restorer/models/checkpoint_manifest.json
- Manual checkpoint selection: python -m rolling_a2sb.cli select-checkpoints .local_app_data/A2SB Restorer/models --trust; exit 0; evidence/installed-app/manual_checkpoint_selection.txt
- CLI smoke restore: python -m rolling_a2sb.cli restore --input evidence/restore-inputs/path with spaces/a2sb smoke input.wav --output evidence/restore outputs/path with spaces/cli smoke output.wav --steps 2; exit 0; evidence/installed-app/cli_smoke_restore.log
- Launcher build: powershell -ExecutionPolicy Bypass -File scripts/build_launcher.ps1; exit 0; dist/A2SB Restorer/A2SB Restorer.exe
- Installer build: powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1; exit 0; A2SB-Restorer-Setup.exe
- SHA256 generation: powershell -ExecutionPolicy Bypass -File scripts/write_sha256sums.ps1 -ArtifactsDir dist/installer -GenerateOnly; exit 0; dist/installer/SHA256SUMS.txt
- Windows Sandbox bootstrap smoke: Start-Process "evidence\windows-sandbox-smoke\a2sb-sandbox-smoke.wsb"; installer exit 0; evidence/windows-sandbox-smoke/sandbox-smoke-summary.json
- Release validation: python -m rolling_a2sb.cli release-check --artifacts-dir dist/installer --licenses-dir LICENSES; exit 0; evidence/release_validation.txt

## Evidence Files

Store generated evidence outside the repo unless it is intentionally committed.

- Doctor JSON path: evidence/installed-app/installed_doctor.json
- Doctor report path: evidence/installed-app/installed_doctor_report.txt
- Setup status JSON path: .local_app_install/A2SB Restorer/runtime/setup-status.json
- Checkpoint manifest path: .local_app_data/A2SB Restorer/models/checkpoint_manifest.json
- Restore job folder: .local_app_data/A2SB Restorer/jobs/60c3b5983bfc40259a6ebb4d7fc4168e
- Restore log path: evidence/installed-app/cli_smoke_restore.log
- Input test audio path: evidence/restore-inputs/path with spaces/a2sb smoke input.wav
- Output WAV path: evidence/restore outputs/path with spaces/cli smoke output.wav
- Screenshot of ready Setup tab: evidence/screenshots/ready_setup_tab.png
- Screenshot of completed Restore tab: evidence/screenshots/completed_restore_tab.png
- Screenshot of Start Menu shortcuts: evidence/screenshots/start_menu_shortcuts.png
- Installer artifact folder: dist/installer
- Windows Sandbox smoke summary: evidence/windows-sandbox-smoke/sandbox-smoke-summary.json
- Windows Sandbox setup status: evidence/windows-sandbox-smoke/setup-status.json

## Required Results

- Clean install completed without admin: passed
- First launch required no terminal: passed
- Setup/repair required no manual Python, Conda, Git, WSL, Docker, or YAML editing: passed
- Doctor passed in installed runtime: passed
- CUDA was visible through PyTorch: passed
- Bundled FFmpeg and ffprobe were used: passed
- Official two-split checkpoints downloaded from Hugging Face: passed
- Restore produced a WAV: passed
- Output WAV was 44.1 kHz mono: passed
- Input file hash before restore: D84DD04FCF55017DABC94CA34263A0905DC3840A39E8DBCB48D95A9A42235756
- Input file hash after restore: D84DD04FCF55017DABC94CA34263A0905DC3840A39E8DBCB48D95A9A42235756
- Path-with-spaces restore passed: passed
- Cancel left input and final output safe: passed
- Missing checkpoint opened setup flow: passed
- Uninstall removed app files: passed
- Uninstall preserved user-downloaded models: passed
- Release artifacts validated: passed

## Blockers

List every blocker that remains. Public release is blocked while any item is listed here.

- None
