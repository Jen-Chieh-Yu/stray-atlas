#!/usr/bin/env python3
"""Aggregate one snapshot per shelter, and list the animals in each.

See CLAUDE.md section 4.1: the frontend's data contract comes first.

    python scripts/build_shelters.py            # newest snapshot
    python scripts/build_shelters.py --date 2026-09-03

Outputs:
    public/data/shelters.json   the 37 shelters, with their totals
    public/data/animals.json    every animal, tagged with its shelter id

One file rather than one per shelter. It is 301 KB gzipped for all 8,265
animals, against roughly 30 KB for a single shelter, but it is fetched once and
then serves both the shelter page and the browse-everything page — and there is
no second copy of the same records to drift out of step.

Each animal carries its build date, not a day count. A count changes for every
animal every day, so a weekly rebuild would rewrite all 8,265 records; a date
only changes when the animal does. The page computes the difference against the
snapshot date, which is the only correct reference — this is a stock snapshot,
so counting from today would overstate it by however stale the deploy is.

Shelters are keyed on shelter_name, never on animal_shelter_pkid. Four codes
each cover two different shelters (63, 69, 81, 96), so keying on the code would
silently merge them. The public id is a short hash of the name, which stays
stable as a shelter is added or removed — a positional index would not, and
every saved link would shift.

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_stats import BUCKETS, KINDS, summarise  # noqa: E402
from clean import load_clean  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SHELTERS_PATH = ROOT / "public" / "data" / "shelters.json"
ANIMALS_PATH = ROOT / "public" / "data" / "animals.json"
LEGACY_ANIMALS_DIR = ROOT / "public" / "data" / "animals"

# Fields the pages actually render. Everything else stays out of a file that is
# downloaded by every visitor who opens an animal list.
ANIMAL_FIELDS = (
    ("animal_id", "id"),
    ("animal_subid", "subid"),
    ("animal_kind", "kind"),
    ("animal_Variety", "variety"),
    ("variety_group", "group"),
    ("animal_sex", "sex"),
    ("animal_bodytype", "body"),
    ("animal_colour", "colour"),
    ("animal_age", "age"),
    ("animal_sterilization", "sterilized"),
    ("animal_opendate", "opendate"),
    ("animal_remark", "remark"),
    ("album_file", "photo"),
)


def shelter_id(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]


def build(snapshot_date: str | None) -> tuple[dict, list[dict]]:
    rows, report = load_clean(snapshot_date)

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["shelter_name"], []).append(row)

    shelters = []
    animals: list[dict] = []
    for name, members in grouped.items():
        identifier = shelter_id(name)
        first = members[0]
        # Three shelters carry more than one spelling of their address, and
        # 新北市瑞芳區公立動物之家 is genuinely two sites under one name. All
        # of them are listed rather than silently picking one.
        addresses = sorted({row["shelter_address"] for row in members})
        entry = {
            "id": identifier,
            "name": name,
            "county": first["area_name"],
            "area_pkid": first["animal_area_pkid"],
            "addresses": addresses,
            "tel": first["shelter_tel"],
            "all": summarise(members),
        }
        for kind in KINDS:
            entry[kind] = summarise([row for row in members if row["animal_kind"] == kind])
        shelters.append(entry)

        animals.extend(
            {target: row.get(source, "") for source, target in ANIMAL_FIELDS}
            | {"shelter": identifier, "created": row["animal_createtime"][:10]}
            for row in members
        )

    shelters.sort(key=lambda item: (item["area_pkid"].zfill(3), -item["all"]["count"]))
    # Longest-resident first, so every list opens on the animals that have been
    # waiting most — the ones the site exists to make visible.
    animals.sort(key=lambda item: item["created"])

    payload = {
        "snapshot_date": report["snapshot_date"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "buckets": [{"label": label, "min": low, "max": high} for label, low, high in BUCKETS],
        "kinds": list(KINDS),
        "shelters": shelters,
    }
    return payload, animals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Snapshot to aggregate (YYYY-MM-DD). Default: newest.")
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing.")
    args = parser.parse_args()

    payload, animals = build(args.date)
    print(f"snapshot {payload['snapshot_date']}: {len(payload['shelters'])} shelters")
    with_photo = sum(1 for animal in animals if animal["photo"])
    print(f"animals {len(animals)}, with a photo {with_photo} "
          f"({with_photo / len(animals) * 100:.1f}%)")
    for shelter in payload["shelters"][:5]:
        print(f"  {shelter['county']:5s} {shelter['name']:28s} {shelter['all']['count']:5d}")
    print("  ...")

    if args.dry_run:
        print("dry run, nothing written")
        return 0

    SHELTERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SHELTERS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {SHELTERS_PATH.relative_to(ROOT)} ({SHELTERS_PATH.stat().st_size} bytes)")

    ANIMALS_PATH.write_text(
        json.dumps(animals, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {ANIMALS_PATH.relative_to(ROOT)} ({ANIMALS_PATH.stat().st_size} bytes)")

    # The per-shelter directory this script used to produce would otherwise sit
    # in public/ forever, shipped to every visitor as dead weight. Tidying it is
    # not worth failing the build over.
    if LEGACY_ANIMALS_DIR.exists():
        try:
            shutil.rmtree(LEGACY_ANIMALS_DIR)
            print(f"removed the superseded {LEGACY_ANIMALS_DIR.relative_to(ROOT)}/")
        except OSError as error:
            print(f"::warning::could not remove {LEGACY_ANIMALS_DIR.relative_to(ROOT)}/: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
