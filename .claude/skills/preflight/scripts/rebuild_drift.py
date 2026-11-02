#!/usr/bin/env python3
"""Report public/data files that differ from HEAD in more than generated_at.

Run after `python scripts/build_all.py`. The same comparison as the "Check the
rebuild matches the committed site data" step in .github/workflows/ci.yml, so a
build-script change that was not followed by a rebuild shows up before the push
rather than as a red CI run. Read-only: it never restores or stages anything.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout


def strip(value: object) -> object:
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items() if not k.startswith("generated_at")}
    if isinstance(value, list):
        return [strip(v) for v in value]
    return value


def main() -> int:
    changed = git("diff", "--name-only", "--", "public/data").split()
    new = git("ls-files", "--others", "--exclude-standard", "--", "public/data").split()
    drift = [f"{name} (not committed)" for name in new]
    timestamp_only = []
    for name in changed:
        before = json.loads(git("show", f"HEAD:{name}"))
        after = json.loads(Path(name).read_text(encoding="utf-8"))
        (timestamp_only if strip(before) == strip(after) else drift).append(name)

    if drift:
        print("public/data differs from HEAD beyond generated_at:")
        print("\n".join(f"  {name}" for name in drift))
    if timestamp_only:
        print(f"{len(timestamp_only)} file(s) differ only in generated_at:")
        print("\n".join(f"  {name}" for name in timestamp_only))
    if not drift and not timestamp_only:
        print("public/data matches HEAD")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
