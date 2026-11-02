"""Scripts bundled with the project skills in .claude/skills/.

They live beside their SKILL.md rather than in scripts/, so they are loaded by
path here instead of through the scripts/ entry conftest.py puts on sys.path.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, datetime
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / ".claude" / "skills"


def load(relative: str):
    path = SKILLS / relative
    spec = importlib.util.spec_from_file_location(f"skill_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses look the module up by name while the class is being built.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check_message = load("deliver/scripts/check_message.py")
manifest_report = load("snapshot-doctor/scripts/manifest_report.py")

COMMIT = """\
ci: tighten the exit-node snapshot run and document its setup

- Record the day as failed at once when a dispatched run finds the
  exit node offline.
- Skip the dispatch in trigger_snapshot.ps1 before 21:00 Taipei time.

Assisted-by: Claude <noreply@anthropic.com>
"""

PR = """\
## Summary

Follow-up to #34.

## Commits

- ci: tighten the exit-node snapshot run and document its setup

## Changes

- `scripts/trigger_snapshot.ps1`: does nothing before 21:00 Taipei time.

## Post-merge checks

- [ ] The 21:00 run stores the snapshot.
"""


def errors_of(text: str) -> list[str]:
    return check_message.check_commit(text)[0]


def test_a_well_formed_commit_passes() -> None:
    assert check_message.check_commit(COMMIT) == ([], [])


def test_title_needs_a_known_prefix_and_no_period() -> None:
    errors = errors_of(COMMIT.replace("ci: tighten", "update: tighten", 1))
    assert any("title must start" in e for e in errors)
    errors = errors_of(COMMIT.replace("its setup\n", "its setup.\n", 1))
    assert any("period" in e for e in errors)


def test_a_scoped_prefix_is_accepted() -> None:
    assert errors_of(COMMIT.replace("ci:", "docs(readme):", 1)) == []


def test_line_two_must_be_blank() -> None:
    text = COMMIT.replace("setup\n\n- Record", "setup\n- Record", 1)
    assert any("line 2 must be blank" in e for e in errors_of(text))


def test_lines_over_72_characters_fail() -> None:
    text = COMMIT.replace("offline.", "offline " + "x" * 70 + ".", 1)
    assert any("over 72" in e for e in errors_of(text))


def test_trailer_is_required_and_co_authored_by_is_rejected() -> None:
    no_trailer = COMMIT.replace("\nAssisted-by: Claude <noreply@anthropic.com>\n", "")
    assert any("Assisted-by" in e for e in errors_of(no_trailer))
    co_author = COMMIT.replace(
        "Assisted-by: Claude", "Co-Authored-By: Claude <x@y>\nAssisted-by: Claude"
    )
    assert any("Co-Authored-By" in e for e in errors_of(co_author))


def test_bullets_end_with_a_period_and_prose_is_rejected() -> None:
    assert any("period" in e for e in errors_of(COMMIT.replace("time.\n", "time\n", 1)))
    prose = COMMIT.replace("- Skip the dispatch", "Then skip the dispatch", 1)
    assert any("not a bullet" in e for e in errors_of(prose))


def test_one_line_of_preamble_is_allowed() -> None:
    text = COMMIT.replace("setup\n\n- Record", "setup\n\nAfter #34:\n- Record", 1)
    assert errors_of(text) == []


def test_work_item_codes_and_notes_paths_are_rejected() -> None:
    assert any("work-item" in e for e in errors_of(COMMIT.replace("offline.", "offline (F7).")))
    assert any("work-item" in e for e in errors_of(COMMIT.replace("offline.", "per patch A.")))
    assert any(".notes/" in e for e in errors_of(COMMIT.replace("offline.", "see .notes/x.")))
    # Not codes: E2E, and pull requests cited by number.
    assert errors_of(COMMIT.replace("offline.", "offline in E2E, see #34.")) == []


def test_cjk_text_is_a_warning_not_an_error() -> None:
    errors, warnings = check_message.check_commit(COMMIT.replace("offline.", "offline (臺灣)."))
    assert errors == [] and warnings


def test_crlf_and_bom_are_rejected() -> None:
    raw = COMMIT.encode("utf-8")
    assert check_message.check_bytes(raw) == []
    assert check_message.check_bytes(raw.replace(b"\n", b"\r\n"))
    assert check_message.check_bytes(b"\xef\xbb\xbf" + raw)


def test_a_well_formed_pr_body_passes() -> None:
    assert check_message.check_pr(PR) == ([], [])


def test_pr_sections_must_be_the_four_in_order() -> None:
    swapped = PR.replace("## Commits", "## Tmp").replace("## Changes", "## Commits")
    assert check_message.check_pr(swapped.replace("## Tmp", "## Changes"))[0]
    assert check_message.check_pr(PR.replace("## Post-merge checks", "## Checks"))[0]


def test_pr_body_rejects_generated_with_and_long_lines() -> None:
    generated = PR + "\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
    assert len(check_message.check_pr(generated)[0]) == 2
    assert any("over 80" in e for e in check_message.check_pr(PR + "x" * 81 + "\n")[0])
    # Ordinary prose that happens to say "generated with" is fine.
    prose = PR.replace("Follow-up to #34.", "Data generated with build_all.py.")
    assert check_message.check_pr(prose) == ([], [])


def test_check_file_dispatches_on_the_extension(tmp_path) -> None:
    (tmp_path / "msg1.txt").write_bytes(COMMIT.encode())
    (tmp_path / "pr1.md").write_bytes(PR.encode())
    assert check_message.main([str(tmp_path / "msg1.txt"), str(tmp_path / "pr1.md")]) == 0
    (tmp_path / "msg2.txt").write_bytes(PR.encode())
    assert check_message.main([str(tmp_path / "msg2.txt")]) == 1


MANIFEST = """\
date,status,rows,bytes,sha256,fetched_at_utc
2026-10-20,stored,8553,2978548,aa,2026-10-20T03:11:21Z
2026-10-21,stored,8594,2991474,bb,2026-10-21T03:06:25Z
2026-10-22,failed,0,0,,2026-10-22T03:14:46Z
2026-10-23,unchanged,8594,2991474,bb,2026-10-23T13:05:00Z
2026-10-25,failed,0,0,,2026-10-26T05:48:14Z
"""


def test_failed_rows_say_who_wrote_them() -> None:
    rows = {row.day: row for row in manifest_report.parse(MANIFEST)}
    assert rows[date(2026, 10, 22)].recorded_by.startswith("run")
    assert rows[date(2026, 10, 25)].recorded_by.startswith("watchdog")
    assert rows[date(2026, 10, 23)].recorded_by == "fetch"


def test_streak_and_missing_days() -> None:
    rows = manifest_report.parse(MANIFEST)
    assert [row.day.day for row in manifest_report.streak(rows)] == [22, 23, 25]
    assert manifest_report.missing(rows, date(2026, 10, 27)) == [
        date(2026, 10, 24),
        date(2026, 10, 26),
    ]


def test_report_summarizes_freshness_and_gaps() -> None:
    rows = manifest_report.parse(MANIFEST)
    now = datetime(2026, 10, 26, 10, 0, tzinfo=manifest_report.TAIPEI)
    text = manifest_report.report(rows, now)
    assert "last stored: 2026-10-21 (5 day(s) ago" in text
    assert "not stored since: 2026-10-22 (3 row(s): 2 failed, 1 unchanged)" in text
    assert "days with no row: 2026-10-24" in text
    assert "only yesterday is missing" not in text
    assert "today (2026-10-26) has no row yet: expected after 21:00" in text


def test_report_calls_a_missing_yesterday_normal_in_the_morning() -> None:
    rows = [row for row in manifest_report.parse(MANIFEST) if row.day <= date(2026, 10, 23)]
    now = datetime(2026, 10, 25, 9, 0, tzinfo=manifest_report.TAIPEI)
    text = manifest_report.report(rows, now)
    assert "days with no row: 2026-10-24" in text
    assert "only yesterday is missing" in text


def test_report_on_an_empty_manifest() -> None:
    text = manifest_report.report(
        manifest_report.parse("date,status,rows,bytes,sha256,fetched_at_utc\n"),
        datetime(2026, 10, 26, tzinfo=manifest_report.TAIPEI),
    )
    assert "manifest is empty" in text
