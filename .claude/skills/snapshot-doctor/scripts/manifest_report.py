#!/usr/bin/env python3
"""Summarize the daily snapshot manifest: freshness, failure streak, gaps.

    git show origin/main:data/raw/_manifest.csv |
        python .claude/skills/snapshot-doctor/scripts/manifest_report.py -

Read-only. Reads the manifest from a file or stdin ("-"), so it can look at
origin/main without touching the working tree.

The one thing it infers is who wrote a failed row. The watchdog cron in
daily-snapshot.yml records a day nobody fetched: no run reached the source
that day at all. Until MORNING_FROM it ran the next morning, so its rows carry
a later date; since then it runs the same afternoon, after the 09:00-12:59
fetch window. Any other failed row came from a run that reached the fetch and
failed there. A manual run that fails after 13:00 reads as the watchdog too.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

TAIPEI = timezone(timedelta(hours=8))
GAP_WINDOW_DAYS = 30
# Snapshots moved to a 09:00-12:59 window on this day, and the watchdog to the
# same afternoon.
MORNING_FROM = date(2026, 11, 3)
WINDOW_END_HOUR = 13


@dataclass(frozen=True)
class Row:
    day: date
    status: str
    rows: int
    fetched: datetime | None  # Taipei time

    @property
    def recorded_by(self) -> str:
        if self.status != "failed":
            return "fetch"
        if self.fetched is None:
            return "unknown"
        if self.fetched.date() > self.day or (
            self.day >= MORNING_FROM and self.fetched.hour >= WINDOW_END_HOUR
        ):
            return "watchdog: no run reached the fetch that day"
        return "run: the fetch was attempted and failed"


def parse(text: str) -> list[Row]:
    rows = []
    for entry in csv.DictReader(io.StringIO(text)):
        stamp = entry.get("fetched_at_utc") or ""
        fetched = (
            datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=timezone.utc)
            .astimezone(TAIPEI)
            if stamp
            else None
        )
        rows.append(
            Row(
                day=date.fromisoformat(entry["date"]),
                status=entry["status"],
                rows=int(entry["rows"] or 0),
                fetched=fetched,
            )
        )
    return sorted(rows, key=lambda row: row.day)


def streak(rows: list[Row]) -> list[Row]:
    """The trailing run of rows that did not store a new snapshot."""
    tail: list[Row] = []
    for row in reversed(rows):
        if row.status == "stored":
            break
        tail.append(row)
    return list(reversed(tail))


def missing(rows: list[Row], today: date) -> list[date]:
    """Days before today with no row, within the recent window."""
    if not rows:
        return []
    known = {row.day for row in rows}
    start = max(rows[0].day, today - timedelta(days=GAP_WINDOW_DAYS))
    days = (start + timedelta(days=n) for n in range((today - start).days))
    return [day for day in days if day not in known]


def report(rows: list[Row], now: datetime, recent: int = 10) -> str:
    today = now.date()
    lines = [f"now (Taipei): {now:%Y-%m-%d %H:%M}"]
    if not rows:
        return "\n".join([*lines, "manifest is empty"])

    stored = [row for row in rows if row.status == "stored"]
    if stored:
        last = stored[-1]
        age = (today - last.day).days
        lines.append(f"last stored: {last.day} ({age} day(s) ago, {last.rows} rows)")
    else:
        lines.append("last stored: none")

    tail = streak(rows)
    if tail:
        counts = {s: sum(1 for row in tail if row.status == s) for s in ("failed", "unchanged")}
        lines.append(
            f"not stored since: {tail[0].day} ({len(tail)} row(s): "
            f"{counts['failed']} failed, {counts['unchanged']} unchanged)"
        )
        if counts["unchanged"] >= 3 and counts["failed"] == 0:
            lines.append("  3+ unchanged in a row: the source may have stopped updating")

    gaps = missing(rows, today)
    if gaps:
        lines.append("days with no row: " + ", ".join(str(day) for day in gaps))
    if rows[-1].day != today:
        if now.hour < 9:
            when = "expected after 09:00"
        elif now.hour < WINDOW_END_HOUR:
            when = "expected before 13:00"
        elif now.hour < 17:
            when = "the window has closed; the watchdog should record it by about 16:00"
        else:
            when = "should exist by now"
        lines.append(f"today ({today}) has no row yet: {when}")

    lines.append("")
    lines.append(f"last {min(recent, len(rows))} rows:")
    for row in rows[-recent:]:
        fetched = f"{row.fetched:%m-%d %H:%M}" if row.fetched else "-"
        lines.append(f"  {row.day}  {row.status:<9}  {row.rows:>5}  {fetched}  {row.recorded_by}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest", help="path to _manifest.csv, or - for stdin")
    parser.add_argument("--recent", type=int, default=10, help="rows to list (default 10)")
    parser.add_argument("--now", help="Taipei time as YYYY-MM-DDTHH:MM, for testing")
    args = parser.parse_args(argv)

    if args.manifest == "-":
        text = sys.stdin.read()
    else:
        with open(args.manifest, encoding="utf-8", newline="") as handle:
            text = handle.read()
    now = (
        datetime.fromisoformat(args.now).replace(tzinfo=TAIPEI)
        if args.now
        else datetime.now(TAIPEI)
    )
    print(report(parse(text), now, args.recent))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
