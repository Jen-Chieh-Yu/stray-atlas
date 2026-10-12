"""check_freshness.py: the trailing run of days that stored no snapshot."""

from __future__ import annotations

import check_freshness


def rows(*statuses: str) -> list[dict[str, str]]:
    return [{"date": f"2026-10-{day:02d}", "status": s} for day, s in enumerate(statuses, 1)]


def test_streak_is_empty_when_the_newest_row_stored() -> None:
    assert check_freshness.stale_streak(rows("unchanged", "unchanged", "stored")) == []


def test_streak_counts_back_to_the_last_stored_row() -> None:
    streak = check_freshness.stale_streak(rows("unchanged", "stored", "unchanged", "unchanged"))
    assert [row["date"] for row in streak] == ["2026-10-03", "2026-10-04"]


def test_failed_rows_count_toward_the_streak() -> None:
    streak = check_freshness.stale_streak(rows("stored", "unchanged", "failed", "unchanged"))
    assert len(streak) == 3


def test_streak_covers_a_manifest_with_no_stored_row() -> None:
    assert len(check_freshness.stale_streak(rows("failed", "unchanged"))) == 2
    assert check_freshness.last_stored(rows("failed", "unchanged")) is None


def test_main_fails_at_the_threshold(tmp_path, monkeypatch) -> None:
    manifest = tmp_path / "_manifest.csv"
    manifest.write_text(
        "date,status,rows,bytes,sha256,fetched_at_utc\n"
        "2026-10-01,stored,1,1,a,\n"
        "2026-10-02,unchanged,1,1,a,\n"
        "2026-10-03,unchanged,1,1,a,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_freshness, "MANIFEST_PATH", manifest)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr("sys.argv", ["check_freshness.py"])
    assert check_freshness.main() == 0

    with manifest.open("a", encoding="utf-8") as handle:
        handle.write("2026-10-04,unchanged,1,1,a,\n")
    assert check_freshness.main() == 1
