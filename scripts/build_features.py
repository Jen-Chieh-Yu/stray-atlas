#!/usr/bin/env python3
"""Compare how long each group of animals has been in a shelter.

    python scripts/build_features.py            # newest snapshot
    python scripts/build_features.py --date 2026-09-03

Output: public/data/stats/features.json

The analysis page answers "what does the distribution look like" and stops
there. This file adds the next question - which groups sit where in that
distribution - and then the question that makes the first answer worth
anything: does the largest gap survive a control.

Two blocks, and they are not the same kind of claim:

  groups      One row per category, median plus the quartiles around it.
              Descriptive, uncontrolled, and the page says so: breed dogs
              skew small and young, so the breed gap is inflated by whatever
              size and age contribute on their own.

  dark_coat   The same comparison done WITHIN each shelter. PROJECT_BRIEF 5.3
              found the coat effect survives that control; this recomputes it
              per snapshot rather than quoting a figure that goes stale.
              Shelters, not counties: the shelter is the unit that actually
              decides how long an animal waits, and a county with four
              shelters averages four different answers together.

Every figure is a QUANTILE, never a mean. The distribution is right-skewed by
construction (CLAUDE.md 1.3, length-biased sampling) and a mean would mostly
report the tail. Nothing here may be presented as a difficulty of adoption:
these are animals still in a shelter, and no row in this dataset records a
departure.

Standard library only.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_shelters import shelter_id  # noqa: E402
from clean import load_clean  # noqa: E402
from common import STATS_DIR, utc_now, write_json  # noqa: E402

OUT_PATH = STATS_DIR / "features.json"

# The log axis the page draws these on. Here rather than in the component so
# the two blocks cannot drift apart, and so a tick can be changed without a
# rebuild of the frontend (DESIGN.md 12.9).
AXIS = {
    "min_days": 20,
    "max_days": 3000,
    "ticks": [
        {"days": 30, "label": "1 個月"},
        {"days": 90, "label": "3 個月"},
        {"days": 730, "label": "2 年"},
        {"days": 1825, "label": "5 年"},
    ],
}

# A group smaller than this is drawn but flagged: with 36 animals the median
# moves by weeks when one of them leaves.
SMALL_GROUP = 100

# The coat comparison needs both sides of one shelter to be worth comparing.
# 20 is stated rather than derived: a threshold nobody can see is a threshold
# nobody can disagree with.
MIN_COAT_GROUP = 20

BODY_LABELS = (("SMALL", "小型"), ("MEDIUM", "中型"), ("BIG", "大型"))
AGE_LABELS = (("CHILD", "幼體"), ("ADULT", "成體"))
SEX_LABELS = (("M", "公"), ("F", "母"))
STERILIZATION_LABELS = (("T", "已絕育"), ("F", "未絕育"), ("N", "未知／不適用"))


def quantile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(int(round(fraction * (len(ordered) - 1))), len(ordered) - 1)
    return ordered[index]


def summarise(rows: list[dict]) -> dict:
    days = [row["days_in_shelter"] for row in rows if row["days_in_shelter"] is not None]
    return {
        "n": len(rows),
        "p25_days": quantile(days, 0.25),
        "median_days": quantile(days, 0.50),
        "p75_days": quantile(days, 0.75),
        "small_sample": len(rows) < SMALL_GROUP,
    }


def has_dark_coat(colour: str) -> bool:
    """Substring match on the free-text colour.

    Deliberately wide: 黑白色 and 黑黃色 count as dark. Taking 黑色 alone drops
    the sample below what a per-shelter comparison can carry, and the page
    states the rule so a reader can reject it.
    """
    return "黑" in colour


def build(snapshot_date: str | None) -> dict:
    rows, report = load_clean(snapshot_date)
    dogs = [row for row in rows if row["animal_kind"] == "狗"]
    cats = [row for row in rows if row["animal_kind"] == "貓"]

    def by(field: str, value: str, source: list[dict] | None = None) -> list[dict]:
        return [row for row in (source if source is not None else rows) if row[field] == value]

    groups: list[dict] = [
        {
            "key": "kind",
            "title": "物種",
            "items": [("狗", dogs), ("貓", cats), ("其他", by("animal_kind", "其他"))],
        },
        {
            "key": "dog_variety",
            "title": "品種（犬）",
            "items": [
                ("混種犬", by("variety_group", "mixed", dogs)),
                ("品種犬", by("variety_group", "breed", dogs)),
            ],
        },
        {
            "key": "cat_variety",
            "title": "品種（貓）",
            "items": [
                ("混種貓", by("variety_group", "mixed", cats)),
                ("品種貓", by("variety_group", "breed", cats)),
            ],
        },
        {
            "key": "bodytype",
            "title": "體型",
            "items": [(label, by("animal_bodytype", code)) for code, label in BODY_LABELS],
        },
        {
            "key": "age",
            "title": "年齡",
            "items": [(label, by("animal_age", code)) for code, label in AGE_LABELS],
        },
        {
            "key": "sex",
            "title": "性別",
            "items": [(label, by("animal_sex", code)) for code, label in SEX_LABELS],
        },
        {
            # Kept even though the arrow most likely points the other way -
            # a long stay is an opportunity to be neutered, not the result of
            # one. The page says so; dropping the group would leave a reader
            # to compute the same figure elsewhere without the warning.
            "key": "sterilization",
            "title": "絕育",
            "items": [
                (label, by("animal_sterilization", code)) for code, label in STERILIZATION_LABELS
            ],
        },
    ]

    common_colours = [
        colour
        for colour, count in Counter(row["animal_colour"] for row in dogs).most_common()
        if count >= SMALL_GROUP and colour
    ]
    groups.append(
        {
            "key": "dog_colour",
            "title": f"毛色（犬，樣本 ≥ {SMALL_GROUP}）",
            "items": [(colour, by("animal_colour", colour, dogs)) for colour in common_colours],
        }
    )

    payload_groups = []
    for group in groups:
        items = [
            {"label": label, **summarise(members)} for label, members in group["items"] if members
        ]
        # Shortest first: the page reads left to right along the axis, and a
        # table ordered by anything else makes the reader do the sorting.
        items.sort(key=lambda item: item["median_days"])
        payload_groups.append({"key": group["key"], "title": group["title"], "items": items})

    # ── the control ──
    per_shelter: dict[str, list[dict]] = {}
    for row in dogs:
        per_shelter.setdefault(row["shelter_name"], []).append(row)

    shelters = []
    for name, members in per_shelter.items():
        dark = [row for row in members if has_dark_coat(row["animal_colour"])]
        light = [
            row
            for row in members
            if row["animal_colour"] and not has_dark_coat(row["animal_colour"])
        ]
        if len(dark) < MIN_COAT_GROUP or len(light) < MIN_COAT_GROUP:
            continue
        dark_median = quantile([row["days_in_shelter"] for row in dark], 0.50)
        light_median = quantile([row["days_in_shelter"] for row in light], 0.50)
        shelters.append(
            {
                "id": shelter_id(name),
                "name": name,
                "county": members[0]["area_name"],
                "dark_n": len(dark),
                "light_n": len(light),
                "dark_median_days": dark_median,
                "light_median_days": light_median,
                "difference_days": dark_median - light_median,
            }
        )
    shelters.sort(key=lambda item: -item["difference_days"])

    national_dark = [row for row in dogs if has_dark_coat(row["animal_colour"])]
    national_light = [
        row for row in dogs if row["animal_colour"] and not has_dark_coat(row["animal_colour"])
    ]

    return {
        "snapshot_date": report["snapshot_date"],
        "generated_at_utc": utc_now(),
        "axis": AXIS,
        "small_sample_below": SMALL_GROUP,
        "overall": summarise(rows),
        "groups": payload_groups,
        "dark_coat": {
            "rule": "animal_colour 含「黑」",
            "min_group": MIN_COAT_GROUP,
            "shelters_compared": len(shelters),
            # The headline the page prints. Counted here rather than in the
            # component so the two can never disagree.
            "shelters_dark_longer": sum(1 for item in shelters if item["difference_days"] > 0),
            "national": {"dark": summarise(national_dark), "light": summarise(national_light)},
            "shelters": shelters,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Snapshot to compare (YYYY-MM-DD). Default: newest.")
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing.")
    args = parser.parse_args()

    payload = build(args.date)
    overall = payload["overall"]
    print(f"snapshot {payload['snapshot_date']}: {overall['n']} rows, "
          f"median {overall['median_days']} days")
    for group in payload["groups"]:
        print(f"\n{group['title']}")
        for item in group["items"]:
            flag = " (small)" if item["small_sample"] else ""
            print(f"  {item['label']:<14}{item['n']:>6}  "
                  f"{item['p25_days']:>6}–{item['median_days']:>6}–{item['p75_days']:>6}{flag}")

    coat = payload["dark_coat"]
    print(f"\ndark coat: {coat['shelters_dark_longer']}/{coat['shelters_compared']} shelters, "
          f"national {coat['national']['dark']['median_days']} vs "
          f"{coat['national']['light']['median_days']}")
    for item in coat["shelters"]:
        print(f"  {item['name']:<24}{item['dark_n']:>4}/{item['light_n']:<4}"
              f"{item['dark_median_days']:>6} vs {item['light_median_days']:>6}"
              f"  {item['difference_days']:+,}")

    if args.dry_run:
        print("dry run, nothing written")
        return 0

    write_json(OUT_PATH, payload, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
