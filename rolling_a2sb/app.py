from __future__ import annotations

import argparse
import sys

from .runtime_check import diagnostic_text, doctor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m rolling_a2sb.app")
    parser.add_argument("--doctor-json", action="store_true", help="Print doctor JSON through the CLI fallback.")
    parser.add_argument("--no-gui", action="store_true", help="Print a diagnostic report instead of opening the GUI.")
    args = parser.parse_args(argv)

    if args.no_gui:
        print(diagnostic_text())
        return 0

    if args.doctor_json:
        from .runtime_check import doctor_json

        print(doctor_json())
        return 0

    try:
        from .gui import run_gui
    except Exception as exc:
        print("A2SB Restorer GUI could not start.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        print(diagnostic_text(doctor()), file=sys.stderr)
        return 1

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())

