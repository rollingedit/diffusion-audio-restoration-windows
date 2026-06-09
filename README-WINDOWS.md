# A2SB Restorer for Windows

RollingEdit A2SB Restorer is a local Windows desktop app for restoring audio with NVIDIA's Audio-to-Audio Schrodinger Bridge checkpoints.

The release artifact set is `A2SB-Restorer-Setup.exe`, `SHA256SUMS.txt`, this Windows README, and `LICENSE-NOTICES.txt`. Checkpoints are downloaded or selected by the user and must not be bundled into the GitHub release.

## Current User Flow

1. Install `A2SB-Restorer-Setup.exe`.
2. Launch `A2SB Restorer` from the Start Menu.
3. Run Doctor from the Setup tab.
4. Download the recommended two-split checkpoints or select a trusted checkpoint folder.
5. Open the Restore tab.
6. Drop or select a WAV, MP3, or FLAC file.
7. Select an output path if the default is not desired.
8. Plan the restore and review the generated job/config/log details.
9. Click Restore to run the shared restore workflow in the background.
10. Watch streamed logs/progress, cancel if needed, and open the output folder after completion.

The GUI restore tab uses the shared product restore path for planning and execution, streams subprocess logs, shows exact step progress when upstream output provides counts, supports cancellation, and enables Open Output Folder after success.

## Model Files

The app uses the official Hugging Face repository:

```text
nvidia/audio_to_audio_schrodinger_bridge
```

Default two-split files:

```text
ckpt/A2SB_twosplit_0.0_0.5_release.ckpt
ckpt/A2SB_twosplit_0.5_1.0_release.ckpt
```

Checkpoints are downloaded or selected by the user. They must not be bundled into the GitHub release by default.

## Local Files

The installer should use per-user locations. Models, logs, jobs, and settings belong under user app data, not Program Files. Restored audio defaults next to the input under:

```text
<input folder>\A2SB Restored\
```

Original audio inputs must never be modified.

## Privacy and Network Use

Audio files stay on the user's PC. The app does not upload user audio, model outputs, logs, or diagnostic reports.

Internet access is used only when the user chooses an action that needs it, such as installing runtime dependencies during setup or downloading official model checkpoints from Hugging Face. Manual checkpoint selection does not require internet access.

The app should not include telemetry by default. Any future telemetry or update-check behavior must be opt-in and documented before public release.

## Release Validation

Before publishing, run:

```powershell
a2sb release-check --artifacts-dir dist\installer --licenses-dir LICENSES
```

The GitHub release should include the installer, checksum file, Windows README, and license notices. It should not include checkpoint files.
