#!/usr/bin/env python3
"""Resize the home page hero photos into the WebP files the site ships.

Input:  assets-src/hero/<code>.jpg   originals downloaded from Unsplash by
                                     hand (not committed; see below)
Output: src/assets/hero/<slug>-1920.webp   desktop
        src/assets/hero/<slug>-960.webp    phones and small screens

The photos are free to use under the Unsplash License. Who took each one,
and the page it came from, lives in src/lib/heroPhotos.ts, which the home
and about pages both read; THIRD-PARTY-LICENSES repeats it.

The originals are about 24 MB and can be downloaded again from those pages,
so they stay out of git (CLAUDE.md 4.1: git carries what cannot be
reproduced, plus what the deploy needs). Only the resized files are
committed.

This is a one-off tool, not part of the daily pipeline, so like
build_districts.py it may use an external dependency:

    pip install pillow

Run it again only when a photo is added or replaced. The output is
deterministic for a given Pillow version.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "assets-src" / "hero"
OUTPUT_DIR = ROOT / "src" / "assets" / "hero"

# Original file name (the code used when the photos were picked) -> slug.
# Keep in step with src/lib/heroPhotos.ts.
PHOTOS = {
    "P1.jpg": "cat-dog-grass",
    "D.jpg": "dog-wall",
    "K.jpg": "cat-pavement",
    "P12.jpg": "cat-dog-sidewalk",
    "H.jpg": "dogs-dirt-road",
    "N.jpg": "cat-tabby",
    "C.jpg": "cat-dog-doorway",
    "P14.jpg": "cat-dogs-snow",
}

WIDTHS = (1920, 960)
QUALITY = 72


def main() -> int:
    missing = [name for name in PHOTOS if not (SOURCE_DIR / name).exists()]
    if missing:
        print(f"missing in {SOURCE_DIR.relative_to(ROOT)}: {', '.join(missing)}", file=sys.stderr)
        return 1
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, slug in PHOTOS.items():
        with Image.open(SOURCE_DIR / name) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
        for width in WIDTHS:
            height = round(image.height * width / image.width)
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            target = OUTPUT_DIR / f"{slug}-{width}.webp"
            # method=6: slowest, smallest; exif=b"" drops camera metadata.
            resized.save(target, "WEBP", quality=QUALITY, method=6, exif=b"")
            print(f"{target.relative_to(ROOT)}  {width}x{height}  {target.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
