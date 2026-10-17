"""Self-tests for the shared contract fixture.

The fixture drives four wrapper test suites. A typo in an expectation
key silently weakens a case in every wrapper; a duplicate id silently
drops a case. These tests validate the fixture itself, not the
wrappers.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "cross_language_consistency.json"
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))

# Keys every case may carry. A wrapper test reads only the keys it
# knows; an unknown key is ignored, so a typo like "expect_all_feild"
# makes the case weaker without failing anything.
KNOWN_KEYS = frozenset({
    "args", "id", "op",
    "expect", "expect_contains", "expect_count_min", "expect_count_max",
    "expect_all_field", "expect_all_status", "expect_all_expiration_ge",
    "expect_missing", "expect_ok", "expect_order_by",
})


def test_case_ids_are_unique():
    ids = [c["id"] for c in DATA["cases"]]
    assert len(ids) == len(set(ids)), (
        f"duplicate case ids: "
        f"{sorted(i for i in ids if ids.count(i) > 1)}"
    )


def test_every_case_has_op_and_args():
    for c in DATA["cases"]:
        assert "id" in c, c
        assert "op" in c, c
        assert "args" in c, c


def test_no_unknown_expectation_keys():
    unknown = {}
    for c in DATA["cases"]:
        bad = {k for k in c if k.startswith("expect") and k not in KNOWN_KEYS}
        if bad:
            unknown[c["id"]] = sorted(bad)
    assert not unknown, f"unknown expectation keys: {unknown}"
