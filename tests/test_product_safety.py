from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_product_python_path_does_not_use_shell_true() -> None:
    product_files = list((ROOT / "rolling_a2sb").glob("*.py")) + [
        ROOT / "launcher" / "launcher.py",
    ]

    offenders = [
        str(path.relative_to(ROOT))
        for path in product_files
        if "shell=True" in path.read_text(encoding="utf-8").replace(" ", "")
    ]

    assert offenders == []
