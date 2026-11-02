#!/usr/bin/env python3
"""Check a commit message or pull request body against CLAUDE.md 6.1 and 6.4-6.6.

    python .claude/skills/deliver/scripts/check_message.py .git/msg92.txt .git/pr92.md

A .txt file is checked as a commit message, a .md file as a pull request body.
Errors exit 1; warnings are printed but leave the exit status at 0, for things
a person should look at rather than a rule that is always right.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TRAILER = "Assisted-by: Claude <noreply@anthropic.com>"
PREFIXES = ("feat", "fix", "docs", "chore", "refactor", "ci", "data")
TITLE = re.compile(rf"^(?:{'|'.join(PREFIXES)})(?:\([a-z0-9-]+\))?: \S")
COMMIT_WIDTH = 72
PR_WIDTH = 80
PR_SECTIONS = ("## Summary", "## Commits", "## Changes", "## Post-merge checks")

# AI attribution belongs in the Assisted-by trailer only (6.1, 6.6).
FORBIDDEN = (
    (r"(?i)co-authored-by:", "use the Assisted-by trailer, not Co-Authored-By (6.1)"),
    (r"(?i)generated with \[?claude", "no 'Generated with Claude' line; use Assisted-by (6.6)"),
    (r"(?i)claude-session", "no Claude-Session link (6.1)"),
    (r"\.notes/", "readers cannot see .notes/; describe the change instead (6.4)"),
)
# Item codes from the private work list in .notes/ (A, B1-B5, F7, patch A).
WORK_ITEM = re.compile(r"\b(?:patch [A-Z]\b|[A-F][1-9][0-9]?\b)")
CJK = re.compile(r"[　-鿿＀-￯]")


def check_bytes(raw: bytes) -> list[str]:
    errors = []
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append("file starts with a UTF-8 BOM; write it without one")
    if b"\r" in raw:
        errors.append("file has CR line endings; write it with LF only")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as error:
        errors.append(f"file is not UTF-8: {error}")
    return errors


def check_common(lines: list[str], width: int) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    text = "\n".join(lines)
    for pattern, reason in FORBIDDEN:
        if re.search(pattern, text):
            errors.append(reason)
    for number, line in enumerate(lines, 1):
        if len(line) > width:
            errors.append(f"line {number} is {len(line)} characters, over {width}")
        for match in WORK_ITEM.finditer(line):
            errors.append(
                f"line {number}: '{match.group()}' looks like a work-item code (6.4); "
                "describe the change, cite pull requests as #NN"
            )
        if CJK.search(line):
            warnings.append(f"line {number} has CJK text; commits and PRs are in English (5)")
    return errors, warnings


def check_commit(text: str) -> tuple[list[str], list[str]]:
    lines = text.rstrip("\n").split("\n")
    errors, warnings = check_common(lines, COMMIT_WIDTH)

    title = lines[0]
    if not TITLE.match(title):
        errors.append(
            f"title must start with one of {', '.join(PREFIXES)}, an optional (scope), "
            "then ': ' (6.2)"
        )
    if title.rstrip().endswith("."):
        errors.append("title must not end with a period (6.4)")
    if len(lines) < 2 or lines[1] != "":
        errors.append("line 2 must be blank, or git reads the body as part of the title")

    if lines[-1] != TRAILER:
        errors.append(f"last line must be exactly '{TRAILER}' (6.1)")
    elif len(lines) < 3 or lines[-2] != "":
        errors.append("leave a blank line before the Assisted-by trailer")

    body = lines[2:-2] if lines[-1] == TRAILER else lines[2:]
    errors += check_bullets(body)
    return errors, warnings


def check_bullets(body: list[str]) -> list[str]:
    """Body is bullets ('- ', continuation lines indented two spaces), each
    ending with a period, after at most one line of preamble (6.4)."""
    errors = []
    items: list[list[tuple[int, str]]] = []
    preamble = 0
    for number, line in enumerate(body, 3):
        if line == "":
            continue
        if line.startswith("- "):
            items.append([(number, line)])
        elif line.startswith("  ") and items:
            items[-1].append((number, line))
        elif not items:
            preamble += 1
            if preamble > 1:
                errors.append(f"line {number}: more than one line of preamble; use bullets")
        else:
            errors.append(f"line {number}: not a bullet ('- ') or an indented continuation")
    if not items:
        errors.append("body has no bullets; describe the change as '- ' bullets (6.4)")
    for item in items:
        number, last = item[-1]
        if not last.rstrip().endswith("."):
            errors.append(f"line {number}: end each bullet with a period (6.4)")
    return errors


def check_pr(text: str) -> tuple[list[str], list[str]]:
    lines = text.rstrip("\n").split("\n")
    errors, warnings = check_common(lines, PR_WIDTH)
    if "\U0001f916" in text:
        errors.append("no robot emoji line; AI is marked by Assisted-by (6.6)")
    headings = [line for line in lines if line.startswith("## ")]
    if tuple(headings) != PR_SECTIONS:
        errors.append(
            f"sections must be exactly {', '.join(PR_SECTIONS)} in that order (6.6); "
            f"found {', '.join(headings) or 'none'}"
        )
    return errors, warnings


def check_file(path: Path) -> tuple[list[str], list[str]]:
    raw = path.read_bytes()
    errors = check_bytes(raw)
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
    if path.suffix == ".md":
        more, warnings = check_pr(text)
    else:
        more, warnings = check_commit(text)
    return errors + more, warnings


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    failed = False
    for name in argv:
        path = Path(name)
        if not path.is_file():
            print(f"{name}: no such file", file=sys.stderr)
            return 2
        errors, warnings = check_file(path)
        for message in errors:
            print(f"{name}: error: {message}")
        for message in warnings:
            print(f"{name}: warning: {message}")
        if not errors:
            print(f"{name}: ok" + (f" ({len(warnings)} warning(s))" if warnings else ""))
        failed = failed or bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
