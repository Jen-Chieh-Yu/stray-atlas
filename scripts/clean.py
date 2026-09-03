#!/usr/bin/env python3
"""Clean one archived snapshot and emit the frontend's reference data.

See CLAUDE.md section 3 (stage 0) and section 4.1 (data contract first).

Two ways to use this module:

  As a library, which is how the analysis and geocoding scripts should
  consume the data:

      from clean import load_clean
      rows, report = load_clean()          # newest snapshot
      rows, report = load_clean("2026-09-03")

  As a CLI, which additionally writes public/data/areas.json and
  public/data/meta.json and prints the cleaning report.

The cleaned table itself is deliberately NOT persisted. It is fully
reproducible from data/raw/ in about a second, and a stored intermediate is
the kind of file that goes stale without anyone noticing. Only the two files
the frontend actually reads are written to disk (CLAUDE.md 4.1).

Nothing here ever writes to data/raw/. That directory is the archive.

Standard library only, so this stays runnable in the same environment as
scripts/fetch_snapshot.py with no install step.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# CLAUDE.md 2.1: never hard-code the repository root directory name.
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "public" / "data"

EXPECTED_AREA_COUNT = 22
SENTINEL_DATE = "1900-01-01"

# The county sits at the head of both shelter_name and shelter_address; two or
# three characters followed by 縣 or 市. Both are curated fields with a few
# dozen distinct values, so a prefix match is safe here in a way it never is
# for the free-text animal_foundplace.
#
# shelter_name is the primary source and shelter_address only cross-checks it.
# The name is the administrative owner and is the more stable string: 37
# distinct values against 40 for the address, which carries 1-19號 / 1~19號
# and other spellings of the same place. animal_place is byte-identical to
# shelter_name in every row, so reading the county from either is the same
# operation.
COUNTY_PATTERN = re.compile(r"^(.{2,3}?[縣市])")

# When two columns hold identical values in every row, keep the one named
# first here. Both pairs below are verified duplicates in the 2026-09-03
# snapshot, but the check is made at run time rather than assumed.
DUPLICATE_PREFERENCE = (
    ("animal_update", "cDate"),
    ("shelter_name", "animal_place"),
)

# animal_Variety spells the same thing two ways: 混種犬 (5,333 dogs) and
# 混種狗 (64) in the 2026-09-01 snapshot, plus 比特犬之混種犬. Grouping is done
# here so that no analysis script has to re-invent the split, and so that a
# new spelling shows up as a rise in "unknown" rather than being silently
# counted as a pedigree breed.
MIXED_MARKERS = ("混種", "米克斯")
UNKNOWN_VARIETIES = ("", "其他")

REQUIRED_COLUMNS = (
    "animal_id",
    "animal_area_pkid",
    "animal_kind",
    "animal_createtime",
    "animal_foundplace",
    "shelter_name",
    "shelter_address",
)


def log(message: str) -> None:
    print(message, flush=True)


def snapshot_paths() -> list[Path]:
    return sorted(RAW_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].csv.gz"))


def resolve_snapshot(snapshot_date: str | None) -> Path:
    if snapshot_date:
        path = RAW_DIR / f"{snapshot_date}.csv.gz"
        if not path.exists():
            raise SystemExit(f"no snapshot for {snapshot_date} in {RAW_DIR}")
        return path
    paths = snapshot_paths()
    if not paths:
        raise SystemExit(f"no snapshots in {RAW_DIR}; run scripts/fetch_snapshot.py first")
    return paths[-1]


def read_snapshot(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read the archive, stripping the BOM the source ships (see fetch_snapshot)."""
    payload = gzip.decompress(path.read_bytes()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(payload, newline=""))
    columns = list(reader.fieldnames or [])
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    if missing:
        raise SystemExit(f"{path.name} is missing required columns: {missing}")
    # Whitespace is stripped everywhere, which also fixes the trailing spaces
    # on animal_Variety noted in PROJECT_BRIEF 4.2.
    rows = [{key: (value or "").strip() for key, value in row.items() if key} for row in reader]
    return columns, rows


