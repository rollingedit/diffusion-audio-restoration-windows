from rolling_a2sb.errors import MissingCudaError, classify_exception


def test_classify_known_a2sb_error() -> None:
    user_error = classify_exception(MissingCudaError("CUDA is not available"))

    assert user_error.code == "missing_cuda"
    assert "NVIDIA CUDA" in user_error.title
    assert "driver" in user_error.suggested_fix


def test_classify_missing_dependency_message() -> None:
    user_error = classify_exception(ModuleNotFoundError("No module named 'torch'"))

    assert user_error.code == "missing_dependency"
    assert "Repair Runtime" in user_error.suggested_fix

