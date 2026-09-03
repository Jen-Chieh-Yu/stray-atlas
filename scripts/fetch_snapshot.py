#!/usr/bin/env python3
"""Download the daily "animal adoption" open-data CSV and archive one snapshot.

Driven by .github/workflows/daily-snapshot.yml. See CLAUDE.md section 3, stage 0.

Why this script is written defensively: the source feed is a *stock snapshot*.
Only animals still open for adoption appear in it; an animal that leaves the
shelter is simply dropped. Diffing consecutive snapshots is the only way this
project will ever obtain an adoption outcome label, so a day that is missed is
a day lost permanently. Every failure path here is therefore loud: the script
exits non-zero and records the failure in the manifest rather than quietly
storing nothing.

Archive policy: the downloaded bytes are stored verbatim, BOM and CRLF line
endings included. data/raw/ is meant to be a faithful copy of what the source
served that day; normalising it here would make the archive un-auditable and
would silently rewrite history if the source ever changes its encoding.
Consumers must therefore read it with encoding="utf-8-sig".
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# CLAUDE.md 2.1: never hard-code the repository root directory name. The CI
# checkout directory is "stray-atlas", the local one is "StrayAtlas".
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "_manifest.csv"

# Resource link published on https://data.gov.tw/dataset/85903 (agency: 農業部).
# Override with the SNAPSHOT_URL environment variable if the agency moves it.
DEFAULT_URL = (
    "https://data.moa.gov.tw/Service/OpenData/TransService.aspx"
    "?UnitId=QcbUEzN6E6DL&FOTT=CSV&IsTransData=1"
)
USER_AGENT = "StrayAtlas-snapshot/1.0 (+https://github.com/Jen-Chieh-Yu/stray-atlas)"

ATTEMPTS = 4
BACKOFF_SECONDS = (5, 15, 45)
TIMEOUT_SECONDS = 180

# A truncated or error-page response must never overwrite a good archive.
MIN_ROWS = 1000
ROW_DRIFT_WARN = 0.5
REQUIRED_COLUMNS = (
    "animal_id",
    "animal_area_pkid",
    "animal_shelter_pkid",
    "animal_kind",
    "animal_createtime",
    "shelter_address",
)

MANIFEST_HEADER = ["date", "status", "rows", "bytes", "sha256", "fetched_at_utc"]


def log(message: str) -> None:
    print(message, flush=True)


def taipei_today() -> str:
    """Snapshot date in Asia/Taipei.

    A fixed +08:00 offset rather than zoneinfo: Taiwan has no DST, and this
    avoids depending on tzdata being present in the runner image. The date is
    computed at run time, so a delayed scheduled run still labels the file with
    the Taipei date it actually ran on.
    """
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def download(url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*"}
            )
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                payload = response.read()
            if not payload:
                raise ValueError("empty response body")
            log(f"downloaded {len(payload)} bytes on attempt {attempt}")
            return payload
        except Exception as error:  # noqa: BLE001 - retry on anything transient
            last_error = error
            log(f"attempt {attempt}/{ATTEMPTS} failed: {error!r}")
            if attempt < ATTEMPTS:
                delay = BACKOFF_SECONDS[attempt - 1]
                log(f"retrying in {delay}s")
                time.sleep(delay)
    raise RuntimeError(f"download failed after {ATTEMPTS} attempts: {last_error!r}")


def validate(payload: bytes) -> int:
    """Return the data row count, or raise if the payload is not the expected CSV."""
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(f"response is not UTF-8: {error}") from error

    reader = csv.DictReader(io.StringIO(text, newline=""))
    columns = reader.fieldnames or []
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    if missing:
        head = text[:200].replace("\n", " ")
        raise ValueError(f"missing expected columns {missing}; response starts with: {head!r}")

    rows = sum(1 for _ in reader)
    if rows < MIN_ROWS:
        raise ValueError(f"only {rows} rows, expected at least {MIN_ROWS}")
    log(f"validated {rows} rows across {len(columns)} columns")
    return rows


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_gzip(path: Path, payload: bytes) -> None:
    """Write deterministically: no mtime, no stored filename.

    Otherwise every run produces different bytes for identical content and git
    records a diff for a file that did not actually change.
    """
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=9, mtime=0) as archive:
        archive.write(payload)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(buffer.getvalue())
    temporary.replace(path)


def snapshot_paths() -> list[Path]:
    return sorted(RAW_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].csv.gz"))


def previous_snapshot(date: str) -> Path | None:
    earlier = [path for path in snapshot_paths() if path.name[:10] < date]
    return earlier[-1] if earlier else None


def read_manifest() -> list[list[str]]:
    if not MANIFEST_PATH.exists():
        return []
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    return [row for row in rows[1:] if row]


def write_manifest(rows: list[list[str]]) -> None:
    rows.sort(key=lambda row: row[0])
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(MANIFEST_HEADER)
        writer.writerows(rows)


def record(date: str, status: str, rows: int, size: int, digest: str) -> None:
    """Upsert one manifest row.

    The manifest exists because a stored file is committed only when its
    content differs from the previous day. Without it a gap in data/raw/ would
    be ambiguous: source unchanged, or fetch never happened? Stage 3 builds
    labels from disappearing animal_id values and cannot tolerate that
    ambiguity.
    """
    entries = [row for row in read_manifest() if row[0] != date]
    entries.append([date, status, str(rows), str(size), digest, utc_now()])
    write_manifest(entries)


def backfill_manifest() -> None:
    """Add manifest rows for snapshots archived before the manifest existed."""
    entries = read_manifest()
    known = {row[0] for row in entries}
    added = 0
    for path in snapshot_paths():
        date = path.name[:10]
        if date in known:
            continue
        payload = gzip.decompress(path.read_bytes())
        rows = sum(1 for _ in csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline="")))
        entries.append([date, "stored", str(rows), str(len(payload)), sha256(payload), ""])
        added += 1
    if added:
        log(f"backfilled {added} manifest row(s) from existing archives")
        write_manifest(entries)


def previous_row_count() -> int | None:
    for row in reversed(read_manifest()):
        if row[1] == "stored" and row[2].isdigit():
            return int(row[2])
    return None


def set_output(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("SNAPSHOT_URL") or DEFAULT_URL)
    parser.add_argument("--date", help="Override the snapshot date (YYYY-MM-DD).")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and overwrite even if today's snapshot already exists.",
    )
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    backfill_manifest()

    date = args.date or taipei_today()
    target = RAW_DIR / f"{date}.csv.gz"

    if target.exists() and not args.force:
        log(f"{target.name} already exists, nothing to do")
        set_output(status="skipped", date=date, commit_message="")
        return 0

    log(f"fetching {args.url}")
    try:
        payload = download(args.url)
        rows = validate(payload)
    except Exception as error:  # noqa: BLE001 - record the failure, then fail loudly
        log(f"::error::snapshot {date} failed: {error}")
        record(date, "failed", 0, 0, "")
        set_output(
            status="failed",
            date=date,
            commit_message=f"data: manifest {date} (fetch failed)",
        )
        return 1

    digest = sha256(payload)
    expected = previous_row_count()
    if expected and abs(rows - expected) > expected * ROW_DRIFT_WARN:
        log(f"::warning::row count moved from {expected} to {rows}; verify the source format")

    previous = previous_snapshot(date)
    if previous is not None and not args.force:
        if sha256(gzip.decompress(previous.read_bytes())) == digest:
            log(f"content identical to {previous.name}, not storing a duplicate")
            record(date, "unchanged", rows, len(payload), digest)
            set_output(
                status="unchanged",
                date=date,
                commit_message=f"data: manifest {date} (source unchanged since {previous.name[:10]})",
            )
            return 0

    write_gzip(target, payload)
    record(date, "stored", rows, len(payload), digest)
    log(f"stored {target.relative_to(ROOT)} ({target.stat().st_size} bytes gzipped)")
    set_output(status="stored", date=date, commit_message=f"data: snapshot {date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
