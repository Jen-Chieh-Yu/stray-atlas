"""The hand-kept visitor information in data/reference/shelter-info.json.

Nothing in the daily feed checks this file: a typo in a key or a link would
sit there unnoticed, attached to no shelter or sending visitors to a dead
page. So the build checks it, and these tests pin what the check catches.
"""

from __future__ import annotations

import json

import pytest

import build_shelters as bs

TAIPEI = bs.shelter_id("臺北市動物之家")
KINMEN = bs.shelter_id("金門縣動物收容中心")


def entry(name: str, **fields) -> dict:
    return {
        "name": name,
        "hours": "週二至週日 10:00–16:00",
        "visit": "unstated",
        "sources": [{"url": "https://example.gov.tw/a", "title": "公告"}],
        "checked": "2026-10-12",
    } | fields


class TestTheFile:
    def test_every_entry_checks_out(self):
        info = bs.load_info()
        assert len(info) == 37

    def test_a_shelter_listed_twice_shows_the_other_entry_under_its_own_note(self):
        info = bs.load_info()
        old = info[bs.shelter_id("苗栗縣生態保育教育中心(動物收容所)")]
        new = info[bs.shelter_id("苗栗縣動物保護教育園區")]
        assert old["hours"] == new["hours"]
        assert old["sources"] == new["sources"]
        assert "同一處" in old["note"]
        assert "note" not in new


class TestCheck:
    def test_a_good_entry_has_no_problems(self):
        assert bs.check_info({TAIPEI: entry("臺北市動物之家")}) == []

    def test_the_key_must_be_the_id_of_the_name(self):
        problems = bs.check_info({KINMEN: entry("臺北市動物之家")})
        assert any("not the id" in problem for problem in problems)

    def test_links_must_be_https(self):
        bad = entry("臺北市動物之家", adoption={"url": "http://example.gov.tw/", "title": "須知"})
        problems = bs.check_info({TAIPEI: bad})
        assert any("https" in problem for problem in problems)

    def test_visit_is_one_of_three_or_null(self):
        assert bs.check_info({TAIPEI: entry("臺北市動物之家", visit=None)}) == []
        problems = bs.check_info({TAIPEI: entry("臺北市動物之家", visit="maybe")})
        assert any("visit" in problem for problem in problems)

    def test_no_hours_needs_a_note(self):
        problems = bs.check_info({TAIPEI: entry("臺北市動物之家", hours=None)})
        assert any("note" in problem for problem in problems)
        assert bs.check_info({TAIPEI: entry("臺北市動物之家", hours=None, note="查不到")}) == []

    def test_same_as_must_point_at_an_entry_with_data_and_say_why(self):
        twin = {"name": "金門縣動物收容中心", "same_as": TAIPEI, "checked": "2026-10-12"}
        problems = bs.check_info({TAIPEI: entry("臺北市動物之家"), KINMEN: twin})
        assert any("needs a note" in problem for problem in problems)
        loop = twin | {"same_as": KINMEN, "note": "同一處"}
        problems = bs.check_info({KINMEN: loop})
        assert any("own data" in problem for problem in problems)

    def test_a_bad_file_stops_the_build(self, tmp_path):
        path = tmp_path / "shelter-info.json"
        bad = {"shelters": {TAIPEI: entry("臺北市動物之家", checked="10/12")}}
        path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ValueError, match="checked"):
            bs.load_info(path)