def uninformative_columns(columns: list[str], rows: list[dict[str, str]]) -> list[dict]:
    """Judge emptiness and zero variance from the data, not from a fixed list.

    PROJECT_BRIEF 4.1 names six columns to drop, but that list describes one
    snapshot. animal_status and animal_closeddate are structural - the feed
    only carries animals still open for adoption - while animal_bacterin and
    the blank text columns are merely how the counties happen to fill the form
    today. Deciding at run time means the day one of them starts carrying
    information, it survives instead of being silently discarded.
    """
    findings = []
    for column in columns:
        values = {row[column] for row in rows}
        values.discard("")
        if not values:
            findings.append({"column": column, "reason": "all_blank", "distinct_values": 0})
        elif len(values) == 1:
            findings.append(
                {
                    "column": column,
                    "reason": "zero_variance",
                    "distinct_values": 1,
                    "value": next(iter(values)),
                }
            )
    return findings


def duplicate_columns(
    columns: list[str], rows: list[dict[str, str]], exclude: set[str]
) -> list[dict]:
    """Find columns holding identical values in every row.

    A duplicate is not an uninformative column: one of the pair must be kept.
    Columns already condemned as blank or zero-variance are excluded, or every
    all-blank column would be reported as a duplicate of every other one.
    """
    signatures: dict[tuple, list[str]] = {}
    for column in columns:
        if column in exclude:
            continue
        signatures.setdefault(tuple(row[column] for row in rows), []).append(column)

    findings = []
    for names in signatures.values():
        if len(names) < 2:
            continue
        keep = names[0]
        for preferred, _ in DUPLICATE_PREFERENCE:
            if preferred in names:
                keep = preferred
                break
        for name in names:
            if name != keep:
                findings.append({"dropped": name, "identical_to": keep})
    return findings


def build_area_map(rows: list[dict[str, str]]) -> dict[str, dict]:
    """animal_area_pkid to county, recovered from shelter_address.

    animal_area_pkid is a bare code; the county name only exists in
    shelter_address. Recovering it here is what makes the constraint in
    CLAUDE.md 1.4 workable: animal_foundplace can be prefixed with a county
    before it is ever sent to a geocoder.
    """
    seen: dict[str, set[str]] = {}
    shelters: dict[str, set[str]] = {}
    disagreements: set[tuple[str, str]] = set()
    for row in rows:
        pkid = row["animal_area_pkid"]
        match = COUNTY_PATTERN.match(row["shelter_name"])
        if not match:
            raise SystemExit(f"no county prefix in shelter_name: {row['shelter_name']!r}")
        county = match.group(1)

        # Cross-check against the address. The two agree on all 37 shelters
        # today; a disagreement would mean the source changed, and is worth
        # stopping for rather than silently preferring one field.
        cross = COUNTY_PATTERN.match(row["shelter_address"])
        if cross and cross.group(1) != county:
            disagreements.add((row["shelter_name"], row["shelter_address"]))

        seen.setdefault(pkid, set()).add(county)
        shelters.setdefault(pkid, set()).add(row["shelter_name"])

    if disagreements:
        raise SystemExit(
            "shelter_name and shelter_address disagree on the county for: "
            f"{sorted(disagreements)}"
        )

    conflicting = {pkid: sorted(names) for pkid, names in seen.items() if len(names) > 1}
    if conflicting:
        raise SystemExit(f"animal_area_pkid maps to more than one county: {conflicting}")
    if len(seen) != EXPECTED_AREA_COUNT:
        raise SystemExit(
            f"expected {EXPECTED_AREA_COUNT} counties, found {len(seen)}: "
            f"{sorted(seen, key=int)}. The source may have changed."
        )

    return {
        pkid: {"name": next(iter(seen[pkid])), "shelters": len(shelters[pkid])}
        for pkid in sorted(seen, key=int)
    }


