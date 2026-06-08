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

### Verified

- `.\.venv\Scripts\python.exe -m pytest` passes with 26 tests.
- `.\.venv\Scripts\python.exe -m rolling_a2sb.cli doctor --json` runs and reports expected missing Torch/checkpoint readiness failures in the lightweight dev venv while detecting the local NVIDIA GPU through `nvidia-smi`.

### Notes

- `Publish Release` workflows must not be triggered without explicit user confirmation and a release tag.
- The real CUDA/Torch/checkpoint restore path is not complete yet; this change creates the tested foundation for Phase A.
