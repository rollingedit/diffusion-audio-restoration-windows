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


class MissingCheckpointError(A2SBError):
    code = "missing_checkpoint"
    title = "Model checkpoints are missing"
    suggested_fix = "Download the recommended model or select a trusted checkpoint folder."


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
    if isinstance(exc, A2SBError):
        return exc.to_user_error()

    message = str(exc)
    lowered = message.lower()
    if "no module named" in lowered:
        return MissingDependencyError(message).to_user_error()
    if "cuda" in lowered and ("not available" in lowered or "out of memory" not in lowered):
        return MissingCudaError(message).to_user_error()
    if "checkpoint" in lowered or ".ckpt" in lowered:
        return MissingCheckpointError(message).to_user_error()
    return UserFacingError(
        code="unexpected_error",
        title="Unexpected error",
        message=message,
        suggested_fix="Open the logs and copy the diagnostic report.",
    )

