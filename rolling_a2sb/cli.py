from __future__ import annotations

import argparse
import json
from pathlib import Path

from .checkpoint_manager import checkpoint_paths_from_validation, validate_checkpoint_folder
from .config_builder import RestoreConfigRequest, write_restore_config
from .job import create_restore_job, with_config_path
from .runtime_check import doctor
from .worker import inference_command, run_restore_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a2sb")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--input", required=True, type=Path)
    restore_parser.add_argument("--output", type=Path)
    restore_parser.add_argument("--steps", type=int, default=50)
    restore_parser.add_argument("--model", choices=["twosplit", "onesplit"], default="twosplit")
    restore_parser.add_argument("--checkpoint-folder", type=Path)
    restore_parser.add_argument("--dry-run", action="store_true")

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

    if args.command == "restore":
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

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

