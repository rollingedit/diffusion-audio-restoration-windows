from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def append_log(path: Path, message: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message.rstrip()}\n")


def append_block(path: Path, title: str, content: str) -> None:
    append_log(path, title)
    if content:
        with Path(path).open("a", encoding="utf-8") as handle:
            handle.write(content.rstrip() + "\n")

