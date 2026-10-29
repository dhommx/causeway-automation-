"""Where files live: readable folders under the data folder, kept for audit.

    <data folder>/
      _uploads/2026-10-27/zoho.xlsx         uploads waiting for a run (deleted after a few days)
      2026-10-27/Causeway Sales Reconciliation - 09-41-12/
        input/     the run's files as uploaded, and entries.json (what the user typed)
        output/    what the run produced
        run.json   who, when, rules, status and file fingerprints

Files are written once and never overwritten: a name already taken gets " (2)", " (3)"...
The database keeps each file's full path and SHA-256, so changing the data folder later
doesn't lose older runs, and a file edited on disk can be detected.
"""

import hashlib
import json
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.config import get_settings

UPLOADS = "_uploads"


def local_now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().timezone))


def safe_name(name: str) -> str:
    """A file or folder name that works on Windows and Linux."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name or "file"


def _numbered(path: Path, n: int) -> Path:
    return path if n == 1 else path.with_name(f"{path.stem} ({n}){path.suffix}")


def write_new(folder: Path, name: str, data: bytes) -> tuple[Path, str]:
    """Write bytes as a new file in folder and return its path and SHA-256."""
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / safe_name(name)
    n = 1
    while True:
        path = _numbered(base, n)
        try:
            with open(path, "xb") as f:
                f.write(data)
            return path, hashlib.sha256(data).hexdigest()
        except FileExistsError:
            n += 1


def read(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def new_run_folder(root: Path, automation: str, at: datetime) -> Path:
    """<root>/<date>/<automation> - <HH-MM-SS>, with input/ and output/ inside."""
    base = root / at.strftime("%Y-%m-%d") / safe_name(f"{automation} - {at:%H-%M-%S}")
    base.parent.mkdir(parents=True, exist_ok=True)
    n = 1
    while True:
        folder = Path(f"{base} ({n})") if n > 1 else base
        try:
            folder.mkdir()
            break
        except FileExistsError:
            n += 1
    (folder / "input").mkdir()
    (folder / "output").mkdir()
    return folder


def write_json(path: Path, value: Any) -> None:
    """Write a summary file (run.json, entries.json). These are the only files rewritten."""
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def check_writable(folder: Path) -> None:
    """Create the folder if needed and prove a file can be written there. Raises OSError."""
    folder.mkdir(parents=True, exist_ok=True)
    probe = folder / ".write-test"
    probe.write_bytes(b"ok")
    probe.unlink()


def clear_old_uploads(root: Path, keep_days: int, today: date) -> list[str]:
    """Delete upload day-folders older than keep_days. Returns the folders removed."""
    uploads = root / UPLOADS
    if not uploads.is_dir():
        return []
    cutoff = today - timedelta(days=keep_days)
    removed = []
    for day in sorted(uploads.iterdir()):
        try:
            day_date = date.fromisoformat(day.name)
        except ValueError:
            continue
        if day.is_dir() and day_date < cutoff:
            shutil.rmtree(day)
            removed.append(str(day))
    return removed
