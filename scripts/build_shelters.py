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

Each shelter also carries `info` from data/reference/shelter-info.json: opening
hours, how to visit and the adoption notice, kept by hand from the shelters'
own websites because the open data has none of it. A shelter the file does not
cover simply has no `info`; a file that does not check out stops the build.

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_stats import BUCKETS, KINDS, summarise  # noqa: E402
from clean import load_clean  # noqa: E402
from common import PUBLIC_DATA, REFERENCE_DIR, relative, utc_now, write_json  # noqa: E402

SHELTERS_PATH = PUBLIC_DATA / "shelters.json"
ANIMALS_PATH = PUBLIC_DATA / "animals.json"
LEGACY_ANIMALS_DIR = PUBLIC_DATA / "animals"
INFO_PATH = REFERENCE_DIR / "shelter-info.json"

# walk-in: the shelter says to come during opening hours; appointment: it says
# to book first; unstated: it says neither, and the page does not guess.
VISIT_MODES = ("walk-in", "appointment", "unstated")
INFO_FIELDS = (
    "hours",
    "visit",
    "visit_note",
    "caution",
    "note",
    "see",
    "official",
    "adoption",
    "sources",
    "checked",
)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

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


def check_info(entries: dict[str, dict]) -> list[str]:
    """Every way a hand-kept entry can be wrong without anyone noticing."""
    problems = []
    for key, entry in entries.items():
        where = f"{key} {entry.get('name', '?')}"
        if shelter_id(entry.get("name", "")) != key:
            problems.append(f"{where}: the key is not the id of this name")
        if not DATE.fullmatch(entry.get("checked", "")):
            problems.append(f"{where}: checked must be YYYY-MM-DD")
        if "same_as" in entry:
            target = entries.get(entry["same_as"])
            if target is None or "same_as" in target:
                problems.append(f"{where}: same_as must name an entry that has its own data")
            if not entry.get("note"):
                problems.append(f"{where}: same_as needs a note saying why")
            continue
        if entry.get("visit") not in (*VISIT_MODES, None):
            problems.append(f"{where}: visit must be one of {', '.join(VISIT_MODES)} or null")
        if not entry.get("hours") and not entry.get("note"):
            problems.append(f"{where}: without hours, a note must say why")
        if entry.get("see") is not None and entry["see"] not in entries:
            problems.append(f"{where}: see must name another entry")
        links = [source.get("url", "") for source in entry.get("sources", [])]
        if not links:
            problems.append(f"{where}: at least one source")
        if entry.get("adoption"):
            links.append(entry["adoption"].get("url", ""))
        if entry.get("official"):
            links.append(entry["official"].get("source", {}).get("url", ""))
        problems.extend(f"{where}: {link!r} is not an https link"
                        for link in links if not link.startswith("https://"))
    return problems


def load_info(path: Path = INFO_PATH) -> dict[str, dict]:
    """The hand-kept entries by shelter id, with same_as followed: a shelter
    listed twice in the open data shows the other entry's details under its
    own note."""
    entries = json.loads(path.read_text(encoding="utf-8"))["shelters"]
    problems = check_info(entries)
    if problems:
        raise ValueError(f"{relative(path)}:\n  " + "\n  ".join(problems))
    resolved = {}
    for key, entry in entries.items():
        base = entries[entry["same_as"]] if "same_as" in entry else entry
        info = {field: base[field] for field in INFO_FIELDS if base.get(field) is not None}
        if "same_as" in entry:
            info["note"] = entry["note"]
        resolved[key] = info
    return resolved


def build(snapshot_date: str | None) -> tuple[dict, list[dict]]:
    rows, report = load_clean(snapshot_date)
    info = load_info()

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
        if identifier in info:
            entry["info"] = info[identifier]
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
        "generated_at_utc": utc_now(),
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
    missing = [shelter["name"] for shelter in payload["shelters"] if "info" not in shelter]
    print(f"visitor info for {len(payload['shelters']) - len(missing)} shelters")
    if missing:
        # A new shelter in the feed: the page still works, it just has no
        # hours yet. Say so in the log rather than fail the daily build.
        print(f"::warning::no entry in {relative(INFO_PATH)} for: {', '.join(missing)}")

    if args.dry_run:
        print("dry run, nothing written")
        return 0

    write_json(SHELTERS_PATH, payload, indent=1)
    write_json(ANIMALS_PATH, animals)

    # The per-shelter directory this script used to produce would otherwise sit
    # in public/ forever, shipped to every visitor as dead weight. Tidying it is
    # not worth failing the build over.
    if LEGACY_ANIMALS_DIR.exists():
        try:
            shutil.rmtree(LEGACY_ANIMALS_DIR)
            print(f"removed the superseded {relative(LEGACY_ANIMALS_DIR)}/")
        except OSError as error:
            print(f"::warning::could not remove {relative(LEGACY_ANIMALS_DIR)}/: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
