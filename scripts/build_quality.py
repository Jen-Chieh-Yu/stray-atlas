#!/usr/bin/env python3
"""Score how completely each county records its animals, not how well it keeps them.

    python scripts/build_quality.py            # newest snapshot
    python scripts/build_quality.py --date 2026-09-03

Output: public/data/stats/quality.json

PROJECT_BRIEF 4 and 5.7 both land on the same finding: several fields measure
the recording habits of the county that filled them in rather than anything
about the animals. Sterilisation is 97% recorded in 南投 and 13% in 宜蘭; the
found-place field names a real district for 95.1% of 雲林 rows and 1.1% of
彰化 rows. Differences that large cannot be policy. This file turns that
finding into the page's data.

Three rules this script exists to keep:

  1. Every metric is a RECORDING measure. A county scoring badly here has
     gaps in its open data, which is not a claim about its shelters. The page
     says so; so does this docstring, because the two travel together.
  2. Thresholds ship in the payload, never in the component (DESIGN 12.9),
     and they are round numbers fixed by hand rather than quantiles of the
     current snapshot: a grade that moves because other counties moved is not
     a grade anyone can act on.
  3. Counties below MIN_ROWS are not graded at all. 連江 has fewer rows than
     some shelters have kennels, and a percentage over 20 rows swings by five
     points when one row changes. Ungraded is the honest answer, and the page
     shows the figure beside it either way.

Variety spelling is deliberately NOT a metric. 94.7% of the roster is mixed
breed (PROJECT_BRIEF 4.2); a county recording mostly 混種犬 is describing its
animals correctly, not failing to fill a field in. It appears at the bottom of
the payload as a spelling count, which is a different claim.

Standard library only.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clean import load_clean, parse_date  # noqa: E402
from common import STATS_DIR, utc_now, write_json  # noqa: E402
from geocode import annotate  # noqa: E402

OUT_PATH = STATS_DIR / "quality.json"

# Below this many rows a share is noise, and the county is reported ungraded.
# 100 rows puts one row at one percentage point, which is the smallest step
# the page prints.
MIN_ROWS = 100

# (key, label, description, good, fair). A share at or above `good` grades
# good, at or above `fair` grades fair, below it poor.
#
# The cut points are round numbers, chosen once, and each has to survive being
# written down: "9 in 10 rows carry a photo" is a sentence a reader can
# disagree with, while "the 75th percentile of this snapshot" is not.
METRICS: tuple[tuple[str, str, str, float, float], ...] = (
    (
        "photo",
        "照片覆蓋率",
        "有照片的比例。沒有照片的動物在任何認養平臺上都很難被看見，"
        "這是四項裡唯一直接影響動物的登錄缺口。",
        0.90,
        0.75,
    ),
    (
        "place",
        "尋獲地可定位率",
        "尋獲地文字能對應到官方 368 鄉鎮市區清單的比例。"
        "全國僅三成多，且各縣市從 1% 到 95% 不等，是本站不畫熱區圖的理由。",
        0.60,
        0.30,
    ),
    (
        "sterilization",
        "絕育狀態已登錄率",
        "絕育欄位填 T 或 F（已登錄結果）的比例；填 N 為未知或不適用。"
        "南投 97%、宜蘭 13%，差距大到不可能是真實政策差異。",
        0.90,
        0.70,
    ),
    (
        "opendate",
        "開放認養日有效率",
        "開放認養日為有效日期的比例。空白、1900-01-01 哨兵值"
        "與晚於快照日的未來日期都不計入。",
        0.95,
        0.85,
    ),
)


def grade(value: float | None, good: float, fair: float) -> str:
    if value is None:
        return "na"
    if value >= good:
        return "good"
    if value >= fair:
        return "fair"
    return "poor"


def score(rows: list[dict], snapshot_date: str) -> dict[str, float]:
    """The four shares, for any subset of rows."""
    total = len(rows)
    if total == 0:
        return {key: 0.0 for key, *_ in METRICS}

    snapshot_day = parse_date(snapshot_date)
    valid_opendate = 0
    for row in rows:
        opendate = parse_date(row["animal_opendate"])
        # load_clean has already nulled the 1900-01-01 sentinel, so an empty
        # string here is either a genuine blank or that sentinel. A date after
        # the snapshot is recorded as invalid for this metric but not
        # corrected anywhere: it may be a real scheduled release.
        if opendate is not None and opendate <= snapshot_day:
            valid_opendate += 1

    return {
        "photo": round(sum(1 for row in rows if row["album_file"]) / total, 4),
        "place": round(sum(1 for row in rows if row["district_verified"] is True) / total, 4),
        "sterilization": round(
            sum(1 for row in rows if row["animal_sterilization"] in ("T", "F")) / total, 4
        ),
        "opendate": round(valid_opendate / total, 4),
    }


def graded(scores: dict[str, float], rows: int) -> dict[str, str]:
    if rows < MIN_ROWS:
        return {key: "na" for key, *_ in METRICS}
    return {key: grade(scores[key], good, fair) for key, _, _, good, fair in METRICS}


def build(snapshot_date: str | None) -> dict:
    rows, report = load_clean(snapshot_date)
    annotated, _ = annotate(snapshot_date)
    # annotate() re-reads the same snapshot, so the two lists line up by index
    # — the same pairing build_stats.py relies on.
    for row, extra in zip(rows, annotated):
        row["district_verified"] = extra["district_verified"]

    snapshot = report["snapshot_date"]
    areas = report["_areas"]

    counties = []
    for pkid, area in areas.items():
        subset = [row for row in rows if row["animal_area_pkid"] == pkid]
        scores = score(subset, snapshot)
        counties.append(
            {
                "pkid": pkid,
                "name": area["name"],
                "shelters": area["shelters"],
                "rows": len(subset),
                "scores": scores,
                "grades": graded(scores, len(subset)),
            }
        )
    counties.sort(key=lambda item: -item["rows"])

    shelters = []
    for name in sorted({row["shelter_name"] for row in rows}):
        subset = [row for row in rows if row["shelter_name"] == name]
        scores = score(subset, snapshot)
        shelters.append(
            {
                # build_shelters.py keys shelters on the name, never on
                # animal_shelter_pkid, because four codes cover two shelters
                # each. The same hash is used here so the page can link
                # straight to /shelters/<id>.
                "id": shelter_identifier(name),
                "name": name,
                "county": subset[0]["area_name"],
                "rows": len(subset),
                "scores": scores,
                "grades": graded(scores, len(subset)),
            }
        )
    shelters.sort(key=lambda item: -item["rows"])

    sterilization = []
    for pkid, area in areas.items():
        subset = [row for row in rows if row["animal_area_pkid"] == pkid]
        counts = Counter(row["animal_sterilization"] for row in subset)
        total = len(subset) or 1
        sterilization.append(
            {
                "pkid": pkid,
                "name": area["name"],
                "rows": len(subset),
                "T": round(counts.get("T", 0) / total, 4),
                "F": round(counts.get("F", 0) / total, 4),
                "N": round(counts.get("N", 0) / total, 4),
            }
        )
    sterilization.sort(key=lambda item: -item["N"])

    return {
        "snapshot_date": snapshot,
        "generated_at_utc": utc_now(),
        "rows": len(rows),
        "min_rows_for_grade": MIN_ROWS,
        "metrics": [
            {
                "key": key,
                "label": label,
                "description": description,
                "thresholds": {"good": good, "fair": fair},
                "national": score(rows, snapshot)[key],
            }
            for key, label, description, good, fair in METRICS
        ],
        "counties": counties,
        "shelters": shelters,
        "spellings": {
            # One thing written several ways. Not a metric — see the module
            # docstring — but the clearest evidence on the page that these
            # rows were typed by people at 37 separate desks.
            "variety": [
                {"value": value, "count": count}
                for value, count in Counter(
                    row["animal_Variety"] for row in rows if row["variety_group"] == "mixed"
                ).most_common()
            ],
            "sterilization_by_county": sterilization,
        },
    }


def shelter_identifier(name: str) -> str:
    import hashlib

    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Snapshot to score (YYYY-MM-DD). Default: newest.")
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing.")
    args = parser.parse_args()

    payload = build(args.date)
    keys = [metric["key"] for metric in payload["metrics"]]
    print(f"snapshot {payload['snapshot_date']}: {payload['rows']} rows")
    print("national  " + "  ".join(f"{m['key']}={m['national']:.3f}" for m in payload["metrics"]))
    header = f"{'縣市':<8}{'隻數':>6}" + "".join(f"{key:>16}" for key in keys)
    print(header)
    for county in payload["counties"]:
        cells = "".join(
            f"{county['scores'][key] * 100:>10.1f}% {county['grades'][key]:<4}" for key in keys
        )
        print(f"{county['name']:<8}{county['rows']:>6}{cells}")

    if args.dry_run:
        print("dry run, nothing written")
        return 0

    write_json(OUT_PATH, payload, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
