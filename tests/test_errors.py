from rolling_a2sb.errors import MissingCudaError, classify_exception, format_user_error


def test_classify_known_a2sb_error() -> None:
    user_error = classify_exception(MissingCudaError("CUDA is not available"))

    assert user_error.code == "missing_cuda"
    assert "NVIDIA CUDA" in user_error.title
    assert "driver" in user_error.suggested_fix


def test_classify_missing_dependency_message() -> None:
    user_error = classify_exception(ModuleNotFoundError("No module named 'torch'"))

    assert user_error.code == "missing_dependency"
    assert "Repair Runtime" in user_error.suggested_fix


def test_classify_cuda_out_of_memory() -> None:
    user_error = classify_exception(RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB"))

    assert user_error.code == "insufficient_vram"
    assert "shorter audio" in user_error.suggested_fix


def test_classify_missing_ffmpeg() -> None:
    user_error = classify_exception(FileNotFoundError("ffmpeg.exe not found"))

    assert user_error.code == "missing_ffmpeg"
    assert "Repair Runtime" in user_error.suggested_fix


def test_format_user_error_hides_traceback_detail() -> None:
    text = format_user_error(RuntimeError("Traceback (most recent call last):\n  File \"x.py\", line 1\nRuntimeError: bad"))

    assert "Unexpected error" in text
    assert "Suggested fix:" in text
    assert "File \"x.py\"" not in text
