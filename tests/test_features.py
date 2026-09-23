"""Quantiles, dispersion and the coat rule.

Every claim the analysis page makes about a group rests on these four
functions. They are small enough to read and easy to get subtly wrong, which
is the combination that earns a test.
"""

from __future__ import annotations

import build_features as bf


def rows(*days: int) -> list[dict]:
    return [{"days_in_shelter": day} for day in days]


class TestQuantile:
    def test_empty_input_has_no_quantile(self):
        assert bf.quantile([], 0.5) is None

    def test_returns_an_observed_value(self):
        assert bf.quantile([10, 20, 30], 0.5) == 20
        assert bf.quantile([30, 10, 20], 0.5) == 20  # order of input is irrelevant

    def test_the_ends_are_the_extremes(self):
        assert bf.quantile([10, 20, 30], 0.0) == 10
        assert bf.quantile([10, 20, 30], 1.0) == 30


class TestSummarise:
    def test_reports_the_three_quartiles_and_the_count(self):
        # Index method on 1..100: round(f x 99) picks the position, so the
        # quartiles are the 26th, 51st and 75th values rather than the
        # interpolated 25.75 / 50.5 / 75.25 another convention would give.
        summary = bf.summarise(rows(*range(1, 101)))
        assert summary["n"] == 100
        assert summary["p25_days"] == 26
        assert summary["median_days"] == 51
        assert summary["p75_days"] == 75

    def test_spread_is_a_ratio_not_a_difference(self):
        # DESIGN.md 11: on a log axis the drawn length of a quartile range is
        # P75/P25, so the figure printed beside it has to be that ratio.
        summary = bf.summarise(rows(100, 200, 300, 400))
        assert summary["iqr_ratio"] == round(summary["p75_days"] / summary["p25_days"], 2)

    def test_a_zero_lower_quartile_has_no_ratio(self):
        # An animal recorded today is 0 days in. Dividing by it would be the
        # kind of crash that only happens on the one morning it matters.
        summary = bf.summarise(rows(0, 0, 0, 10))
        assert summary["p25_days"] == 0
        assert summary["iqr_ratio"] is None

    def test_small_groups_are_flagged_not_hidden(self):
        assert bf.summarise(rows(*range(bf.SMALL_GROUP - 1)))["small_sample"] is True
        assert bf.summarise(rows(*range(bf.SMALL_GROUP)))["small_sample"] is False

    def test_an_empty_group_does_not_raise(self):
        summary = bf.summarise([])
        assert summary["n"] == 0
        assert summary["median_days"] is None
        assert summary["iqr_ratio"] is None

    def test_rows_without_a_duration_are_left_out_of_the_quantiles(self):
        summary = bf.summarise([{"days_in_shelter": None}, {"days_in_shelter": 10}])
        assert summary["n"] == 2  # the group still has two animals in it
        assert summary["median_days"] == 10


class TestHasDarkCoat:
    def test_every_spelling_containing_black_counts(self):
        # Deliberately wide: taking 黑色 alone drops the sample below what a
        # per-shelter comparison can carry (build_features.py).
        assert bf.has_dark_coat("黑色")
        assert bf.has_dark_coat("黑白色")
        assert bf.has_dark_coat("黑黃色")

    def test_other_colours_do_not(self):
        assert not bf.has_dark_coat("白色")
        assert not bf.has_dark_coat("虎斑色")
        assert not bf.has_dark_coat("")


class TestAxis:
    def test_the_axis_starts_above_zero(self):
        # The page draws these on a log scale, and log10(0) is not a number.
        assert bf.AXIS["min_days"] > 0
        assert bf.AXIS["max_days"] > bf.AXIS["min_days"]

    def test_every_tick_sits_inside_the_axis(self):
        for tick in bf.AXIS["ticks"]:
            assert bf.AXIS["min_days"] <= tick["days"] <= bf.AXIS["max_days"]
