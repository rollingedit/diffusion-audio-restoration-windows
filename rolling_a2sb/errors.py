from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserFacingError:
    code: str
    title: str
    message: str
    suggested_fix: str


class A2SBError(Exception):
    code = "a2sb_error"
    title = "A2SB Restorer failed"
    suggested_fix = "Open the logs and run Doctor for more detail."

    def to_user_error(self) -> UserFacingError:
        return UserFacingError(
            code=self.code,
            title=self.title,
            message=str(self),
            suggested_fix=self.suggested_fix,
        )


class MissingDependencyError(A2SBError):
    code = "missing_dependency"
    title = "A required dependency is missing"
    suggested_fix = "Run Repair Runtime, then run Doctor again."


class MissingCudaError(A2SBError):
    code = "missing_cuda"
    title = "NVIDIA CUDA is not available"
    suggested_fix = "Install or update the NVIDIA driver, then run Doctor again."


class InsufficientVramError(A2SBError):
    code = "insufficient_vram"
    title = "GPU memory is not sufficient for this restore"
    suggested_fix = "Try a shorter audio file, close other GPU apps, or reduce restore steps."


class MissingFfmpegError(A2SBError):
    code = "missing_ffmpeg"
    title = "FFmpeg is missing"
    suggested_fix = "Run Repair Runtime or use a packaged build that includes ffmpeg.exe and ffprobe.exe."


class MissingCheckpointError(A2SBError):
    code = "missing_checkpoint"
    title = "Model checkpoints are missing"
    suggested_fix = "Download Official Model or select a trusted checkpoint folder."


class CheckpointTrustError(A2SBError):
    code = "checkpoint_trust_required"
    title = "Checkpoint trust confirmation required"
    suggested_fix = "Use the official NVIDIA Hugging Face download or confirm the manual checkpoint source is trusted."


class AudioProbeError(A2SBError):
    code = "audio_probe_failed"
    title = "Audio file could not be read"
    suggested_fix = "Choose a WAV, MP3, or FLAC file that can be opened by FFmpeg."


class RestoreProcessError(A2SBError):
    code = "restore_process_failed"
    title = "Restoration process failed"
    suggested_fix = "Check the log. If CUDA ran out of memory, try a shorter audio file or fewer steps."


def classify_exception(exc: BaseException) -> UserFacingError:
    if isinstance(exc, A2SBError) and not isinstance(exc, RestoreProcessError):
        return exc.to_user_error()

    message = str(exc)
    lowered = message.lower()
    if "out of memory" in lowered or "cuda oom" in lowered or "cublas_status_alloc_failed" in lowered:
        return InsufficientVramError(_safe_message(message)).to_user_error()
    if "ffmpeg" in lowered or "ffprobe" in lowered:
        if "not found" in lowered or "no such file" in lowered or "cannot find" in lowered or "missing" in lowered:
            return MissingFfmpegError(_safe_message(message)).to_user_error()
    if "no module named" in lowered:
        return MissingDependencyError(message).to_user_error()
    if "cuda" in lowered and ("not available" in lowered or "out of memory" not in lowered):
        return MissingCudaError(message).to_user_error()
    if "checkpoint" in lowered or ".ckpt" in lowered:
        return MissingCheckpointError(message).to_user_error()
    return UserFacingError(
        code="unexpected_error",
        title="Unexpected error",
        message=_safe_message(message),
        suggested_fix="Open the logs and copy the diagnostic report.",
    )


def format_user_error(exc: BaseException) -> str:
    user_error = classify_exception(exc)
    return "\n".join(
        [
            user_error.title,
            user_error.message,
            f"Suggested fix: {user_error.suggested_fix}",
        ]
    )


def _safe_message(message: str) -> str:
    if "traceback (most recent call last)" not in message.lower():
        return message
    for line in reversed(message.splitlines()):
        stripped = line.strip()
        if stripped and not stripped.startswith("File ") and not stripped.startswith("^"):
            return stripped
    return "Detailed error information was written to the log."
