#!/usr/bin/env python3
"""Place every shelter on the map, and carry what a map panel needs to show.

    python scripts/build_shelter_points.py

Output: public/data/shelter-points.json

No geocoder is called. shelter_address names a 鄉鎮市區, and the project
already ships that district's polygon, so the district's centroid is a
position the data itself supports. It is deliberately coarser than a street
address: the point says "this shelter is in this district", and the page says
so too. A geocoded rooftop position would look more precise than the source
justifies, and 內政部 TGOS is not open to individuals in any case.

Two municipalities write addresses without the 區 and need a stated mapping;
they are listed in MANUAL below rather than guessed at run time.

Standard library only.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
SHELTERS = ROOT / "public" / "data" / "shelters.json"
DISTRICTS = ROOT / "public" / "data" / "districts.geojson"
OUT_PATH = ROOT / "public" / "data" / "shelter-points.json"

# 新竹市 and 嘉義市 write their addresses without the district. Both were read
# off the address by hand and are recorded here so the judgement is auditable
# rather than buried in a heuristic.
MANUAL = {
    "新竹市動物保護教育園區": "北區",
    "嘉義市動物保護教育園區": "東區",
}


def largest_ring(feature: dict) -> list[list[float]]:
    geometry = feature["geometry"]
    polygons = (
        [geometry["coordinates"]]
        if geometry["type"] == "Polygon"
        else geometry["coordinates"]
    )
    best, best_area = None, 0.0
    for polygon in polygons:
        ring = polygon[0]
        area = abs(
            sum(
                ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
                for i in range(len(ring) - 1)
            )
            / 2
        )
        if area > best_area:
            best, best_area = ring, area
    return best or []


def centroid(ring: list[list[float]]) -> tuple[float, float]:
    """Planar area-weighted centroid.

    Not d3's geoCentroid, and not by accident: that one is spherical and reads
    an RFC 7946 exterior ring as the complement of the polygon - the same
    winding convention that once rendered the whole map as a rectangle - so it
    answers with a point on the far side of the globe. At district scale the
    planar centroid is accurate enough and cannot be caught by that.
    """
    area = cx = cy = 0.0
    for i in range(len(ring) - 1):
        cross = ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
        area += cross
        cx += (ring[i][0] + ring[i + 1][0]) * cross
        cy += (ring[i][1] + ring[i + 1][1]) * cross
    area *= 0.5
    return round(cx / (6 * area), 6), round(cy / (6 * area), 6)


def build() -> dict:
    payload = json.loads(SHELTERS.read_text(encoding="utf-8"))
    districts = json.loads(DISTRICTS.read_text(encoding="utf-8"))

    by_key = {f["properties"]["c"] + "|" + f["properties"]["t"]: f for f in districts["features"]}
    names: dict[str, list[str]] = {}
    for feature in districts["features"]:
        names.setdefault(feature["properties"]["c"], []).append(feature["properties"]["t"])

    points, unplaced = [], []
    for shelter in payload["shelters"]:
        district = MANUAL.get(shelter["name"])
        if district is None:
            for address in shelter["addresses"]:
                district = next((d for d in names.get(shelter["county"], []) if d in address), None)
                if district:
                    break
        feature = by_key.get(f"{shelter['county']}|{district}") if district else None
        if feature is None:
            unplaced.append(shelter["name"])
            continue
        lon, lat = centroid(largest_ring(feature))
        points.append(
            {
                "id": shelter["id"],
                "name": shelter["name"],
                "county": shelter["county"],
                "district": district,
                "lon": lon,
                "lat": lat,
                "count": shelter["all"]["count"],
                "median_days": shelter["all"]["median_days"],
                "mean_days": shelter["all"]["mean_days"],
                "max_days": shelter["all"]["max_days"],
                "dogs": shelter["狗"]["count"],
                "cats": shelter["貓"]["count"],
                "tel": shelter["tel"],
                # Every spelling, not the first: 新北市瑞芳區公立動物之家 is two
                # sites filed under one name, and picking one would hide that.
                "addresses": shelter["addresses"],
                "manual": shelter["name"] in MANUAL,
            }
        )

    points.sort(key=lambda p: -p["count"])
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snapshot_date": payload["snapshot_date"],
        "position": "district_centroid",
        "unplaced": unplaced,
        "points": points,
    }


def main() -> int:
    result = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    print(f"wrote {OUT_PATH.relative_to(ROOT)} ({OUT_PATH.stat().st_size:,} bytes)")
    print(f"  placed {len(result['points'])}, unplaced {len(result['unplaced'])}")
    manual = [p["name"] for p in result["points"] if p["manual"]]
    print(f"  by hand: {', '.join(manual) or '—'}")
    if result["unplaced"]:
        print(f"  ::warning::unplaced: {', '.join(result['unplaced'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
