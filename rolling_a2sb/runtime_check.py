from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import paths
from .checkpoint_manager import validate_checkpoint_folder


def check_python() -> dict[str, Any]:
    version = ".".join(str(part) for part in sys.version_info[:3])
    return {
        "ok": sys.version_info >= (3, 10) and sys.version_info < (3, 12),
        "version": version,
        "executable": sys.executable,
    }


def check_import(module_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return {"ok": False, "module": module_name, "error": str(exc)}
    return {"ok": True, "module": module_name, "version": getattr(module, "__version__", None)}


def check_imports(module_names: list[str] | None = None) -> dict[str, Any]:
    modules = {name: check_import(name) for name in (module_names or ["yaml"])}
    return {"ok": all(check["ok"] for check in modules.values()), "modules": modules}


def check_torch_cuda() -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    cuda_available = bool(torch.cuda.is_available())
    result: dict[str, Any] = {
        "ok": cuda_available,
        "version": getattr(torch, "__version__", None),
        "cuda_version": getattr(torch.version, "cuda", None),
        "cuda_available": cuda_available,
    }
    if cuda_available:
        result["gpu_name"] = torch.cuda.get_device_name(0)
        try:
            props = torch.cuda.get_device_properties(0)
            result["vram_gb"] = round(props.total_memory / (1024**3), 2)
        except Exception as exc:
            result["vram_error"] = str(exc)
    return result


def check_nvidia_smi() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {"ok": False, "available": False, "error": "nvidia-smi not found"}

    completed = subprocess.run(
        [executable, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
    )
    if completed.returncode != 0:
        return {"ok": False, "available": True, "error": completed.stderr.strip()}

    first_line = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
    parts = [part.strip() for part in first_line.split(",")]
    return {
        "ok": bool(first_line),
        "available": True,
        "raw": first_line,
        "name": parts[0] if len(parts) > 0 else None,
        "memory_total_mb": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None,
        "driver_version": parts[2] if len(parts) > 2 else None,
    }


def check_ffmpeg() -> dict[str, Any]:
    bundled = paths.ffmpeg_path()
    found = bundled if bundled.exists() else shutil.which("ffmpeg")
    return {
        "ok": bool(found),
        "path": str(found) if found else str(bundled),
        "bundled_expected": str(bundled),
    }


def check_write_permissions() -> dict[str, Any]:
    try:
        created = paths.ensure_app_dirs()
        probe = paths.temp_dir() / "write-test.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return {"ok": True, "dirs": [str(path) for path in created]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def check_checkpoints(mode: str = "twosplit", folder: Path | None = None, min_size_bytes: int | None = None) -> dict[str, Any]:
    validation = validate_checkpoint_folder(
        folder or paths.models_dir(),
        mode=mode,
        min_size_bytes=min_size_bytes if min_size_bytes is not None else 2_000_000_000,
        compute_hashes=False,
    )
    return {
        "ok": validation.ok,
        "mode": validation.mode,
        "files": [str(file.path) for file in validation.files],
        "missing": validation.missing,
        "errors": validation.errors,
    }


def doctor(mode: str = "twosplit", checkpoint_min_size_bytes: int | None = None) -> dict[str, Any]:
    checks = {
        "python": check_python(),
        "imports": check_imports(),
        "torch": check_torch_cuda(),
        "nvidia_smi": check_nvidia_smi(),
        "ffmpeg": check_ffmpeg(),
        "write_permissions": check_write_permissions(),
        "checkpoints": check_checkpoints(mode=mode, min_size_bytes=checkpoint_min_size_bytes),
    }
    return {"ok": all(check.get("ok", False) for check in checks.values()), **checks}


def doctor_json(**kwargs: Any) -> str:
    return json.dumps(doctor(**kwargs), indent=2)


def diagnostic_text(report: dict[str, Any] | None = None) -> str:
    report = report or doctor()
    lines = ["A2SB Restorer diagnostic report", f"overall: {'ok' if report.get('ok') else 'not ready'}"]
    for name, value in report.items():
        if name == "ok":
            continue
        status = "ok" if isinstance(value, dict) and value.get("ok") else "needs attention"
        lines.append(f"{name}: {status}")
        if isinstance(value, dict):
            if value.get("error"):
                lines.append(f"  error: {value['error']}")
            if value.get("missing"):
                lines.append(f"  missing: {', '.join(value['missing'])}")
    return "\n".join(lines) + "\n"
