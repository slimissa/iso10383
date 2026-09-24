"""Ground-truth assertions on the registry.

Every value here is a fact verified against the ISO 10383 source.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "iso10383.json").read_text(encoding="utf-8"))
BY_MIC = {m["mic"]: m for m in DATA["mics"]}


@pytest.mark.parametrize("mic,want_type,want_country", [
    ("XNYS", "OPERATING", "US"),
    ("XLON", "OPERATING", "GB"),
    ("XTKS", "SEGMENT",   "JP"),
    ("XPAR", "OPERATING", "FR"),
])
def test_spot_check(mic, want_type, want_country):
    m = BY_MIC.get(mic)
    assert m is not None, f"{mic} missing"
    assert m["mic_type"] == want_type
    assert m["country_code"] == want_country


def test_counts_add_up():
    c = DATA["meta"]["counts"]
    assert c["operating"] + c["segment"] == c["total"]
    assert c["active"] + c["updated"] + c["expired"] == c["total"]
    assert c["total"] == len(DATA["mics"])


def test_counts_within_expected_range():
    c = DATA["meta"]["counts"]
    assert c["operating"] >= 1500
    assert c["segment"] >= 1000
    assert c["total"] >= 2500


def test_meta_fields_present():
    meta = DATA["meta"]
    for k in ("version", "updated", "source_snapshot", "source_url",
              "source_hash", "counts", "broken_chains"):
        assert k in meta, f"meta missing {k}"
    assert meta["source_hash"].startswith("sha256:")
    assert len(meta["source_hash"]) == 71


def test_broken_chains_empty():
    assert DATA["meta"]["broken_chains"] == []


def test_market_categories_are_iso_codes():
    allowed = {"ATSS", "APPA", "ARMS", "CTPS", "CASP", "DCMS", "IDQS",
               "MLTF", "NSPD", "OTFS", "OTHR", "RMOS", "RMKT", "SEFS",
               "SINT", "TRFS"}
    seen = {m["market_category"] for m in DATA["mics"]
            if m.get("market_category")}
    assert seen <= allowed, f"unknown categories: {seen - allowed}"


def test_status_values_closed():
    allowed = {"ACTIVE", "UPDATED", "EXPIRED"}
    seen = {m["status"] for m in DATA["mics"]}
    assert seen <= allowed


def test_mic_type_values_closed():
    allowed = {"OPERATING", "SEGMENT"}
    seen = {m["mic_type"] for m in DATA["mics"]}
    assert seen <= allowed
