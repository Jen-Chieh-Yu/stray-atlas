"""Grading, and the two rules that keep it honest.

The page grades recording practice, and a grade is an assertion about a
county. The threshold comparisons and the small-sample rule are therefore the
two places where a one-character slip would put a claim on the site that the
data does not support.
"""

from __future__ import annotations

import build_quality as bq


def row(
    *,
    photo: str = "x.jpg",
    district: bool | None = True,
    sterilization: str = "T",
    opendate: str = "2026-01-01",
) -> dict:
    return {
        "album_file": photo,
        "district_verified": district,
        "animal_sterilization": sterilization,
        "animal_opendate": opendate,
    }


SNAPSHOT = "2026-09-18"


class TestGrade:
    def test_the_threshold_itself_passes(self):
        # "優 ≥ 90%" is printed on the page, so 90% has to be 優. An
        # accidental > would silently demote whichever county sits on it.
        assert bq.grade(0.90, 0.90, 0.70) == "good"
        assert bq.grade(0.70, 0.90, 0.70) == "fair"

    def test_just_below_a_threshold_drops_a_level(self):
        assert bq.grade(0.8999, 0.90, 0.70) == "fair"
        assert bq.grade(0.6999, 0.90, 0.70) == "poor"

    def test_no_value_is_not_a_bad_value(self):
        assert bq.grade(None, 0.90, 0.70) == "na"


class TestGraded:
    def test_a_small_county_gets_figures_but_no_grades(self):
        # DESIGN.md 13: below this many rows a percentage swings several
        # points when one animal leaves, so the grade is withheld and the
        # figure is still shown.
        scores = {key: 1.0 for key, *_ in bq.METRICS}
        grades = bq.graded(scores, bq.MIN_ROWS - 1)
        assert set(grades.values()) == {"na"}

    def test_at_the_row_threshold_grading_starts(self):
        scores = {key: 1.0 for key, *_ in bq.METRICS}
        grades = bq.graded(scores, bq.MIN_ROWS)
        assert set(grades.values()) == {"good"}


class TestScore:
    def test_photo_coverage_counts_non_empty_values(self):
        scores = bq.score([row(), row(photo=""), row(), row()], SNAPSHOT)
        assert scores["photo"] == 0.75

    def test_only_a_verified_district_counts_as_locatable(self):
        # False and None are both "not locatable"; neither may be counted.
        scores = bq.score([row(), row(district=False), row(district=None), row()], SNAPSHOT)
        assert scores["place"] == 0.5

    def test_sterilisation_counts_a_recorded_answer_either_way(self):
        # T and F are both answers. N is the absence of one, which is what
        # this metric measures.
        scores = bq.score(
            [row(sterilization="T"), row(sterilization="F"), row(sterilization="N")], SNAPSHOT
        )
        assert scores["sterilization"] == round(2 / 3, 4)

    def test_a_blank_or_future_opening_date_is_not_valid(self):
        # The sentinel is already nulled by the cleaner, so a blank here is
        # either a genuine gap or that sentinel. A date after the snapshot is
        # recorded as invalid but never corrected: it may be a real scheduled
        # release.
        scores = bq.score(
            [row(), row(opendate=""), row(opendate="2099-01-01"), row()], SNAPSHOT
        )
        assert scores["opendate"] == 0.5

    def test_the_snapshot_day_itself_is_valid(self):
        assert bq.score([row(opendate=SNAPSHOT)], SNAPSHOT)["opendate"] == 1.0

    def test_an_empty_county_scores_zero_rather_than_raising(self):
        assert bq.score([], SNAPSHOT) == {key: 0.0 for key, *_ in bq.METRICS}


class TestMetrics:
    def test_every_metric_has_an_ordered_pair_of_thresholds(self):
        for key, label, description, good, fair in bq.METRICS:
            assert good > fair, key
            assert 0 < fair < good <= 1, key
            assert label and description, key

    def test_score_returns_exactly_the_declared_metrics(self):
        # The payload's metric list and the scoring function must not drift:
        # the page reads the thresholds from one and the values from the other.
        assert set(bq.score([row()], SNAPSHOT)) == {key for key, *_ in bq.METRICS}
