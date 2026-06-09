from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from .audio_probe import audio_info_dict, probe_audio
from .checkpoint_manager import select_manual_checkpoint_folder
from .downloader import ByteProgressCallback, build_download_plan, download_model
from . import paths
from .runtime_check import diagnostic_text, doctor
from .subprocess_runner import run_command_streaming
from .workflow import RestorePreparation as DryRunRestorePlan
from .workflow import execute_restore, prepare_restore


LineCallback = Callable[[str, str], None]
STEP_PROGRESS_PATTERNS = [
    re.compile(r"\b(?:step|sampling step|predict step)\s*(\d+)\s*(?:/|of)\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*/\s*(\d+)\b"),
]


def about_text() -> str:
    return "\n".join(
        [
            "A2SB Restorer",
            "Experimental RollingEdit Windows app for NVIDIA Audio-to-Audio Schrodinger Bridge restoration.",
            "GitHub: https://github.com/rollingedit/diffusion-audio-restoration-windows",
            "",
            "Uses upstream NVIDIA A2SB engine code and official NVIDIA Hugging Face checkpoints.",
            "This project is not affiliated with or endorsed by NVIDIA.",
            "The upstream model card says the model is for non-commercial use only.",
            "Review the included NVIDIA A2SB license before commercial or production use.",
            "Audio stays local on this PC.",
            "",
            "License notices are installed under the app LICENSES and docs folders.",
        ]
    )


def about_html() -> str:
    return """
<h2>A2SB Restorer</h2>
<p>Experimental RollingEdit Windows app for NVIDIA Audio-to-Audio Schrodinger Bridge restoration.</p>
<p><a href="https://github.com/rollingedit/diffusion-audio-restoration-windows">GitHub repository</a></p>
<p>Uses upstream NVIDIA A2SB engine code and official NVIDIA Hugging Face checkpoints. This project is not affiliated with or endorsed by NVIDIA.</p>
<p><b>Use warning:</b> the upstream model card says the model is for non-commercial use only. Review the included NVIDIA A2SB license before commercial or production use.</p>
<p>Audio stays local on this PC. License notices are installed under the app LICENSES and docs folders.</p>
"""


def task_mode_help_text(task_mode: str) -> str:
    if task_mode == "inpaint":
        return (
            "Inpainting\n\n"
            "Repairs a short damaged or missing time range. Pick the gap start and end times; "
            "A2SB supports short gaps under 1 second."
        )
    return (
        "Bandwidth extension\n\n"
        "For dull, low-passed, or bandwidth-limited audio. The app predicts missing high-frequency detail "
        "above the cutoff and writes a new WAV beside the input by default."
    )


def doctor_report_text() -> str:
    return diagnostic_text(doctor())


def _format_gb(bytes_count: int) -> str:
    return f"{bytes_count / (1024**3):.1f} GB"


def download_plan_text(mode: str = "twosplit", target_dir: Path | None = None) -> str:
    plan = build_download_plan(mode=mode, target_dir=target_dir)
    lines = [
        "Official model download",
        f"Source: {plan.repo_id}",
        f"Model: {plan.mode}",
        f"Save to: {plan.target_dir}",
        f"Needs about: {_format_gb(plan.required_bytes)}",
        f"Free space here: {_format_gb(plan.free_bytes)}",
        f"Space check: {'ok' if plan.enough_space else 'not enough space'}",
        "",
        "Files:",
    ]
    lines.extend(f"- {filename}" for filename in plan.filenames)
    return "\n".join(lines) + "\n"


def model_download_progress(mode: str = "twosplit", target_dir: Path | None = None) -> tuple[int, int]:
    plan = build_download_plan(mode=mode, target_dir=target_dir)
    downloaded = 0
    for filename in plan.filenames:
        path = plan.target_dir / filename
        if path.exists():
            downloaded += min(path.stat().st_size, plan.required_bytes)
    return min(downloaded, plan.required_bytes), plan.required_bytes


def model_download_confirmation_text(mode: str = "twosplit", target_dir: Path | None = None) -> str:
    plan = build_download_plan(mode=mode, target_dir=target_dir)
    lines = [
        "Download the official NVIDIA model checkpoints?",
        "",
        f"Source: {plan.repo_id}",
        f"Model: {plan.mode}",
        f"Save to: {plan.target_dir}",
        f"Download size estimate: {_format_gb(plan.required_bytes)}",
        f"Free space here: {_format_gb(plan.free_bytes)}",
        f"Space check: {'ok' if plan.enough_space else 'not enough space'}",
        "Internet access is required for this action.",
        "",
        "Files:",
    ]
    lines.extend(f"- {filename}" for filename in plan.filenames)
    return "\n".join(lines) + "\n"


def download_recommended_model_text(mode: str = "twosplit", target_dir: Path | None = None) -> str:
    progress: list[str] = []
    result = download_model(
        mode=mode,
        target_dir=target_dir,
        progress=progress.append,
    )
    return format_model_download_result(result, progress)


