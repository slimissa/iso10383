"""D3 invariants: operating MICs self-reference; segments do not.

Chains of any depth terminate at an operating MIC.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "iso10383.json").read_text(encoding="utf-8"))
BY_MIC = {m["mic"]: m for m in DATA["mics"]}


def test_operating_mics_self_reference():
    for m in DATA["mics"]:
        if m["mic_type"] == "OPERATING":
            assert m["operating_mic"] == m["mic"], (
                f"{m['mic']}: operating_mic = {m['operating_mic']}"
            )


def test_segments_do_not_self_reference():
    for m in DATA["mics"]:
        if m["mic_type"] == "SEGMENT":
            assert m["operating_mic"] != m["mic"], (
                f"{m['mic']}: segment self-references"
            )


def test_every_segment_chain_terminates_at_operating():
    max_depth = 8
    for m in DATA["mics"]:
        if m["mic_type"] != "SEGMENT":
            continue
        seen = {m["mic"]}
        cur = m["operating_mic"]
        depth = 0
        while depth < max_depth:
            assert cur not in seen, f"{m['mic']}: cycle via {cur}"
            seen.add(cur)
            parent = BY_MIC.get(cur)
            assert parent is not None, f"{m['mic']}: missing parent {cur}"
            if parent["mic_type"] == "OPERATING":
                break
            cur = parent["operating_mic"]
            depth += 1
        else:
            raise AssertionError(f"{m['mic']}: chain deeper than {max_depth}")


def test_no_duplicate_mics():
    seen = set()
    for m in DATA["mics"]:
        assert m["mic"] not in seen, f"duplicate {m['mic']}"
        seen.add(m["mic"])


def test_at_least_one_three_level_chain():
    # Phase 1 finding: XEAS -> XEQT -> XBER
    depth_gt_2 = 0
    for m in DATA["mics"]:
        if m["mic_type"] != "SEGMENT":
            continue
        cur = m["operating_mic"]
        depth = 1
        while BY_MIC[cur]["mic_type"] == "SEGMENT" and depth < 8:
            cur = BY_MIC[cur]["operating_mic"]
            depth += 1
        if depth >= 2:
            depth_gt_2 += 1
    assert depth_gt_2 > 0, "expected at least one multi-level chain"
