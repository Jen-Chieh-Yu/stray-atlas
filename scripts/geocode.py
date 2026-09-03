#!/usr/bin/env python3
"""Turn animal_foundplace into something that can be located, honestly graded.

See CLAUDE.md section 3 (stage 0) and constraints 4, 5 and 6.

This script does NOT call a geocoder. Everything here is text work:

  1. separate the values that are not places at all,
  2. fill in the county, from the text when it says one and otherwise from
     the shelter,
  3. pull out the district when the text names one,
  4. grade every row by how much the original text actually supports.

That ordering is the whole point. animal_foundplace names a county in 2.4% of
rows; sending "西安街" to a geocoder without a county first is the error
CLAUDE.md 1.4 forbids, because dozens of counties have one. What this script
emits is a query string plus a confidence tier, and a later step turns the
high-confidence ones into coordinates.

Usage:

    from geocode import annotate
    rows, report = annotate()          # newest snapshot, via clean.load_clean

    python scripts/geocode.py          # writes public/data/stats/foundplace.json

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clean import load_clean  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "data" / "reference"
DISTRICTS_PATH = REFERENCE_DIR / "districts.json"
OUT_PATH = ROOT / "public" / "data" / "stats" / "foundplace.json"

# Values that are not locations. Whole-value matches, deliberately not keyword
# matching: "自行車道", "彰濱產業園區服務中心" and "鹿角坑生態保護區" are real
# places that a keyword blacklist on 自行 / 園區 / 保護 would throw away.
# Counts are from the 2026-09-03 snapshot.
NON_PLACE_EXACT = frozenset(
    {
        "民眾不擬續養",  # 48
        "不擬續養",  # 12
        "所內",  # 24
        "動物之家",  # 13
        "動保園區",  # 9
        "認養退回",  # 1
        "防疫所移交",  # 1
        "無",
        "不詳",
        "未知",
    }
)
# 所內出生 / 所內生產 / 所內生產，媽媽1110241
NON_PLACE_PREFIX = ("所內",)
# 臺北市動物之家 / 台北市動物之家: the shelter itself, not where the animal was found.
SHELTER_SELF = re.compile(r"^.{2,3}[縣市]動物之家$")

COUNTY_SUFFIX = "縣市"
DISTRICT_PATTERN = re.compile(r"([一-鿿]{1,3}[區鄉鎮市])")
STREET_PATTERN = re.compile(r"[路街巷弄段]")
HOUSE_NUMBER_PATTERN = re.compile(r"\d+\s*號")

CONFIDENCE_TIERS = ("high", "medium", "low", "none")


def log(message: str) -> None:
    print(message, flush=True)


def normalise(text: str) -> str:
    """Fold the 臺 / 台 split. 台北市 outnumbers 臺北市 7 to 3 in foundplace."""
    return text.replace("台", "臺")


def load_districts() -> dict[str, set[str]] | None:
    """Official district names per county, if the reference file is present.

    Without it the district pulled out of the text cannot be verified: 淡水區
    and 區公所 are the same shape, and there is no way to tell that 東區
    belongs to several different counties. The file is optional so this script
    runs before it exists, but the report says plainly when it is missing.
    """
    if not DISTRICTS_PATH.exists():
        return None
    raw = json.loads(DISTRICTS_PATH.read_text(encoding="utf-8"))
    return {normalise(county): {normalise(d) for d in names} for county, names in raw.items()}


def is_non_place(value: str) -> bool:
    folded = normalise(value)
    if folded in {normalise(v) for v in NON_PLACE_EXACT}:
        return True
    if folded.startswith(NON_PLACE_PREFIX):
        return True
    return bool(SHELTER_SELF.match(folded))


def county_in_text(value: str, counties: set[str]) -> str | None:
    folded = normalise(value)
    for county in counties:
        if county in folded:
            return county
    return None


def district_in_text(value: str, county: str | None, districts: dict[str, set[str]] | None):
    """Return (district, verified). verified is None when no reference list exists."""
    folded = normalise(value)
    if county:
        # 南投縣南投市: strip the county so its own name is not read as a district.
        folded = folded.replace(county, "", 1)
    for candidate in DISTRICT_PATTERN.findall(folded):
        if districts is None:
            return candidate, None
        if county and candidate in districts.get(county, set()):
            return candidate, True
        if any(candidate in names for names in districts.values()):
            return candidate, False
    return None, None


def grade(value: str, county_from_text: bool, district: str | None) -> str:
    """CLAUDE.md 3, stage 0: high / medium / low / none.

    The tier describes what the ORIGINAL TEXT supports, never how confident the
    geocoder later feels. A county filled in from the shelter can never lift a
    row above low, because CLAUDE.md 1.5 is explicit that an animal is not
    necessarily found in the county of the shelter holding it.
    """
    if county_from_text and HOUSE_NUMBER_PATTERN.search(value):
        return "high"
    if district and STREET_PATTERN.search(value):
        return "medium"
    # Everything left is low: a street with no district, a bare district, or a
    # landmark such as 鹿港體育場. They differ in kind, which place_kind
    # records, but not in how much the text pins down the location. "none" is
    # reserved for rows with no location at all, so nothing here drops below.
    return "low"


def annotate(snapshot_date: str | None = None) -> tuple[list[dict], dict]:
    rows, clean_report = load_clean(snapshot_date)
    districts = load_districts()
    counties = {normalise(name) for name in {row["area_name"] for row in rows}}

    tiers = dict.fromkeys(CONFIDENCE_TIERS, 0)
    kinds: dict[str, int] = {}
    county_source = {"text": 0, "shelter": 0, "none": 0}
    district_found = 0
    district_verified = 0
    district_unverified = 0
    county_mismatch = 0
    samples: dict[str, list[str]] = {tier: [] for tier in CONFIDENCE_TIERS}

    for row in rows:
        value = row["animal_foundplace"]
        shelter_county = normalise(row["area_name"])

        if not value:
            kind, tier = "blank", "none"
            row.update(
                place_kind=kind,
                foundplace_county=None,
                county_source="none",
                foundplace_district=None,
                district_verified=None,
                geocode_query=None,
                location_confidence=tier,
            )
        elif is_non_place(value):
            kind, tier = "non_place", "none"
            row.update(
                place_kind=kind,
                foundplace_county=None,
                county_source="none",
                foundplace_district=None,
                district_verified=None,
                geocode_query=None,
                location_confidence=tier,
            )
        else:
            text_county = county_in_text(value, counties)
            county = text_county or shelter_county
            district, verified = district_in_text(value, county, districts)

            if text_county and text_county != shelter_county:
                # Not an error: CLAUDE.md 1.5, animals are transferred across
                # county lines. Counted so the size of the effect is visible.
                county_mismatch += 1

            if STREET_PATTERN.search(value):
                kind = "address"
            elif district:
                kind = "district"
            else:
                kind = "landmark"

            tier = grade(value, text_county is not None, district)
            remainder = normalise(value)
            if text_county:
                remainder = remainder.replace(text_county, "", 1)
            row.update(
                place_kind=kind,
                foundplace_county=county,
                county_source="text" if text_county else "shelter",
                foundplace_district=district,
                district_verified=verified,
                geocode_query=f"{county}{remainder}",
                location_confidence=tier,
            )
            county_source["text" if text_county else "shelter"] += 1
            if district:
                district_found += 1
                if verified is True:
                    district_verified += 1
                elif verified is False:
                    district_unverified += 1

        if row["location_confidence"] == "none":
            county_source["none"] += 1
        tiers[row["location_confidence"]] += 1
        kinds[row["place_kind"]] = kinds.get(row["place_kind"], 0) + 1
        bucket = samples[row["location_confidence"]]
        if value and len(bucket) < 5 and value not in bucket:
            bucket.append(value)

    total = len(rows)
    report = {
        "snapshot_date": clean_report["snapshot_date"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": total,
        "district_reference": "loaded" if districts else "missing",
        "place_kinds": kinds,
        "confidence": {
            tier: {"rows": count, "share": round(count / total, 4)} for tier, count in tiers.items()
        },
        "county_source": county_source,
        "county_from_text_differs_from_shelter": county_mismatch,
        "district": {
            "extracted": district_found,
            "verified_against_reference": district_verified,
            "not_in_that_county": district_unverified,
        },
        "samples": samples,
    }
    return rows, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Snapshot to use (YYYY-MM-DD). Default: the newest.")
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing.")
    args = parser.parse_args()

    _, report = annotate(args.date)

    log(f"snapshot {report['snapshot_date']}: {report['rows']} rows")
    log(f"district reference: {report['district_reference']}")
    log("place kinds: " + ", ".join(f"{k}={v}" for k, v in sorted(report["place_kinds"].items())))
    for tier in CONFIDENCE_TIERS:
        item = report["confidence"][tier]
        log(f"  {tier:6s} {item['rows']:5d}  {item['share'] * 100:5.1f}%")
    log(f"county from text: {report['county_source']['text']}, "
        f"inferred from shelter: {report['county_source']['shelter']}")
    log(f"text county differs from shelter county: "
        f"{report['county_from_text_differs_from_shelter']}")
    log(f"districts extracted: {report['district']['extracted']}")

    if args.dry_run:
        log("dry run, nothing written")
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    log(f"wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
