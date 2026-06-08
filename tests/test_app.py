from rolling_a2sb.app import main


def test_app_no_gui_prints_diagnostic(capsys) -> None:
    exit_code = main(["--no-gui"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "A2SB Restorer diagnostic report" in output

