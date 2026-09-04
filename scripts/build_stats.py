#!/usr/bin/env python3
"""Aggregate one snapshot into the JSON the map reads.

See CLAUDE.md section 4.1: the frontend's data contract is defined first, and
the analysis scripts are written to satisfy it. This produces the county-level
figures behind the first map.

    python scripts/build_stats.py            # newest snapshot
    python scripts/build_stats.py --date 2026-09-03

Output: public/data/stats/counties.json

County comes from the shelter, never from animal_foundplace. That is a
deliberate limitation, not an oversight: only 2.4% of rows state their own
county, and 12 of the 197 that do disagree with the shelter holding them
(CLAUDE.md 1.5). So this map answers "where are the animals now", not "where
were they found", and the UI has to say so.

Every duration figure is time in the shelter for animals STILL in it. Never
present it as difficulty of adoption - CLAUDE.md 1.3, length-biased sampling.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clean import load_clean  # noqa: E402
from geocode import annotate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "public" / "data" / "stats" / "counties.json"

# Cut points in days. Chosen to be readable rather than even: the first three
# cover the range where most cats leave, the last two the long tail that the
# stock snapshot over-samples.
BUCKETS = [
    ("30 天內", 0, 30),
    ("31–90 天", 31, 90),
    ("91–180 天", 91, 180),
    ("181–365 天", 181, 365),
    ("1–2 年", 366, 730),
    ("2–4 年", 731, 1460),
    ("4 年以上", 1461, None),
]

KINDS = ("狗", "貓", "其他")


def median(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def bucket_index(days: int) -> int:
    for index, (_, low, high) in enumerate(BUCKETS):
        if days >= low and (high is None or days <= high):
            return index
    return len(BUCKETS) - 1


def summarise(rows: list[dict]) -> dict:
    """Median first, mean and extremes alongside it.

    The median is the figure to read. The mean is dragged upward by a
    right-skewed tail — a stock snapshot over-samples long stays by
    construction — and the maximum is one animal, not a trend. They are here
    because a reader asks for them, and the page labels them as secondary.
    """
    durations = [row["days_in_shelter"] for row in rows if row["days_in_shelter"] is not None]
    histogram = [0] * len(BUCKETS)
    for days in durations:
        histogram[bucket_index(days)] += 1
    return {
        "count": len(rows),
        "median_days": median(durations),
        "mean_days": round(sum(durations) / len(durations)) if durations else None,
        "min_days": min(durations) if durations else None,
        "max_days": max(durations) if durations else None,
        "histogram": histogram,
    }


def build(snapshot_date: str | None) -> dict:
    rows, clean_report = load_clean(snapshot_date)
    graded, _ = annotate(snapshot_date)
    # annotate() re-reads the same snapshot, so the two lists line up by index.
    for row, extra in zip(rows, graded):
        row["foundplace_district"] = extra["foundplace_district"]
        row["district_verified"] = extra["district_verified"]

    areas = json.loads((ROOT / "public" / "data" / "areas.json").read_text(encoding="utf-8"))

    counties = []
    for pkid, area in areas.items():
        subset = [row for row in rows if row["animal_area_pkid"] == pkid]
        verified = sum(1 for row in subset if row["district_verified"] is True)
        entry = {
            "pkid": pkid,
            "name": area["name"],
            "shelters": area["shelters"],
            # Stated so the UI can warn before anyone reads the district layer
            # as a map of where animals were found. CLAUDE.md 3, stage 1.
            "district_coverage": round(verified / len(subset), 4) if subset else 0.0,
            "all": summarise(subset),
        }
        for kind in KINDS:
            entry[kind] = summarise([row for row in subset if row["animal_kind"] == kind])
        counties.append(entry)

    counties.sort(key=lambda item: -item["all"]["count"])

    return {
        "snapshot_date": clean_report["snapshot_date"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "county_source": "shelter",
        "buckets": [
            {"label": label, "min": low, "max": high} for label, low, high in BUCKETS
        ],
        "kinds": list(KINDS),
        "total": summarise(rows),
        "counties": counties,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Snapshot to aggregate (YYYY-MM-DD). Default: newest.")
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing.")
    args = parser.parse_args()

    payload = build(args.date)
    print(f"snapshot {payload['snapshot_date']}: {payload['total']['count']} rows")
    print(f"{'縣市':<8}{'在所':>7}{'中位數':>8}{'狗':>7}{'貓':>7}{'區級覆蓋':>10}")
    for county in payload["counties"]:
        print(
            f"{county['name']:<8}{county['all']['count']:>7}"
            f"{county['all']['median_days'] or 0:>8}"
            f"{county['狗']['count']:>7}{county['貓']['count']:>7}"
            f"{county['district_coverage'] * 100:>9.1f}%"
        )

    if args.dry_run:
        print("dry run, nothing written")
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {OUT_PATH.relative_to(ROOT)} ({OUT_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
