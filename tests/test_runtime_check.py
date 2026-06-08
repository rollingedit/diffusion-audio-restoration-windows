import sys

from rolling_a2sb.runtime_check import add_next_actions, check_imports, check_python, diagnostic_text


def test_check_python_reports_supported_dev_python() -> None:
    result = check_python()

    assert result["version"].count(".") == 2
    assert result["executable"] == sys.executable


def test_check_imports_has_group_ok() -> None:
    result = check_imports(["json"])

    assert result["ok"] is True
    assert result["modules"]["json"]["ok"] is True


def test_check_imports_reports_missing_module() -> None:
    result = check_imports(["definitely_missing_a2sb_module"])

    assert result["ok"] is False
    assert result["modules"]["definitely_missing_a2sb_module"]["ok"] is False


def test_diagnostic_text_includes_missing_checkpoints() -> None:
    report = {
        "ok": False,
        "python": {"ok": True},
        "checkpoints": {"ok": False, "missing": ["a.ckpt", "b.ckpt"]},
    }

    text = diagnostic_text(report)

    assert "overall: not ready" in text
    assert "checkpoints: needs attention" in text
    assert "missing: a.ckpt, b.ckpt" in text


def test_next_actions_added_to_failed_checks() -> None:
    checks = add_next_actions({"torch": {"ok": False, "error": "missing"}})

    assert "Repair Runtime" in checks["torch"]["next_action"]


def test_diagnostic_text_includes_next_action() -> None:
    report = {
        "ok": False,
        "torch": {
            "ok": False,
            "error": "No module named 'torch'",
            "next_action": "Run Repair Runtime.",
        },
    }

    text = diagnostic_text(report)

    assert "next: Run Repair Runtime." in text
