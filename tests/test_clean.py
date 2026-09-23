"""The cleaning rules, on synthetic rows.

Nothing here reads data/raw/. The snapshot changes every morning; a test that
reads it would be measuring today's weather rather than the code. Each case is
a rule that was decided once and must keep holding — several of them are rules
that were got wrong first and fixed, which is exactly why they are pinned.
"""

from __future__ import annotations

import json

import clean


class TestVarietyGroup:
    """PROJECT_BRIEF 4.2 and its 2026-09-03 correction.

    The original pass counted 混種犬 and 混種狗 as different things and folded
    其他 into pedigree, which moved the pedigree median by 16 days. Both
    spellings and the unknown bucket are pinned here so that cannot recur.
    """

    def test_both_spellings_of_mixed_dog_are_one_group(self):
        assert clean.variety_group("混種犬") == "mixed"
        assert clean.variety_group("混種狗") == "mixed"

    def test_mixed_marker_anywhere_in_the_string_counts(self):
        assert clean.variety_group("比特犬之混種犬") == "mixed"
        assert clean.variety_group("米克斯") == "mixed"

    def test_blank_and_other_are_unknown_not_pedigree(self):
        assert clean.variety_group("") == "unknown"
        assert clean.variety_group("其他") == "unknown"

    def test_a_named_breed_is_pedigree(self):
        assert clean.variety_group("拉布拉多") == "breed"


class TestParseDate:
    def test_reads_the_date_part_of_a_timestamp(self):
        assert clean.parse_date("2026-09-18 14:30:00").isoformat() == "2026-09-18"

    def test_returns_none_rather_than_raising(self):
        assert clean.parse_date("") is None
        assert clean.parse_date("not a date") is None


class TestPercentile:
    def test_empty_input_has_no_percentile(self):
        assert clean.percentile([], 0.5) is None

    def test_picks_an_observed_value_never_an_average(self):
        # The index method is deliberate: every figure the site quotes is a
        # value some animal actually has.
        assert clean.percentile([1, 2, 3, 4], 0.5) == 3
        assert clean.percentile([1, 2, 3], 0.5) == 2

    def test_clamps_at_the_top(self):
        assert clean.percentile([1, 2, 3], 1.0) == 3


class TestUninformativeColumns:
    def test_an_all_blank_column_is_reported(self):
        rows = [{"a": "", "b": "x"}, {"a": "", "b": "y"}]
        found = clean.uninformative_columns(["a", "b"], rows)
        assert found == [{"column": "a", "reason": "all_blank", "distinct_values": 0}]

    def test_a_single_valued_column_is_reported_with_its_value(self):
        rows = [{"a": "OPEN"}, {"a": "OPEN"}]
        found = clean.uninformative_columns(["a"], rows)
        assert found[0]["reason"] == "zero_variance"
        assert found[0]["value"] == "OPEN"

    def test_blanks_do_not_count_as_a_second_value(self):
        # A column that is either blank or one constant carries no more
        # information than the constant alone, so it is still dropped. This
        # surprised me once; it is pinned so the behaviour is a decision.
        rows = [{"a": ""}, {"a": "F"}]
        assert clean.uninformative_columns(["a"], rows)[0]["reason"] == "zero_variance"

    def test_a_varying_column_survives(self):
        rows = [{"a": "1"}, {"a": "2"}]
        assert clean.uninformative_columns(["a"], rows) == []


class TestDuplicateColumns:
    def test_identical_columns_are_paired_by_preference(self):
        rows = [{"animal_update": "x", "cDate": "x"}, {"animal_update": "y", "cDate": "y"}]
        found = clean.duplicate_columns(["animal_update", "cDate"], rows, exclude=set())
        assert found == [{"dropped": "cDate", "identical_to": "animal_update"}]

    def test_columns_already_condemned_are_skipped(self):
        # Otherwise every all-blank column is a duplicate of every other one.
        rows = [{"a": "", "b": ""}, {"a": "", "b": ""}]
        assert clean.duplicate_columns(["a", "b"], rows, exclude={"a", "b"}) == []


class TestFieldLabels:
    def test_known_columns_get_their_chinese_name(self):
        labels, missing = clean.field_labels(["animal_id", "animal_foundplace"])
        assert labels["animal_id"] == "動物的流水編號"
        assert missing == []

    def test_an_unknown_column_is_named_rather_than_swallowed(self):
        # The day the source adds a column, the build log has to say so.
        labels, missing = clean.field_labels(["animal_id", "animal_brand_new"])
        assert missing == ["animal_brand_new"]
        assert "animal_brand_new" not in labels

    def test_the_reference_file_covers_every_column_in_the_live_snapshot(self):
        # Guards the pair the other way round: a column named in meta.json's
        # coverage must have a label, or the quality page prints a blank.
        meta = json.loads((clean.OUT_DIR / "meta.json").read_text(encoding="utf-8"))
        _, missing = clean.field_labels(list(meta["coverage"]))
        assert missing == []


class TestSentinelDate:
    def test_the_sentinel_is_a_placeholder_not_a_date(self):
        # PROJECT_BRIEF 4.2: 1900-01-01 would drag every date aggregate back
        # by a century. load_clean nulls it; this pins the constant it looks
        # for, which is the part a refactor could quietly change.
        assert clean.SENTINEL_DATE == "1900-01-01"
        assert clean.parse_date(clean.SENTINEL_DATE) is not None
