#!/usr/bin/env python3
"""Fail when the source has not produced a new snapshot for several days.

    python scripts/check_freshness.py               # threshold 3 days
    python scripts/check_freshness.py --days 5

Run by .github/workflows/daily-snapshot.yml after the manifest row for the
day is committed. A failed fetch already fails its own run; an unchanged one
does not, because a source that skips a day is normal. Several in a row is
not: either the agency stopped updating the feed or it is serving a cached
file, and the site keeps showing an old list with nothing to flag it. Failing
the run here is what turns that into a GitHub notification.

The check reads only data/raw/_manifest.csv: the trailing run of rows whose
status is not "stored", counted from the newest row back. "failed" rows count
too, so a mix of failures and unchanged days is still caught.

Standard library only, like the rest of the daily job.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import RAW_DIR, log, relative  # noqa: E402

MANIFEST_PATH = RAW_DIR / "_manifest.csv"
DEFAULT_DAYS = 3


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return sorted(csv.DictReader(handle), key=lambda row: row["date"])


def stale_streak(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """The newest rows that did not store a snapshot, oldest first."""
    streak: list[dict[str, str]] = []
    for row in reversed(rows):
        if row["status"] == "stored":
            break
        streak.append(row)
    return list(reversed(streak))


def last_stored(rows: list[dict[str, str]]) -> str | None:
    for row in reversed(rows):
        if row["status"] == "stored":
            return row["date"]
    return None


def write_summary(lines: list[str]) -> None:
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if not target:
        return
    with open(target, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"Fail once this many newest rows stored nothing (default {DEFAULT_DAYS}).",
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        log(f"::error::{relative(MANIFEST_PATH)} is missing")
        return 1

    rows = read_rows(MANIFEST_PATH)
    streak = stale_streak(rows)
    if len(streak) < args.days:
        log(f"freshness ok: {len(streak)} day(s) without a new snapshot (limit {args.days})")
        return 0

    since = last_stored(rows) or "the start of the archive"
    statuses = ", ".join(f"{row['date']} {row['status']}" for row in streak)
    log(f"::error::no new snapshot for {len(streak)} days (last stored {since}): {statuses}")
    write_summary(
        [
            "### Source freshness",
            "",
            f"No new snapshot for **{len(streak)} days**; the last one stored is {since}.",
            "The site still shows that day's list. Check whether the source at",
            "https://data.gov.tw/dataset/85903 is still being updated.",
            "",
            "| date | status |",
            "|---|---|",
            *(f"| {row['date']} | {row['status']} |" for row in streak),
        ]
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
