from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import paths
from .audio_probe import audio_info_dict, probe_audio
from .checkpoint_manager import checkpoint_paths_from_validation, validate_checkpoint_folder
from .config_builder import RestoreConfigRequest, write_restore_config
from .downloader import build_download_plan, download_model
from .job import create_restore_job, with_config_path
from .runtime_check import doctor
from .worker import inference_command, run_restore_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a2sb")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")

    download_parser = subparsers.add_parser("download-model")
    download_parser.add_argument("--model", choices=["twosplit", "onesplit"], default="twosplit")
    download_parser.add_argument("--target-dir", type=Path)
    download_parser.add_argument("--yes", action="store_true", help="Confirm the multi-GB download.")
    download_parser.add_argument("--no-hash", action="store_true", help="Skip SHA256 calculation after download.")
    download_parser.add_argument("--force", action="store_true", help="Skip the free-space guard.")

    probe_parser = subparsers.add_parser("probe")
    probe_parser.add_argument("audio", type=Path)
    probe_parser.add_argument("--json", action="store_true", dest="as_json")

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--input", required=True, type=Path)
    restore_parser.add_argument("--output", type=Path)
    restore_parser.add_argument("--steps", type=int, default=50)
    restore_parser.add_argument("--model", choices=["twosplit", "onesplit"], default="twosplit")
    restore_parser.add_argument("--checkpoint-folder", type=Path)
    restore_parser.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("open-model-folder")
    subparsers.add_parser("open-logs")

    args = parser.parse_args(argv)

    if args.command == "doctor":
        report = doctor()
        if args.as_json:
            print(json.dumps(report, indent=2))
        else:
            print("A2SB Restorer doctor:", "ready" if report["ok"] else "not ready")
            for name, check in report.items():
                if name == "ok":
                    continue
                print(f"- {name}: {'ok' if check.get('ok') else 'needs attention'}")
        return 0 if report["ok"] else 1

    if args.command == "download-model":
        plan = build_download_plan(mode=args.model, target_dir=args.target_dir)
        if not args.yes:
            print(
                json.dumps(
                    {
                        "confirmation_required": True,
                        "repo_id": plan.repo_id,
                        "model": plan.mode,
                        "files": plan.filenames,
                        "target_dir": str(plan.target_dir),
                        "required_bytes": plan.required_bytes,
                        "free_bytes": plan.free_bytes,
                        "enough_space": plan.enough_space,
                        "next_command": f"a2sb download-model --model {plan.mode} --yes",
                    },
                    indent=2,
                )
            )
            return 2

        result = download_model(
            mode=args.model,
            target_dir=args.target_dir,
            force=args.force,
            compute_hashes=not args.no_hash,
            progress=lambda message: print(message, flush=True),
        )
        print(json.dumps({"ok": result.validation.ok, "manifest": str(result.manifest_path)}, indent=2))
        return 0

    if args.command == "probe":
        info = probe_audio(args.audio)
        if args.as_json:
            print(json.dumps(audio_info_dict(info), indent=2))
        else:
            print(f"Audio: {info.path}")
            print(f"- format: {info.format}")
            print(f"- duration_seconds: {info.duration_seconds}")
            print(f"- sample_rate: {info.sample_rate}")
            print(f"- channels: {info.channels}")
        return 0

    if args.command == "restore":
        probe_audio(args.input)
        validation = validate_checkpoint_folder(args.checkpoint_folder or Path.cwd(), mode=args.model)
        checkpoint_paths = checkpoint_paths_from_validation(validation)
        job = create_restore_job(args.input, output_audio=args.output, steps=args.steps, model_mode=args.model)
        config_path = write_restore_config(
            RestoreConfigRequest(
                input_audio=args.input,
                output_audio=Path(job.output_audio),
                checkpoint_paths=checkpoint_paths,
                job_dir=Path(job.job_dir),
                steps=args.steps,
                model_mode=args.model,
            )
        )
        job = with_config_path(job, config_path)

        if args.dry_run:
            command = inference_command(config_path)
            print(json.dumps({"job": job.job_id, "config": str(config_path), "command": [str(part) for part in command]}, indent=2))
            return 0

        result = run_restore_config(config_path)
        print(result.stdout, end="")
        print(result.stderr, end="")
        return result.returncode

    if args.command == "open-model-folder":
        return _open_folder(paths.models_dir())

    if args.command == "open-logs":
        return _open_folder(paths.logs_dir())

    return 2


def _open_folder(path: Path) -> int:
    path.mkdir(parents=True, exist_ok=True)
    os.startfile(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
