"""Small helpers shared by every script under scripts/.

Only what was written out identically in several scripts lives here: the
repository paths, the log line, the UTC timestamp, the JSON writer and the
list of archived snapshots. Anything with a judgement in it - how a median is
taken, which columns are dropped - stays in the script that owns the
judgement, so it can be read where it is used.

Every script still runs on its own (`python scripts/<name>.py`): Python puts
the script's own directory on sys.path, so `from common import ...` needs no
install step. Standard library only, like the daily fetch.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

# CLAUDE.md 2.1: never hard-code the repository root directory name. The CI
# checkout directory is "stray-atlas", the local one is "StrayAtlas".
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
REFERENCE_DIR = ROOT / "data" / "reference"
PUBLIC_DATA = ROOT / "public" / "data"
STATS_DIR = PUBLIC_DATA / "stats"

SNAPSHOT_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.csv\.gz$")


def log(message: str) -> None:
    print(message, flush=True)


def utc_now() -> str:
    """The generated-at stamp every output file carries."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot_paths() -> list[Path]:
    """Archived snapshots, oldest first. The manifest is not one of them."""
    return sorted(path for path in RAW_DIR.glob("*.csv.gz") if SNAPSHOT_NAME.match(path.name))


def latest_snapshot_date() -> str | None:
    paths = snapshot_paths()
    return paths[-1].name[:10] if paths else None


def relative(path: Path) -> str:
    """A path as the log shows it: relative to the repository, with / on
    every platform."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, payload: object, *, indent: int | None = None) -> int:
    """Write UTF-8 JSON with a trailing newline and LF line endings.

    indent=None writes the compact form the large files use; an integer
    pretty-prints. newline="\\n" is not optional: without it Windows writes
    CRLF and every rebuild on a Windows machine rewrites the whole file.
    Returns the size in bytes.
    """
    if indent is None:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=indent)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
    size = path.stat().st_size
    log(f"wrote {relative(path)} ({size:,} bytes)")
    return size
