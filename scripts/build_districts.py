#!/usr/bin/env python3
"""Convert the official 鄉鎮市區界線 shapefile into the two files this project uses.

Source: 內政部, published as dataset 7441 on https://data.gov.tw/dataset/7441
        (鄉鎮市區界線 TWD97經緯度). The download is a zipped ESRI shapefile;
        TOWN_MOI_<date>.dbf carries the names and .shp the polygons.

Outputs:
    data/reference/districts.json   county -> district names, used by geocode.py
    public/data/districts.geojson   simplified district boundaries
    public/data/counties.geojson    the same boundaries dissolved to 22 counties

This is a one-off tool, not part of the daily pipeline, so unlike
fetch_snapshot.py and clean.py it is allowed an external dependency:

    pip install pyshp

The source archive is NOT committed. It is 12.8 MB, re-downloadable from the
dataset above, and only its two derivatives are things the project depends on
(CLAUDE.md 4.1: git carries what cannot be reproduced, plus what the deploy
needs).

Coordinates are TWD97 geographic, which is WGS84 for practical purposes, so no
reprojection is needed before handing them to a web map.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
DISTRICTS_PATH = ROOT / "data" / "reference" / "districts.json"
GEOJSON_PATH = ROOT / "public" / "data" / "districts.geojson"
COUNTIES_PATH = ROOT / "public" / "data" / "counties.geojson"

EXPECTED_COUNTIES = 22
EXPECTED_DISTRICTS = 368
COORDINATE_PRECISION = 5  # ~1 m, well past what a choropleth can show


def log(message: str) -> None:
    print(message, flush=True)


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Ramer-Douglas-Peucker, tolerance in degrees.

    Written out rather than pulled from shapely: this is the only geometry
    operation the project needs, and it keeps the tool to one dependency.
    """
    if tolerance <= 0 or len(points) < 3:
        return points

    def distance(point, start, end) -> float:
        (x, y), (x1, y1), (x2, y2) = point, start, end
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x - x1, y - y1)
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        index, worst = -1, 0.0
        for i in range(start + 1, end):
            d = distance(points[i], points[start], points[end])
            if d > worst:
                index, worst = i, d
        if worst > tolerance:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [point for point, keeper in zip(points, keep) if keeper]


def wind(ring, counter_clockwise: bool):
    """RFC 7946 winding: exterior rings counter-clockwise, holes clockwise.

    The published files follow the RFC so they are valid GeoJSON for anything
    that reads them. d3-geo predates the RFC and uses the opposite spherical
    convention, so the frontend reverses every ring once at load; see
    src/composables/useAtlasData.ts. Getting this wrong is not subtle: an
    inverted exterior ring means "everything outside this shape" and renders
    as a rectangle covering the viewport.
    """
    if (ring_area(ring) > 0) != counter_clockwise:
        ring.reverse()
    return ring


def ring_area(ring) -> float:
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total / 2


def point_in_ring(point, ring) -> bool:
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def dissolve_county(shapes, tolerance: float) -> list[list[list[list[float]]]]:
    """Merge a county's district polygons into its outline.

    Done by edge cancellation on the UNSIMPLIFIED geometry: an edge shared by
    two districts appears exactly twice and is dropped, leaving only the
    county's own boundary. The source is topologically clean — 507,552 of its
    639,722 undirected edges appear twice and the rest are coastline — so this
    works without a geometry library.

    Simplification must come after the merge, not before: Douglas-Peucker
    applied to each district independently would thin a shared border two
    different ways and leave slivers along it.
    """
    counts: dict = {}
    for shape in shapes:
        parts = list(shape.parts) + [len(shape.points)]
        for start, end in zip(parts, parts[1:]):
            ring = [(round(x, 7), round(y, 7)) for x, y in shape.points[start:end]]
            for p, q in zip(ring, ring[1:]):
                if p != q:
                    key = (p, q) if p <= q else (q, p)
                    counts[key] = counts.get(key, 0) + 1

    neighbours: dict = {}
    for (p, q), n in counts.items():
        if n == 1:
            neighbours.setdefault(p, []).append(q)
            neighbours.setdefault(q, []).append(p)

    used: set = set()
    rings = []
    for start in list(neighbours):
        while neighbours[start]:
            ring = [start]
            current, previous = start, None
            while True:
                step = None
                for candidate in neighbours[current]:
                    key = (current, candidate) if current <= candidate else (candidate, current)
                    if key in used:
                        continue
                    if candidate == previous and len(neighbours[current]) > 1:
                        continue
                    step = candidate
                    break
                if step is None:
                    break
                used.add((current, step) if current <= step else (step, current))
                ring.append(step)
                previous, current = current, step
                if current == start:
                    break
            if len(ring) >= 4 and ring[0] == ring[-1]:
                rings.append(ring)
            else:
                break

    simplified = []
    for ring in rings:
        thinned = simplify(
            [(round(x, COORDINATE_PRECISION), round(y, COORDINATE_PRECISION)) for x, y in ring],
            tolerance,
        )
        if len(thinned) >= 4:
            if thinned[0] != thinned[-1]:
                thinned.append(thinned[0])
            simplified.append([[x, y] for x, y in thinned])
    simplified = [list(ring) for ring in simplified]

    # Nest enclaves as holes rather than separate polygons, or 臺北市 would be
    # painted over by 新北市 and 嘉義市 by 嘉義縣.
    simplified.sort(key=lambda ring: -abs(ring_area(ring)))
    taken = [False] * len(simplified)
    polygons = []
    for i, outer in enumerate(simplified):
        if taken[i]:
            continue
        taken[i] = True
        polygon = [outer]
        for j in range(i + 1, len(simplified)):
            if not taken[j] and point_in_ring(simplified[j][0], outer):
                polygon.append(simplified[j])
                taken[j] = True
        polygons.append(
            [wind(ring, counter_clockwise=(index == 0)) for index, ring in enumerate(polygon)]
        )
    return polygons


