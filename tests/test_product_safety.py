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


def test_product_path_does_not_add_non_v1_platforms_or_services() -> None:
    product_files = list((ROOT / "rolling_a2sb").glob("*.py")) + [
        ROOT / "launcher" / "launcher.py",
        ROOT / "installer" / "a2sb-restorer.iss",
    ]
    forbidden = ["wsl", "docker", "conda", "saas", "serverless", "multi-gpu", "multigpu", "amd gpu", "intel gpu"]
    offenders: list[str] = []

    for path in product_files:
        text = path.read_text(encoding="utf-8").lower()
        for term in forbidden:
            if term in text:
                offenders.append(f"{path.relative_to(ROOT)}: {term}")

    assert offenders == []


def test_launcher_and_installer_do_not_use_one_file_torch_packaging() -> None:
    launcher_spec = (ROOT / "launcher" / "launcher.spec").read_text(encoding="utf-8").lower()
    installer = (ROOT / "installer" / "a2sb-restorer.iss").read_text(encoding="utf-8").lower()

    assert "--onefile" not in launcher_spec
    assert "onefile" not in launcher_spec
    assert "torch" not in launcher_spec
    assert "*.pt" not in installer
    assert "*.pth" not in installer
    assert "*.safetensors" not in installer