def download_recommended_model_stream_text(
    mode: str = "twosplit",
    target_dir: Path | None = None,
    on_progress: Callable[[str], None] | None = None,
    on_progress_bytes: ByteProgressCallback | None = None,
) -> str:
    progress: list[str] = []

    def collect(line: str) -> None:
        progress.append(line)
        if on_progress:
            on_progress(line)

    result = download_model(mode=mode, target_dir=target_dir, progress=collect, byte_progress=on_progress_bytes)
    return format_model_download_result(result, progress)


def format_model_download_result(result, progress: list[str]) -> str:
    lines = [
        "Model download complete." if result.validation.ok else "Model download finished, but validation needs attention.",
        f"Model: {result.mode}",
        f"Manifest: {result.manifest_path}",
        "",
        "Progress:",
    ]
    lines.extend(f"- {line}" for line in progress)
    lines.append("")
    lines.append("Files:")
    lines.extend(f"- {path}" for path in result.files)
    return "\n".join(lines) + "\n"


def audio_probe_text(audio_path: Path) -> str:
    return json.dumps(audio_info_dict(probe_audio(audio_path)), indent=2)


def latest_restore_log_text(log_root: Path | None = None) -> str:
    root = log_root or paths.jobs_dir()
    logs = sorted(Path(root).glob("*/restore.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not logs:
        return "No restore logs found."
    latest = logs[0]
    return f"Latest restore log: {latest}\n\n{latest.read_text(encoding='utf-8', errors='replace')}"


def repair_runtime_text(on_line: LineCallback | None = None) -> str:
    script = paths.app_install_dir() / "scripts" / "repair_runtime.ps1"
    if not script.exists():
        raise FileNotFoundError(f"Repair script was not found: {script}")
    result = run_command_streaming(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script, "-Json"],
        cwd=paths.app_install_dir(),
        on_line=on_line,
    )
    return json.dumps(
        {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
        indent=2,
    )


def parse_restore_step_progress(line: str) -> tuple[int, int] | None:
    for pattern in STEP_PROGRESS_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        current = int(match.group(1))
        total = int(match.group(2))
        if total > 0 and 0 <= current <= total:
            return current, total
    return None


def is_checkpoint_setup_error(text: str) -> bool:
    lowered = text.lower()
    return "model checkpoints are missing" in lowered or "checkpoint validation failed" in lowered


def select_checkpoint_folder_text(
    folder: Path,
    mode: str = "twosplit",
    trusted: bool = False,
) -> str:
    validation, manifest_path = select_manual_checkpoint_folder(folder, mode=mode, trusted=trusted)
    return json.dumps(
        {
            "ok": validation.ok,
            "mode": validation.mode,
            "folder": str(Path(folder).resolve()),
            "manifest": str(manifest_path),
            "files": [str(file.path) for file in validation.files],
        },
        indent=2,
    )


def prepare_restore_dry_run(
    input_audio: Path,
    output_audio: Path | None = None,
    steps: int = 50,
    model_mode: str = "twosplit",
    task_mode: str = "bandwidth",
    cutoff_hz: int = 4000,
    inpaint_start_seconds: float | None = None,
    inpaint_end_seconds: float | None = None,
    checkpoint_folder: Path | None = None,
    trust_manual_checkpoints: bool = False,
) -> DryRunRestorePlan:
    return prepare_restore(
        input_audio=input_audio,
        output_audio=output_audio,
        steps=steps,
        model_mode=model_mode,
        task_mode=task_mode,
        cutoff_hz=cutoff_hz,
        inpaint_start_seconds=inpaint_start_seconds,
        inpaint_end_seconds=inpaint_end_seconds,
        checkpoint_folder=checkpoint_folder,
        trust_manual_checkpoints=trust_manual_checkpoints,
        dry_run=True,
    )


def execute_restore_text(
    input_audio: Path,
    output_audio: Path | None = None,
    steps: int = 50,
    model_mode: str = "twosplit",
    task_mode: str = "bandwidth",
    cutoff_hz: int = 4000,
    inpaint_start_seconds: float | None = None,
    inpaint_end_seconds: float | None = None,
    checkpoint_folder: Path | None = None,
    trust_manual_checkpoints: bool = False,
    on_line: LineCallback | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> str:
    execution = execute_restore(
        input_audio=input_audio,
        output_audio=output_audio,
        steps=steps,
        model_mode=model_mode,
        task_mode=task_mode,
        cutoff_hz=cutoff_hz,
        inpaint_start_seconds=inpaint_start_seconds,
        inpaint_end_seconds=inpaint_end_seconds,
        checkpoint_folder=checkpoint_folder,
        trust_manual_checkpoints=trust_manual_checkpoints,
        on_line=on_line,
        should_cancel=should_cancel,
    )
    return json.dumps(
        {
            "ok": execution.returncode == 0,
            "returncode": execution.returncode,
            "cancelled": execution.cancelled,
            "job": execution.plan.job_id,
            "output": execution.plan.output_audio,
            "log": execution.plan.log_path,
            "stdout": execution.stdout,
            "stderr": execution.stderr,
        },
        indent=2,
    )


def restore_plan_text(plan: DryRunRestorePlan) -> str:
    return json.dumps(plan.__dict__, indent=2)
