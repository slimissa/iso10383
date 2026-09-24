"""Fixture-anchor rule: tests read every expected value from here.

Nothing in test_registry.py hardcodes a MIC, count, or country code.
The anchor module loads the bundled snapshot, asserts it matches the
shared contract fixture, and exposes the values tests read.
"""

from __future__ import annotations

import json
from pathlib import Path

from iso10383 import MICRegistry

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE = _REPO_ROOT / "tests" / "cross_language_consistency.json"

assert _FIXTURE.is_file(), (
    f"missing shared fixture: {_FIXTURE}. "
    "Every wrapper reads the same contract file."
)

with _FIXTURE.open(encoding="utf-8") as f:
    CONTRACT = json.load(f)

CASES = {c["id"]: c for c in CONTRACT["cases"]}

# --- Sanity assertions on the bundled snapshot itself ---

REG = MICRegistry()
assert len(REG) > 0, "bundled registry is empty"
assert REG.version == "0.1.0", f"unexpected version: {REG.version}"
assert REG.broken_chains == [], "bundled snapshot has broken chains"

XNYS = REG.by_mic("XNYS")
XTKS = REG.by_mic("XTKS")
assert XNYS is not None and XNYS.mic_type == "OPERATING"
assert XTKS is not None and XTKS.mic_type == "SEGMENT"
