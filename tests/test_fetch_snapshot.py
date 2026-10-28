"""fetch_snapshot.py: recording a missed day without touching the source."""

from __future__ import annotations

import csv

import pytest

import fetch_snapshot


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_snapshot, "RAW_DIR", tmp_path)
    monkeypatch.setattr(fetch_snapshot, "MANIFEST_PATH", tmp_path / "_manifest.csv")
    monkeypatch.setattr(fetch_snapshot, "snapshot_paths", lambda: sorted(tmp_path.glob("*.csv.gz")))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    def no_download(url: str) -> bytes:
        raise AssertionError("--mark-failed must not contact the source")

    monkeypatch.setattr(fetch_snapshot, "download", no_download)
    return tmp_path


def manifest(raw_dir) -> list[dict[str, str]]:
    with (raw_dir / "_manifest.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_mark_failed_records_the_day_and_fails(raw_dir, monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["fetch_snapshot.py", "--date", "2026-10-29", "--mark-failed", "exit node offline"],
    )
    assert fetch_snapshot.main() == 1
    assert [(row["date"], row["status"]) for row in manifest(raw_dir)] == [
        ("2026-10-29", "failed")
    ]


def test_mark_failed_leaves_an_archived_day_alone(raw_dir, monkeypatch) -> None:
    (raw_dir / "2026-10-29.csv.gz").write_bytes(b"")
    monkeypatch.setattr(
        "sys.argv",
        ["fetch_snapshot.py", "--date", "2026-10-29", "--mark-failed", "exit node offline"],
    )
    assert fetch_snapshot.main() == 0


def test_mark_failed_needs_a_date(raw_dir, monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["fetch_snapshot.py", "--mark-failed", "exit node offline"])
    with pytest.raises(SystemExit):
        fetch_snapshot.main()
