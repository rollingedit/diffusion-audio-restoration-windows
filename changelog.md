# Changelog


This file is local coordination material unless the user explicitly decides to publish it.

## Unreleased

### Added

- Added this `changelog.md` for local change tracking.
- Added initial Python project metadata and `a2sb` console script entrypoint.
- Added `rolling_a2sb` package foundation: path handling, checkpoint validation, config generation, job manifest creation, runtime doctor, subprocess runner, worker command construction, and CLI restore dry-run support.
- Added Windows config marker files for two-split and one-split modes.
- Added pinned initial requirement files for CUDA runtime, GUI, and build/test tooling.
- Added `.gitignore` for local runtime, model, build, and test artifacts.
- Added unit tests for checkpoint validation, config generation, path handling, job manifests, and worker command construction.
- Added Hugging Face checkpoint downloader orchestration with disk-space guard, progress messages, resume-capable `hf_hub_download`, validation, SHA256 manifest writing, and CLI `download-model` support.
- Added audio probing for WAV through the standard library and MP3/FLAC through `ffprobe`, plus CLI `probe` support.
- Added user-facing error classification for missing dependencies, CUDA, checkpoints, checkpoint trust, audio probing, and restore process failures.
- Added `nvidia-smi` GPU detection and diagnostic text generation to the runtime doctor.
- Added CLI `open-model-folder` and `open-logs` helpers.
- Added tests for downloader behavior, audio probing, error mapping, and runtime-check diagnostics.
- Added runtime setup, repair, doctor, smoke restore, launcher build, and installer build PowerShell scripts with dry-run support where appropriate.
- Added user guide, troubleshooting guide, release checklist, license notices, setup disclosure, and license placeholder files that block public release until replaced.
- Added release scaffolding tests for required docs/scripts and release-blocking license placeholders.
- Added bootstrap launcher source and PyInstaller spec that run the private runtime and launch `rolling_a2sb.app`.
- Added Inno Setup installer skeleton for per-user install, app files, scripts, docs, license notices, and Start Menu shortcuts without checkpoint bundling.
- Added minimal `rolling_a2sb.app` and PySide6 GUI shell with doctor status, diagnostics, and model/log folder actions.
- Added launcher, installer, and app entrypoint tests.
- Added persistent `settings.json` handling for model state and recent inputs.
- Added job log helpers and restore dry-run logging.
- Updated restore to use saved checkpoint settings by default and require explicit trust for manual checkpoint folders.
- Added `a2sb reset-models`.
- Added settings and stateful CLI dry-run tests.
- Added partial output path planning in job manifests using a `.partial` suffix inside the job folder.
- Added restore request validation for existing input/checkpoint paths and input/output path separation before config generation.
- Extended restore dry-run JSON and logs with final and partial output paths.
- Added tests for partial output path planning and restore request validation.
- Added release artifact tooling for `SHA256SUMS.txt` generation and release validation.
- Added release gates that block checkpoint/model artifacts and placeholder license notices.
- Integrated checksum generation into the installer build script after a successful Inno Setup build.
- Added tests for checksum generation and release validation.
- Added streaming subprocess runner with stdout/stderr callbacks and cancellation support.
- Updated restore execution to stream subprocess lines into the job log while preserving captured stdout/stderr.
- Added tests for streaming output capture and cancellation.
- Added GUI action service layer for doctor text, download planning, audio probing, and restore dry-run planning without requiring PySide6 in tests.
- Wired the PySide shell to doctor refresh, model download plan display, copy diagnostics, and model/log folder actions.
- Added tests for GUI action service behavior.
- Added `next_action` guidance to failed doctor checks and included it in copyable diagnostic reports.
- Added ffprobe doctor check alongside FFmpeg.
- Added `a2sb doctor --report`.
- Added tests for diagnostic next actions and report CLI output.
- Added controlled audio preparation for restore inputs, including FFmpeg command planning for non-44.1 kHz mono WAV/MP3/FLAC sources.
- Restore config generation now uses a prepared job-local WAV path when conversion is needed, while leaving original input files untouched.
- Restore dry-run output and logs now include prepared input state.
- Added tests for target-WAV passthrough and conversion planning.
- Added trusted manual checkpoint folder selection service.
- Added `a2sb select-checkpoints` with required `--trust`, validation, manifest writing, and settings persistence.
- Added GUI action text for trusted checkpoint folder selection.
- Added tests for manual checkpoint trust enforcement and successful selection.
- Added shared restore workflow preparation so CLI restore and GUI restore dry-run use the same checkpoint validation, job creation, audio preparation, config generation, and logging path.
- Added workflow tests for shared restore planning and manual checkpoint trust enforcement.
- Added a GUI restore tab with audio selection, output selection, checkpoint folder selection, drag-and-drop input support, audio inspection, and restore dry-run planning through the shared workflow.
- Added a GUI source contract test for restore controls and shared action wiring.
- Added a shared non-dry-run restore readiness gate that blocks restore before model execution when Python/imports/Torch CUDA/FFmpeg/write-permission/checkpoint checks are not ready.
- Added CLI and workflow tests for readable restore readiness failures.
- Added retry handling for Hugging Face checkpoint downloads with per-attempt progress messages and CLI `--retries`.
- Added downloader tests for transient retry success and invalid retry counts.
- Added root `README-WINDOWS.md` and `LICENSE-NOTICES.txt` release-source files with explicit public-release blockers.
- Added release scaffold tests for Windows README/notices presence and README blocker content.
- Added user-facing restore error formatting for CUDA OOM, missing FFmpeg/ffprobe, and traceback-heavy failures while preserving raw subprocess output in logs.
- Wired GUI restore planning and CLI failed restore execution to show mapped readable errors.
- Added tests for OOM, FFmpeg, traceback redaction, and nonzero restore subprocess output.
- Added public-facing privacy, network-use, and no-default-telemetry statements to Windows release docs.
- Added release scaffold coverage for privacy and network-use statements.
- Added a product safety test that blocks `shell=True` usage in `rolling_a2sb` and the launcher while leaving upstream research files explicitly out of the product path.
- Added direct validator coverage that generated restore configs reject upstream `PATH/TO` placeholders before release.
- Added Unicode-path job manifest/output planning coverage for non-ASCII input folders and filenames.
- Added explicit runtime doctor tests for CUDA-unavailable and missing-FFmpeg failure reporting.
- Added GUI recommended-model download confirmation/action service with official source, required bytes, local model folder, internet requirement, and progress result text.
- Wired the setup tab with a `Download Recommended Model` button that asks for confirmation before calling the shared download service.
- Added GUI action/source tests for model download confirmation and progress formatting.
- Added a GUI Logs tab with latest restore log display, copy log, and open logs folder actions.
- Added GUI action/source tests for latest-log empty and newest-log behavior.
- Added app-owned worker cache environment variables for Hugging Face, Torch, matplotlib, and XDG cache paths.
- Documented app-owned cache location in setup disclosure.
- Added path and worker tests for cache directory creation and worker environment values.
- Added release validation coverage that blocks `.pt`, `.pth`, and `.safetensors` model weight files from release artifacts.

### Verified

- `.\.venv\Scripts\python.exe -m pytest` passes with 91 tests.
- `.\.venv\Scripts\python.exe -m rolling_a2sb.cli doctor --report` prints actionable next steps for missing Torch/checkpoints and sandboxed write permissions.
- `powershell -ExecutionPolicy Bypass -File scripts/write_sha256sums.ps1 -ArtifactsDir dist\installer -ValidateOnly` runs and correctly blocks release because artifacts are missing and license notices are placeholders.
- `.\.venv\Scripts\python.exe -m rolling_a2sb.cli doctor --json` runs and reports expected missing Torch/checkpoint readiness failures in the lightweight dev venv while detecting the local NVIDIA GPU through `nvidia-smi`.
- `powershell -ExecutionPolicy Bypass -File scripts/setup_runtime.ps1 -DryRun -Json` succeeds without modifying the runtime.

### Notes

- `Publish Release` workflows must not be triggered without explicit user confirmation and a release tag.
- The real CUDA/Torch/checkpoint restore path is not complete yet; this change creates the tested foundation for Phase A.