def read_shapefile(base: Path):
    import shapefile  # noqa: PLC0415 - optional dependency, only this tool needs it

    reader = shapefile.Reader(str(base), encoding="utf-8")
    names = [field[0] for field in reader.fields[1:]]
    records = [dict(zip(names, list(record))) for record in reader.records()]
    return records, reader.shapes()


def locate_shapefile(source: Path, workdir: Path) -> Path:
    """Accept either the downloaded .zip or an already extracted .shp."""
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            archive.extractall(workdir)
        candidates = sorted(workdir.glob("TOWN_MOI_*.shp"))
        if not candidates:
            raise SystemExit(f"no TOWN_MOI_*.shp inside {source.name}")
        return candidates[0].with_suffix("")
    return source.with_suffix("")


def build(source: Path, tolerance: float, write: bool) -> None:
    with TemporaryDirectory() as tmp:
        base = locate_shapefile(source, Path(tmp))
        records, shapes = read_shapefile(base)

        counties: dict[str, set[str]] = {}
        for record in records:
            counties.setdefault(record["COUNTYNAME"], set()).add(record["TOWNNAME"])

        # Fail rather than emit a half-complete reference: geocode.py treats a
        # present districts.json as authoritative.
        if len(counties) != EXPECTED_COUNTIES or len(records) != EXPECTED_DISTRICTS:
            raise SystemExit(
                f"expected {EXPECTED_COUNTIES} counties and {EXPECTED_DISTRICTS} districts, "
                f"got {len(counties)} and {len(records)}. Check the source release."
            )

        features = []
        vertices = 0
        for record, shape in zip(records, shapes):
            parts = list(shape.parts) + [len(shape.points)]
            rings = []
            for start, end in zip(parts, parts[1:]):
                ring = [
                    (round(x, COORDINATE_PRECISION), round(y, COORDINATE_PRECISION))
                    for x, y in shape.points[start:end]
                ]
                ring = simplify(ring, tolerance)
                # A ring needs four points to close; anything less is a sliver
                # that simplification has collapsed.
                if len(ring) >= 4:
                    closed = [[x, y] for x, y in ring]
                    if closed[0] != closed[-1]:
                        closed.append(closed[0])
                    rings.append(wind(closed, counter_clockwise=True))
            vertices += sum(len(ring) for ring in rings)
            if rings:
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "county": record["COUNTYNAME"],
                            "district": record["TOWNNAME"],
                            "code": record["TOWNCODE"],
                        },
                        "geometry": {"type": "MultiPolygon", "coordinates": [[r] for r in rings]},
                    }
                )

        collection = {"type": "FeatureCollection", "features": features}
        payload = json.dumps(collection, ensure_ascii=False, separators=(",", ":"))
        log(f"{len(counties)} counties, {len(records)} districts")
        log(f"tolerance {tolerance}: {vertices:,} vertices, {len(payload) / 1024 / 1024:.2f} MB")

        if not write:
            log("dry run, nothing written")
            return

        DISTRICTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        names = {county: sorted(items) for county, items in sorted(counties.items())}
        DISTRICTS_PATH.write_text(
            "{\n"
            + ",\n".join(
                f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}"
                for k, v in names.items()
            )
            + "\n}\n",
            encoding="utf-8",
            newline="\n",
        )
        log(f"wrote {DISTRICTS_PATH.relative_to(ROOT)}")

        GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        GEOJSON_PATH.write_text(payload + "\n", encoding="utf-8", newline="\n")
        log(f"wrote {GEOJSON_PATH.relative_to(ROOT)}")

        by_county: dict = {}
        for record, shape in zip(records, shapes):
            by_county.setdefault(record["COUNTYNAME"], []).append(shape)
        county_features = [
            {
                "type": "Feature",
                "properties": {"county": county},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": dissolve_county(county_shapes, tolerance),
                },
            }
            for county, county_shapes in by_county.items()
        ]
        county_payload = json.dumps(
            {"type": "FeatureCollection", "features": county_features},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        COUNTIES_PATH.write_text(county_payload + "\n", encoding="utf-8", newline="\n")
        log(f"wrote {COUNTIES_PATH.relative_to(ROOT)} ({len(county_payload) / 1024:.0f} KB)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="The downloaded .zip, or the .shp inside it.")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.0003,
        help="Douglas-Peucker tolerance in degrees. 0 keeps every vertex (22.8 MB).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report sizes, write nothing.")
    args = parser.parse_args()
    build(args.source, args.tolerance, write=not args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
