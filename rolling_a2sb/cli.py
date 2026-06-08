from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import paths
from .audio_probe import audio_info_dict, probe_audio
from .audio_prepare import prepare_audio
from .checkpoint_manager import (
    checkpoint_paths_from_validation,
    select_manual_checkpoint_folder,
    trusted_manual_checkpoint_warning,
    validate_checkpoint_folder,
)
from .config_builder import RestoreConfigRequest, write_restore_config
from .downloader import build_download_plan, download_model
from .job import create_restore_job, with_config_path
from .log import append_block, append_log
from .runtime_check import diagnostic_text, doctor
from .settings import load_settings, remember_input, reset_model_settings, update_settings
from .worker import inference_command, run_restore_config_streaming


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a2sb")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")
    doctor_parser.add_argument("--report", action="store_true", help="Print a copyable diagnostic report.")

    download_parser = subparsers.add_parser("download-model")
    download_parser.add_argument("--model", choices=["twosplit", "onesplit"], default="twosplit")
    download_parser.add_argument("--target-dir", type=Path)
    download_parser.add_argument("--yes", action="store_true", help="Confirm the multi-GB download.")
    download_parser.add_argument("--no-hash", action="store_true", help="Skip SHA256 calculation after download.")
    download_parser.add_argument("--force", action="store_true", help="Skip the free-space guard.")

    select_parser = subparsers.add_parser("select-checkpoints")
    select_parser.add_argument("folder", type=Path)
    select_parser.add_argument("--model", choices=["twosplit", "onesplit"], default="twosplit")
    select_parser.add_argument("--trust", action="store_true", help="Confirm the checkpoint folder is from a trusted source.")
    select_parser.add_argument("--no-hash", action="store_true", help="Skip SHA256 calculation.")

    probe_parser = subparsers.add_parser("probe")
    probe_parser.add_argument("audio", type=Path)
    probe_parser.add_argument("--json", action="store_true", dest="as_json")

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--input", required=True, type=Path)
    restore_parser.add_argument("--output", type=Path)
    restore_parser.add_argument("--steps", type=int, default=50)
    restore_parser.add_argument("--model", choices=["twosplit", "onesplit"], default="twosplit")
    restore_parser.add_argument("--checkpoint-folder", type=Path)
    restore_parser.add_argument("--trust-manual-checkpoints", action="store_true")
    restore_parser.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("reset-models")
    subparsers.add_parser("open-model-folder")
    subparsers.add_parser("open-logs")

    args = parser.parse_args(argv)

    if args.command == "doctor":
        report = doctor()
        if args.as_json:
            print(json.dumps(report, indent=2))
        elif args.report:
            print(diagnostic_text(report), end="")
        else:
            print("A2SB Restorer doctor:", "ready" if report["ok"] else "not ready")
            for name, check in report.items():
                if name == "ok":
                    continue
                print(f"- {name}: {'ok' if check.get('ok') else 'needs attention'}")
                if check.get("next_action"):
                    print(f"  next: {check['next_action']}")
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

    if args.command == "select-checkpoints":
        try:
            validation, manifest_path = select_manual_checkpoint_folder(
                args.folder,
                mode=args.model,
                trusted=args.trust,
                compute_hashes=not args.no_hash,
            )
        except PermissionError as exc:
            print(str(exc))
            print("Rerun with --trust after confirming the source is trusted.")
            return 2
        print(
            json.dumps(
                {
                    "ok": validation.ok,
                    "mode": validation.mode,
                    "folder": str(Path(args.folder).resolve()),
                    "manifest": str(manifest_path),
                    "files": [str(file.path) for file in validation.files],
                },
                indent=2,
            )
        )
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
        settings = load_settings()
        checkpoint_folder = args.checkpoint_folder or (Path(settings.checkpoint_folder) if settings.checkpoint_folder else paths.models_dir())
        if args.checkpoint_folder:
            if not args.trust_manual_checkpoints:
                print(trusted_manual_checkpoint_warning())
                print("Rerun with --trust-manual-checkpoints after confirming the source is trusted.")
                return 2
            update_settings(
                model_mode=args.model,
                checkpoint_folder=str(checkpoint_folder.resolve()),
                checkpoint_manifest=None,
                trusted_manual_checkpoint_folder=True,
            )

        validation = validate_checkpoint_folder(checkpoint_folder, mode=args.model)
        checkpoint_paths = checkpoint_paths_from_validation(validation)
        job = create_restore_job(args.input, output_audio=args.output, steps=args.steps, model_mode=args.model)
        prepared = prepare_audio(args.input, Path(job.job_dir), dry_run=args.dry_run)
        remember_input(args.input)
        append_log(Path(job.log_path), f"created restore job {job.job_id}")
        append_log(Path(job.log_path), f"input={Path(args.input).resolve()}")
        append_log(Path(job.log_path), f"prepared_input={prepared.prepared_path}")
        append_log(Path(job.log_path), f"audio_converted={prepared.converted}")
        append_log(Path(job.log_path), f"output={job.output_audio}")
        append_log(Path(job.log_path), f"partial_output={job.partial_output_audio}")
        append_log(Path(job.log_path), f"checkpoint_folder={Path(checkpoint_folder).resolve()}")
        config_path = write_restore_config(
            RestoreConfigRequest(
                input_audio=prepared.prepared_path,
                output_audio=Path(job.output_audio),
                checkpoint_paths=checkpoint_paths,
                job_dir=Path(job.job_dir),
                steps=args.steps,
                model_mode=args.model,
                require_input_exists=not (args.dry_run and prepared.converted),
            )
        )
        job = with_config_path(job, config_path)
        append_log(Path(job.log_path), f"config={config_path}")

        if args.dry_run:
            command = inference_command(config_path)
            append_log(Path(job.log_path), "dry-run: restore subprocess was not started")
            print(
                json.dumps(
                    {
                        "job": job.job_id,
                        "job_dir": job.job_dir,
                        "log": job.log_path,
                        "input": job.input_audio,
                        "prepared_input": str(prepared.prepared_path),
                        "audio_converted": prepared.converted,
                        "output": job.output_audio,
                        "partial_output": job.partial_output_audio,
                        "config": str(config_path),
                        "command": [str(part) for part in command],
                    },
                    indent=2,
                )
            )
            return 0

        def log_stream(stream_name: str, line: str) -> None:
            append_log(Path(job.log_path), f"{stream_name}: {line}")

        result = run_restore_config_streaming(config_path, on_line=log_stream)
        append_block(Path(job.log_path), "stdout", result.stdout)
        append_block(Path(job.log_path), "stderr", result.stderr)
        append_log(Path(job.log_path), f"returncode={result.returncode}")
        if result.cancelled:
            append_log(Path(job.log_path), "cancelled=true")
        print(result.stdout, end="")
        print(result.stderr, end="")
        return result.returncode

    if args.command == "reset-models":
        settings = reset_model_settings()
        print(json.dumps({"ok": True, "settings": settings.__dict__}, indent=2))
        return 0

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