def shelter_address_variants(rows: list[dict[str, str]]) -> list[dict]:
    """Shelters whose name maps to more than one address string.

    Two are punctuation variants of one address (1-19號 / 1~19號, and a URL
    written with fullwidth slashes). One is a genuine second site sharing a
    name. Either way shelter_address is not a key, and a shelter map keyed on
    it would place one shelter twice.
    """
    by_name: dict[str, set[str]] = {}
    for row in rows:
        by_name.setdefault(row["shelter_name"], set()).add(row["shelter_address"])
    return [
        {"shelter_name": name, "addresses": sorted(addresses)}
        for name, addresses in sorted(by_name.items())
        if len(addresses) > 1
    ]


def shelter_pkid_collisions(rows: list[dict[str, str]]) -> list[dict]:
    """animal_shelter_pkid is not unique per shelter.

    Four codes are shared by two shelters each. Any per-shelter analysis keyed
    on the code would silently merge them, so downstream work must key on
    shelter_name instead.
    """
    by_pkid: dict[str, set[str]] = {}
    for row in rows:
        by_pkid.setdefault(row.get("animal_shelter_pkid", ""), set()).add(row["shelter_name"])
    return [
        {"pkid": pkid, "shelter_names": sorted(names)}
        for pkid, names in sorted(by_pkid.items())
        if len(names) > 1
    ]


def variety_group(variety: str) -> str:
    """mixed / breed / unknown, from the free-text animal_Variety value."""
    if variety in UNKNOWN_VARIETIES:
        return "unknown"
    if any(marker in variety for marker in MIXED_MARKERS):
        return "mixed"
    return "breed"


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def percentile(sorted_values: list[int], fraction: float) -> int | None:
    if not sorted_values:
        return None
    index = min(int(round(fraction * (len(sorted_values) - 1))), len(sorted_values) - 1)
    return sorted_values[index]


def foundplace_stats(rows: list[dict[str, str]], counties: list[str]) -> dict:
    """Two different measures, both named explicitly.

    PROJECT_BRIEF 4.3 reports "5.1% contains a county name". That figure is
    the share of NON-BLANK values containing the character 縣 or 市 anywhere,
    which also matches 新市區, 市場 and 北市. The share of ALL rows carrying an
    actual county name is 2.4%. Both are recorded so no later reader has to
    guess which definition a number came from.
    """
    values = [row["animal_foundplace"] for row in rows]
    nonblank = [value for value in values if value]
    variants = set(counties) | {name.replace("臺", "台") for name in counties}
    with_name = sum(1 for value in nonblank if any(name in value for name in variants))
    with_char = sum(1 for value in nonblank if "縣" in value or "市" in value)
    return {
        "rows": len(values),
        "nonblank_rows": len(nonblank),
        "unique_values": len(set(nonblank)),
        "rows_with_county_name": with_name,
        "share_of_all_rows_with_county_name": round(with_name / len(values), 4),
        "rows_with_county_or_city_character": with_char,
        "share_of_nonblank_rows_with_county_or_city_character": round(
            with_char / len(nonblank), 4
        ),
    }


