#!/usr/bin/env python3
"""The home page's counts and cards, so it can render without the roster.

    python scripts/build_home.py

Output:
    public/data/home.json

The home page shows 18 cards and a few dozen counts, and used to download
animals.json (2.8 MB unpacked) to compute them. This file carries exactly
what the page draws; the roster is still fetched, but after the page is up.

Reads build_shelters.py's output, so it runs after that script and follows
whichever snapshot the shelters file was built from - the same arrangement as
build_shelter_points.py.

Counts, not rankings. The page sorts every list with tally() in
src/lib/animals.ts, which breaks ties by zh-TW collation; Python's standard
library cannot reproduce that order, so this file carries the count per key
and the page keeps ranking them itself. Keys appear in roster order, which
is the order the page reads the 其他 names in.

Days are counted the way the page counts them: whole days from the build
date to the snapshot date, never to today, with an even-length median
rounded half up as median() in src/lib/animals.ts does.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PUBLIC_DATA, utc_now, write_json  # noqa: E402

SHELTERS = PUBLIC_DATA / "shelters.json"
ANIMALS = PUBLIC_DATA / "animals.json"
OUT_PATH = PUBLIC_DATA / "home.json"

# (key, min, max) - the same bands as DAY_BANDS in src/lib/animals.ts, which
# owns their labels. tests/test_home.py reads that file and fails if the two
# drift apart, since a drifted band would put a wrong count beside a chip.
DAY_BANDS = (
    ("0-30", 0, 30),
    ("31-90", 31, 90),
    ("91-365", 91, 365),
    ("1-2y", 366, 730),
    ("2-5y", 731, 1825),
    ("5y+", 1826, None),
)

LONGEST = 10
NEWEST = 4
NEWEST_KINDS = ("狗", "貓")


def days_between(created: str, snapshot: date) -> int | None:
    try:
        return (snapshot - date.fromisoformat(created)).days
    except ValueError:
        return None


def median(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    # Math.round in the page: half up, not Python's half to even.
    return math.floor((ordered[mid - 1] + ordered[mid]) / 2 + 0.5)


def band_of(days: int | None) -> str | None:
    if days is None:
        return None
    for key, low, high in DAY_BANDS:
        if days >= low and (high is None or days <= high):
            return key
    return None


def kind_block(
    members: list[dict], county_of: dict[str, str], days: dict[str, int | None]
) -> dict:
    bands = dict.fromkeys((key for key, _, _ in DAY_BANDS), 0)
    for animal in members:
        key = band_of(days[animal["id"]])
        if key is not None:
            bands[key] += 1
    return {
        "count": len(members),
        "mixed": sum(1 for animal in members if animal["group"] == "mixed"),
        "counties": dict(Counter(county_of.get(animal["shelter"], "") for animal in members)),
        "varieties": dict(Counter(animal["variety"] for animal in members)),
        "body": dict(Counter(animal["body"] for animal in members)),
        "age": dict(Counter(animal["age"] for animal in members)),
        "bands": bands,
    }


def build(shelters: dict, animals: list[dict]) -> dict:
    snapshot = date.fromisoformat(shelters["snapshot_date"])
    county_of = {shelter["id"]: shelter["county"] for shelter in shelters["shelters"]}
    days = {animal["id"]: days_between(animal["created"], snapshot) for animal in animals}

    # Stable sorts on the roster's own order, as Array.prototype.sort is in
    # the page, so ties come out the same way they did there.
    dated = [animal for animal in animals if days[animal["id"]] is not None]
    longest = sorted(dated, key=lambda animal: -days[animal["id"]])[:LONGEST]
    newest = {
        kind: sorted(
            (animal for animal in dated if animal["kind"] == kind),
            key=lambda animal: days[animal["id"]],
        )[:NEWEST]
        for kind in NEWEST_KINDS
    }

    return {
        "snapshot_date": shelters["snapshot_date"],
        "generated_at_utc": utc_now(),
        "roster": {"count": len(animals)},
        "median_days": median([value for value in days.values() if value is not None]),
        "kinds": {
            kind: kind_block(
                [animal for animal in animals if animal["kind"] == kind], county_of, days
            )
            for kind in shelters["kinds"]
        },
        "longest": longest,
        "newest": newest,
    }


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    shelters = json.loads(SHELTERS.read_text(encoding="utf-8"))
    animals = json.loads(ANIMALS.read_text(encoding="utf-8"))
    payload = build(shelters, animals)

    print(f"snapshot {payload['snapshot_date']}: {payload['roster']['count']} animals, "
          f"median {payload['median_days']} days")
    for kind, block in payload["kinds"].items():
        print(f"  {kind} {block['count']:5d}  varieties {len(block['varieties'])}")
    write_json(OUT_PATH, payload, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
