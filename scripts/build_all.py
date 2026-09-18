#!/usr/bin/env python3
"""Rebuild every file under public/data/ from one archived snapshot.

    python scripts/build_all.py                    # the newest snapshot
    python scripts/build_all.py --date 2026-09-03  # a named one
    python scripts/build_all.py --list             # show the steps, run nothing

The build scripts each pick a snapshot on their own, and a file built without
--date takes whichever snapshot is newest at that moment. Run by hand, one at a
time, that is how the analysis page ended up drawing a different day from the
rest of the site. This script fixes the date once, passes it to every step,
and then refuses to finish if any output names a different snapshot.

Steps run as separate processes, in dependency order, and the first failure
stops the build: a half-built public/data/ with mixed dates is exactly what
this exists to prevent.

Not included, on purpose:
  fetch_snapshot.py   the daily archive job; it runs on its own schedule
  build_districts.py  a one-off conversion of the boundary shapefile, which
                      needs pyshp and the downloaded source archive

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PUBLIC_DATA, RAW_DIR, STATS_DIR, latest_snapshot_date, log, relative  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent

# (script, takes --date). build_shelter_points.py reads shelters.json instead,
# so it follows whatever the step before it wrote.
STEPS: tuple[tuple[str, bool], ...] = (
    ("clean.py", True),  # areas.json, meta.json
    ("geocode.py", True),  # stats/foundplace.json
    ("build_stats.py", True),  # stats/counties.json
    ("build_shelters.py", True),  # shelters.json, animals.json
    ("build_shelter_points.py", False),  # shelter-points.json
    ("build_distribution.py", True),  # stats/distribution.json
    ("build_features.py", True),  # stats/features.json
    ("build_quality.py", True),  # stats/quality.json
)

# Every output that records its snapshot. areas.json and animals.json carry no
# date of their own; they are written by the same processes as meta.json and
# shelters.json.
DATED_OUTPUTS = (
    PUBLIC_DATA / "meta.json",
    STATS_DIR / "foundplace.json",
    STATS_DIR / "counties.json",
    PUBLIC_DATA / "shelters.json",
    PUBLIC_DATA / "shelter-points.json",
    STATS_DIR / "distribution.json",
    STATS_DIR / "features.json",
    STATS_DIR / "quality.json",
)


def run(script: str, args: list[str]) -> None:
    command = [sys.executable, str(SCRIPTS / script), *args]
    log(f"\n== {script} {' '.join(args)}".rstrip())
    started = time.monotonic()
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(f"{script} failed with exit code {result.returncode}; build stopped")
    log(f"   ({time.monotonic() - started:.1f} s)")


def check_dates(expected: str) -> list[str]:
    problems = []
    for path in DATED_OUTPUTS:
        if not path.exists():
            problems.append(f"{relative(path)} is missing")
            continue
        found = json.loads(path.read_text(encoding="utf-8")).get("snapshot_date")
        if found != expected:
            problems.append(f"{relative(path)} says {found!r}, expected {expected!r}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--date", help="Snapshot to build from (YYYY-MM-DD). Default: the newest.")
    parser.add_argument("--list", action="store_true", help="Print the steps and exit.")
    args = parser.parse_args()

    date = args.date or latest_snapshot_date()
    if date is None:
        raise SystemExit(f"no snapshots in {relative(RAW_DIR)}; run scripts/fetch_snapshot.py first")
    if not (RAW_DIR / f"{date}.csv.gz").exists():
        raise SystemExit(f"no snapshot for {date} in {relative(RAW_DIR)}")

    log(f"snapshot {date}")
    if args.list:
        for script, dated in STEPS:
            log(f"  {script}" + (f" --date {date}" if dated else ""))
        return 0

    for script, dated in STEPS:
        run(script, ["--date", date] if dated else [])

    problems = check_dates(date)
    if problems:
        for problem in problems:
            log(f"::error::{problem}")
        return 1
    log(f"\nall {len(DATED_OUTPUTS)} dated outputs are from {date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
