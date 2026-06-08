from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import paths
from .audio_probe import audio_info_dict, probe_audio
from .checkpoint_manager import select_manual_checkpoint_folder
from .downloader import build_download_plan, download_model
from .errors import RestoreProcessError, format_user_error
from .runtime_check import diagnostic_text, doctor
from .settings import reset_model_settings
from .workflow import execute_restore, prepare_restore


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
    download_parser.add_argument("--retries", type=int, default=3, help="Attempts per checkpoint download.")

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
            retries=args.retries,
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
        try:
            plan = None
            execution = None
            if args.dry_run:
                plan = prepare_restore(
                    input_audio=args.input,
                    output_audio=args.output,
                    steps=args.steps,
                    model_mode=args.model,
                    checkpoint_folder=args.checkpoint_folder,
                    trust_manual_checkpoints=args.trust_manual_checkpoints,
                    dry_run=True,
                )
            else:
                execution = execute_restore(
                    input_audio=args.input,
                    output_audio=args.output,
                    steps=args.steps,
                    model_mode=args.model,
                    checkpoint_folder=args.checkpoint_folder,
                    trust_manual_checkpoints=args.trust_manual_checkpoints,
                )
        except PermissionError as exc:
            print(str(exc))
            print("Rerun with --trust-manual-checkpoints after confirming the source is trusted.")
            return 2
        except RuntimeError as exc:
            print(str(exc))
            return 1

        if args.dry_run:
            assert plan is not None
            print(
                json.dumps(
                    {
                        "job": plan.job_id,
                        "job_dir": plan.job_dir,
                        "log": plan.log_path,
                        "input": plan.input_audio,
                        "prepared_input": plan.prepared_input_audio,
                        "audio_converted": plan.audio_converted,
                        "output": plan.output_audio,
                        "partial_output": plan.partial_output_audio,
                        "config": plan.config_path,
                        "command": plan.command,
                    },
                    indent=2,
                )
            )
            return 0

        assert execution is not None
        if execution.returncode == 0:
            print(execution.stdout, end="")
            print(execution.stderr, end="")
        else:
            print(format_user_error(RestoreProcessError(execution.stderr or execution.stdout or "Restore process failed.")))
        return execution.returncode

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
