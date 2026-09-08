#!/usr/bin/env python3
"""Aggregate the stay-duration distribution the analysis page reads.

    python scripts/build_distribution.py            # newest snapshot
    python scripts/build_distribution.py --date 2026-09-07

Output: public/data/stats/distribution.json

What this measures, and what it does not
----------------------------------------
Every animal in a snapshot is still in the shelter, so days_in_shelter is a
*right-censored* observation: it says the animal has been there at least this
long, never how long the stay will turn out to be. The sample is also
length-biased, because a long stay is present in more daily snapshots than a
short one and is therefore more likely to be caught by any single one.

So this file describes the composition of the population currently in the
shelters. It is NOT the distribution of how long a stay lasts, and the page has
to say so. The estimator for that question is a survival curve, which needs
departure events - stage 3 recovers those by diffing consecutive snapshots.

Why both scales are published
-----------------------------
On a linear axis the density falls away monotonically and the whole structure
is compressed into the first few hundred days. On log10 it is clearly bimodal:
one mode under a year, a trough, then a second mode around a decade. Both are
true of the same numbers - the second mode is a statement about orders of
magnitude, not about days - so the page ships both and lets the reader switch,
rather than picking the flattering one.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clean import load_clean  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "public" / "data" / "stats" / "distribution.json"

# A stay recorded as 0 days was registered on the snapshot date. It is a real
# observation, not a missing value, but log10(0) is not, so it is placed at half
# a day - which is what "registered today" means.
ZERO_DAY = 0.5

GRID_POINTS = 220
LOG_TICKS = (1, 7, 30, 90, 365, 730, 1825, 3650)

# A KDE's shape is an argument about the bandwidth as much as about the data:
# narrow enough and every wobble becomes a mode, wide enough and the second mode
# disappears entirely. Publishing three multiples of Silverman's value and giving
# the reader the control is the honest version of the chart - the conclusion has
# to survive being smoothed, or it was never there.
BANDWIDTH_LEVELS = (("fine", 0.6), ("standard", 1.0), ("smooth", 1.7))


def quantile(ordered: list[int], q: float) -> int | None:
    """Nearest-rank quantile. No interpolation: these are whole days, and a
    quantile that lands between two animals is not a day anyone spent."""
    if not ordered:
        return None
    index = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


def stdev(values: list[float], mean: float) -> float:
    if len(values) < 2:
        return 0.0
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def silverman(values: list[float]) -> float:
    """Silverman's rule of thumb, on the IQR-robust form.

    The rule assumes near-normality and over-smooths a multi-modal sample, which
    is exactly the sample here. Taking min(sd, IQR/1.34) is the standard guard:
    on a heavy tail the IQR term is far smaller than the standard deviation, so
    the bandwidth is set by the bulk of the data rather than by the outliers.
    """
    n = len(values)
    if n < 2:
        return 1.0
    mean = sum(values) / n
    ordered = sorted(values)
    spread = ordered[min(n - 1, int(0.75 * n))] - ordered[int(0.25 * n)]
    scale = min(stdev(values, mean), spread / 1.34) if spread > 0 else stdev(values, mean)
    if scale <= 0:
        scale = stdev(values, mean) or 1.0
    return 0.9 * scale * n ** (-0.2)


def kde(
    values: list[float],
    lo: float,
    hi: float,
    reflect_at: float | None = None,
    scale: float = 1.0,
    pad_hi: float = 3.0,
) -> dict:
    """Gaussian KDE evaluated on a fixed grid, as a density that integrates to 1.

    Written out rather than pulled from scipy: it is fifteen lines, and this
    project's pipeline is standard-library-only by policy. Reflection is applied
    on the linear scale, where a plain KDE spreads mass below zero and invents
    animals that have been in a shelter for a negative number of days.

    The grid runs pad_hi bandwidths past the largest observation so the curve
    decays to zero on its own. Stopping it exactly at the maximum cuts the last
    kernel in half and draws a cliff, which reads as a feature of the data
    rather than of where the axis was cut.
    """
    n = len(values)
    if n < 2:
        return {"bandwidth": 0.0, "points": []}
    h = silverman(values) * scale
    hi = hi + pad_hi * h
    step = (hi - lo) / (GRID_POINTS - 1)
    norm = 1.0 / (n * h * math.sqrt(2 * math.pi))
    points = []
    for i in range(GRID_POINTS):
        x = lo + i * step
        total = 0.0
        for v in values:
            z = (x - v) / h
            if -5.0 < z < 5.0:
                total += math.exp(-0.5 * z * z)
            if reflect_at is not None:
                zr = (x - (2 * reflect_at - v)) / h
                if -5.0 < zr < 5.0:
                    total += math.exp(-0.5 * zr * zr)
        points.append([round(x, 4), round(total * norm, 8)])
    return {"bandwidth": round(h, 4), "points": points}


def histogram(values: list[float], lo: float, hi: float, bins: int) -> list[dict]:
    """Counts and densities, so bars and the KDE curve share one y axis."""
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        index = min(bins - 1, max(0, int((v - lo) / width)))
        counts[index] += 1
    total = len(values) or 1
    return [
        {
            "x0": round(lo + i * width, 4),
            "x1": round(lo + (i + 1) * width, 4),
            "count": counts[i],
            "density": round(counts[i] / (total * width), 8),
        }
        for i in range(bins)
    ]


def ecdf(ordered: list[int], points: int = 180) -> list[list[float]]:
    """The empirical CDF, thinned to a drawable number of points.

    It is here because it needs no bandwidth and makes no smoothing assumption:
    whatever the KDE's shape turns out to be, "43% have been in a shelter for
    over a year" is read straight off this curve and can be quoted.
    """
    n = len(ordered)
    if not n:
        return []
    keep = sorted({0, n - 1} | {round(i * (n - 1) / (points - 1)) for i in range(points)})
    return [[ordered[i], round((i + 1) / n, 5)] for i in keep]


def summarise(days: list[int]) -> dict:
    ordered = sorted(days)
    n = len(ordered)
    linear = [float(v) for v in ordered]
    logged = [math.log10(max(v, ZERO_DAY)) for v in ordered]
    log_hi = math.log10(max(ordered[-1], 1))
    return {
        "count": n,
        "median_days": quantile(ordered, 0.5),
        "mean_days": round(sum(ordered) / n),
        "p25_days": quantile(ordered, 0.25),
        "p75_days": quantile(ordered, 0.75),
        "p90_days": quantile(ordered, 0.90),
        "max_days": ordered[-1],
        "over_year": round(sum(1 for v in ordered if v > 365) / n, 4),
        "over_4_years": round(sum(1 for v in ordered if v > 1460) / n, 4),
        "linear": {
            "bins": histogram(linear, 0.0, float(ordered[-1]), 40),
            "kde": {
                name: kde(linear, 0.0, float(ordered[-1]), reflect_at=0.0, scale=scale)
                for name, scale in BANDWIDTH_LEVELS
            },
        },
        "log": {
            "bins": histogram(logged, math.log10(ZERO_DAY), log_hi, 34),
            "kde": {
                name: kde(logged, math.log10(ZERO_DAY), log_hi, scale=scale)
                for name, scale in BANDWIDTH_LEVELS
            },
        },
        "ecdf": ecdf(ordered),
    }


def build(snapshot_date: str | None) -> dict:
    rows, _ = load_clean(snapshot_date)
    scopes: dict[str, list[int]] = {"all": [], "dog": [], "cat": []}
    for row in rows:
        days = row["days_in_shelter"]
        if days is None:
            continue
        scopes["all"].append(days)
        if row["animal_kind"] == "狗":
            scopes["dog"].append(days)
        elif row["animal_kind"] == "貓":
            scopes["cat"].append(days)
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snapshot_date": snapshot_date or "",
        "log_ticks": list(LOG_TICKS),
        "bandwidth_levels": [name for name, _ in BANDWIDTH_LEVELS],
        "scopes": {name: summarise(days) for name, days in scopes.items() if days},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Snapshot date (YYYY-MM-DD). Defaults to the newest.")
    args = parser.parse_args()

    payload = build(args.date)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    size = OUT_PATH.stat().st_size
    print(f"wrote {OUT_PATH.relative_to(ROOT)} ({size:,} bytes)")
    for name, scope in payload["scopes"].items():
        print(
            f"  {name:4} n={scope['count']:>5,} median={scope['median_days']:>5,}"
            f" log h={[round(k['bandwidth'], 3) for k in scope['log']['kde'].values()]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
