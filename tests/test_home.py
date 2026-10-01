"""The home page's figures, computed in Python the way the page used to.

home.json replaced counts the page took over the whole roster. A figure that
moved by one in the move would look right and be wrong, so the rules the page
applied - rounding, band edges, tie order - are pinned here.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import build_home as bh

ROOT = Path(__file__).resolve().parents[1]


def animal(ident: str, kind: str = "狗", created: str = "2026-01-01", **fields) -> dict:
    return {
        "id": ident,
        "kind": kind,
        "created": created,
        "shelter": "s1",
        "group": "mixed",
        "variety": "混種犬",
        "body": "SMALL",
        "age": "ADULT",
    } | fields


SHELTERS = {
    "snapshot_date": "2026-10-01",
    "kinds": ["狗", "貓", "其他"],
    "shelters": [{"id": "s1", "county": "臺南市"}, {"id": "s2", "county": "雲林縣"}],
}


class TestMedian:
    def test_empty_input_has_no_median(self):
        assert bh.median([]) is None

    def test_rounds_an_even_midpoint_half_up_like_the_page(self):
        # Math.round(2.5) is 3; Python's round(2.5) is 2.
        assert bh.median([2, 3]) == 3
        assert bh.median([1, 2, 3, 4]) == 3


class TestDays:
    def test_counts_to_the_snapshot(self):
        assert bh.days_between("2026-09-30", date(2026, 10, 1)) == 1

    def test_a_missing_build_date_has_no_days(self):
        assert bh.days_between("", date(2026, 10, 1)) is None

    def test_band_edges(self):
        assert bh.band_of(30) == "0-30"
        assert bh.band_of(31) == "31-90"
        assert bh.band_of(730) == "1-2y"
        assert bh.band_of(731) == "2-5y"
        assert bh.band_of(10_000) == "5y+"
        assert bh.band_of(-1) is None
        assert bh.band_of(None) is None

    def test_bands_match_the_page(self):
        # The page owns the labels and the URL keys; a drifted edge here would
        # put a wrong count beside a chip that filters correctly.
        source = (ROOT / "src" / "lib" / "animals.ts").read_text(encoding="utf-8")
        pattern = r"key: '([^']+)', label: '[^']*', min: (\d+), max: (\d+|null)"
        page = tuple(
            (key, int(low), None if high == "null" else int(high))
            for key, low, high in re.findall(pattern, source)
        )
        assert page == bh.DAY_BANDS


class TestBuild:
    def test_ties_keep_roster_order(self):
        # Array.prototype.sort is stable, so the page kept file order on ties.
        animals = [
            animal("a", created="2020-01-01"),
            animal("b", created="2020-01-01"),
            animal("c", created="2019-01-01"),
        ]
        payload = bh.build(SHELTERS, animals)
        assert [item["id"] for item in payload["longest"]] == ["c", "a", "b"]
        assert [item["id"] for item in payload["newest"]["狗"]] == ["a", "b", "c"]

    def test_an_animal_without_a_build_date_is_counted_but_never_shown(self):
        animals = [animal("a"), animal("b", created="")]
        payload = bh.build(SHELTERS, animals)
        assert payload["roster"]["count"] == 2
        assert payload["kinds"]["狗"]["count"] == 2
        assert sum(payload["kinds"]["狗"]["bands"].values()) == 1
        assert [item["id"] for item in payload["longest"]] == ["a"]

    def test_counts_per_kind(self):
        animals = [
            animal("a", shelter="s1"),
            animal("b", shelter="s2", age="CHILD", group="breed", variety="柴犬"),
            animal("c", kind="貓", variety="", shelter="s9"),
        ]
        dogs = bh.build(SHELTERS, animals)["kinds"]["狗"]
        cats = bh.build(SHELTERS, animals)["kinds"]["貓"]
        assert dogs["counties"] == {"臺南市": 1, "雲林縣": 1}
        assert dogs["varieties"] == {"混種犬": 1, "柴犬": 1}
        assert dogs["age"] == {"ADULT": 1, "CHILD": 1}
        assert dogs["mixed"] == 1
        # An unknown shelter and a blank variety stay as '', for the page to
        # filter out or relabel exactly as it did before.
        assert cats["counties"] == {"": 1}
        assert cats["varieties"] == {"": 1}

    def test_every_kind_is_present_even_when_empty(self):
        payload = bh.build(SHELTERS, [animal("a")])
        assert payload["kinds"]["其他"]["count"] == 0
        assert payload["newest"]["貓"] == []
