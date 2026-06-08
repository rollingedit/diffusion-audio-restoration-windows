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

### Verified

- `.\.venv\Scripts\python.exe -m pytest` passes with 15 tests.
- `.\.venv\Scripts\python.exe -m rolling_a2sb.cli doctor --json` runs and reports expected missing Torch/checkpoint readiness failures in the lightweight dev venv.

### Notes

- `Publish Release` workflows must not be triggered without explicit user confirmation and a release tag.
- The real CUDA/Torch/checkpoint restore path is not complete yet; this change creates the tested foundation for Phase A.
