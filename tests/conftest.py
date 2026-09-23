"""Make scripts/ importable, the same way the scripts import each other.

scripts/*.py put their own directory on sys.path so `from common import ...`
works with no install step (see scripts/common.py). The tests import the same
modules, so they need the same path.

There is no pyproject.toml and no packaging: `python -m pytest` from the
repository root is the whole story. The scripts themselves stay standard
library only; pytest is a development dependency of the tests, not of the
pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