def load_clean(snapshot_date: str | None = None) -> tuple[list[dict], dict]:
    """Return the cleaned rows and a report describing what was done to them."""
    path = resolve_snapshot(snapshot_date)
    snapshot = path.name[:10]
    columns, rows = read_snapshot(path)
    if not rows:
        raise SystemExit(f"{path.name} has no data rows")

    uninformative = uninformative_columns(columns, rows)
    uninformative_names = {item["column"] for item in uninformative}
    duplicates = duplicate_columns(columns, rows, exclude=uninformative_names)
    dropped = uninformative_names | {item["dropped"] for item in duplicates}
    kept = [column for column in columns if column not in dropped]

    areas = build_area_map(rows)
    collisions = shelter_pkid_collisions(rows)
    address_variants = shelter_address_variants(rows)

    sentinel_nulled = 0
    future_opendate = 0
    snapshot_day = date.fromisoformat(snapshot)
    durations: list[int] = []
    undated = 0

    cleaned = []
    for row in rows:
        record = {column: row[column] for column in kept}

        # PROJECT_BRIEF 4.2: 1900-01-01 is a placeholder, not a date. Leaving
        # it in place would drag every date aggregate back by a century.
        if record.get("animal_opendate") == SENTINEL_DATE:
            record["animal_opendate"] = ""
            sentinel_nulled += 1
        opendate = parse_date(record.get("animal_opendate", ""))
        if opendate and opendate > snapshot_day:
            # Recorded, not corrected: a future opening date may well be a
            # genuine scheduled release rather than an error.
            future_opendate += 1

        record["area_name"] = areas[row["animal_area_pkid"]]["name"]
        record["variety_group"] = variety_group(record.get("animal_Variety", ""))

        # The project's central measure, defined once here so that no analysis
        # script invents its own. CLAUDE.md 1.3: this is time spent in the
        # shelter by animals still in it, never a difficulty-of-adoption score.
        created = parse_date(row["animal_createtime"])
        if created is None:
            record["days_in_shelter"] = None
            undated += 1
        else:
            days = (snapshot_day - created).days
            record["days_in_shelter"] = days
            durations.append(days)

        cleaned.append(record)

    durations.sort()
    coverage = {
        column: round(sum(1 for row in cleaned if row[column] != "") / len(cleaned), 4)
        for column in kept
    }

    report = {
        "snapshot_date": snapshot,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_file": f"data/raw/{path.name}",
        "rows": len(cleaned),
        "columns_in_source": len(columns),
        "columns_after_clean": len(kept),
        "dropped_columns": uninformative,
        "duplicate_columns": duplicates,
        "cleaning_actions": {
            "opendate_sentinel_nulled": sentinel_nulled,
            "opendate_in_the_future": future_opendate,
            "rows_without_createtime": undated,
        },
        "coverage": coverage,
        "variety_groups": {
            group: sum(1 for row in cleaned if row["variety_group"] == group)
            for group in ("mixed", "breed", "unknown")
        },
        "areas": len(areas),
        "shelters": len({row["shelter_name"] for row in rows}),
        "shelter_pkid_collisions": collisions,
        "shelter_address_variants": shelter_address_variants(rows),
        "days_in_shelter": {
            "median": percentile(durations, 0.50),
            "p75": percentile(durations, 0.75),
            "p90": percentile(durations, 0.90),
            "max": durations[-1] if durations else None,
        },
        "foundplace": foundplace_stats(rows, [area["name"] for area in areas.values()]),
        # Kept in the report so the frontend never has to re-derive it.
        "_areas": areas,
    }
    return cleaned, report


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
    log(f"wrote {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Snapshot to clean (YYYY-MM-DD). Default: the newest.")
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing.")
    args = parser.parse_args()

    rows, report = load_clean(args.date)
    areas = report.pop("_areas")

    log(f"snapshot {report['snapshot_date']}: {report['rows']} rows")
    log(f"columns {report['columns_in_source']} -> {report['columns_after_clean']}")
    for item in report["dropped_columns"]:
        detail = item.get("value", "")
        log(f"  dropped {item['column']:20s} {item['reason']}" + (f" ({detail})" if detail else ""))
    for item in report["duplicate_columns"]:
        log(f"  dropped {item['dropped']:20s} identical to {item['identical_to']}")
    log(f"areas {report['areas']}, shelters {report['shelters']}")
    for item in report["shelter_pkid_collisions"]:
        log(f"  shelter_pkid {item['pkid']} covers {item['shelter_names']}")
    for item in report["shelter_address_variants"]:
        log(f"  {item['shelter_name']} has {len(item['addresses'])} address spellings")
    log(f"days_in_shelter {report['days_in_shelter']}")

    if args.dry_run:
        log("dry run, nothing written")
        return 0

    write_json(OUT_DIR / "areas.json", areas)
    write_json(OUT_DIR / "meta.json", report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
