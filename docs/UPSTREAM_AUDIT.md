# Upstream Audit

This file records the upstream NVIDIA A2SB behavior that matters for the Windows product wrapper.

## Destination Repo

This repository is the RollingEdit Windows productization fork:

```text
rollingedit/diffusion-audio-restoration-windows
```

Treat this repo as the destination product repo. Keep upstream NVIDIA files in place unless moving them has been proven not to break imports.

## Preserved Upstream Source

The root model and engine files are still used by the product path:

- `ensembled_inference_api.py`
- `A2SB_lightning_module_api.py`
- `datasets/datamodule.py`
- `audio_transforms/`
- `corruption/`
- `diffusion.py`
- `networks.py`

The product wrapper calls NVIDIA's LightningCLI entrypoint through:

```text
python ensembled_inference_api.py predict -c <generated restore_config.yaml>
```

The command is built as a subprocess argument array in `rolling_a2sb.worker`, with `cwd` set to the engine root.

## Upstream Entry Points

Primary inference entrypoint:

```text
ensembled_inference_api.py
```

This creates a LightningCLI around:

- `TimePartitionedPretrainedSTFTBridgeModel`
- `STFTAudioDataModule`

Research convenience wrappers under `inference/` are not the product restore path.

## Upstream Assumptions Bypassed By Product Code

The upstream research wrappers under `inference/` include behavior that is unsafe or fragile for a Windows desktop product:

- `Popen(..., shell=True)`
- command strings using `cd ../`
- generated temporary YAML under relative paths
- placeholder path assumptions such as `PATH/TO/MANIFEST/FOLDER`

The product path bypasses these wrappers and uses:

- argument-array subprocess execution
- explicit engine root working directory
- generated absolute-path restore YAML
- job-local logs and config files
- checkpoint validation before execution

## Upstream Config Assumptions Sanitized By Product Code

The upstream configs may include research/HPC defaults such as:

- `SLURMEnvironment`
- placeholder checkpoint paths
- placeholder manifest roots
- distributed/HPC trainer assumptions

`rolling_a2sb.config_builder` generates restore configs that must:

- contain no `PATH/TO` placeholders
- contain no `SLURMEnvironment`
- use `trainer.strategy: auto`
- use `trainer.devices: 1`
- use `trainer.num_nodes: 1`
- use `data.num_workers: 0`
- use `data.batch_size: 1`
- use absolute input, output, and checkpoint paths

## Current Upstream Patch Policy

Keep upstream files mostly intact for the first public Windows product unless a real restore smoke test proves a patch is required.

Document every upstream behavior change before release. If a future agent patches upstream source, add:

- exact file and function changed
- reason the wrapper could not bypass it
- before/after behavior
- smoke-test evidence

## Still Needs Real Validation

This audit does not prove Windows CUDA inference works. Public release still requires:

- installed private runtime
- real two-split checkpoint download or trusted selection
- short WAV restore smoke test
- output WAV verification
- no traceback in GUI
- logs written and readable
