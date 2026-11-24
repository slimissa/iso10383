"""Vendoring metadata of every registry snapshot (qlf-sentinel client contract CC-2).

For each tools/<s>_snapshot.meta.json with <s> in the four QuantOS registry
names, the "meta" object carries source, source_version, vendored_at,
review_by and refresh_cadence; review_by is vendored_at plus one cadence
period; every key present both at the top level and in "meta" has the same
value in both; and meta.source_version is the snapshot's own source_version.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from cadence import CADENCE_MONTHS, add_months  # noqa: E402  (the rule lives once, in tools/cadence.py)
REGISTRIES = ("iso4217", "iso3166", "iso10383", "exchange_calendar")
PRESENT = [s for s in REGISTRIES if (TOOLS / f"{s}_snapshot.meta.json").is_file()]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _iso_date(v):
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def problems(meta_path: Path, snapshot_path: Path) -> list[str]:
    """Every rule the meta file breaks; empty when it is valid."""
    doc = json.loads(meta_path.read_text(encoding="utf-8"))
    meta = doc.get("meta")
    if not isinstance(meta, dict):
        return ["no meta object"]
    out = []
    # (a) the five keys and their types
    for k in ("source", "source_version", "vendored_at", "review_by", "refresh_cadence"):
        if k not in meta:
            out.append(f"meta lacks {k}")
    if "source" in meta and not isinstance(meta["source"], str):
        out.append("meta.source is not a string")
    if "source_version" in meta and not (isinstance(meta["source_version"], str)
                                         and SEMVER.match(meta["source_version"])):
        out.append("meta.source_version is not SemVer")
    for k in ("vendored_at", "review_by"):
        if k in meta and _iso_date(meta[k]) is None:
            out.append(f"meta.{k} is not a YYYY-MM-DD date")
    # (b) cadence vocabulary
    cad = meta.get("refresh_cadence")
    if "refresh_cadence" in meta and cad not in CADENCE_MONTHS:
        out.append(f"meta.refresh_cadence {cad!r} not in {sorted(CADENCE_MONTHS)}")
    # (c) review_by = vendored_at + 1 period
    va, rb = _iso_date(meta.get("vendored_at")), _iso_date(meta.get("review_by"))
    if va and rb and cad in CADENCE_MONTHS:
        want = add_months(va, CADENCE_MONTHS[cad])
        if rb != want:
            out.append(f"meta.review_by {rb} != vendored_at + 1 {cad} period ({want})")
    # (d) copies at both levels agree
    for k in sorted(set(meta) & (set(doc) - {"meta"})):
        if doc[k] != meta[k]:
            out.append(f"{k}: top level {doc[k]!r} != meta {meta[k]!r}")
    # (e) the snapshot's own version
    snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if meta.get("source_version") != snap.get("source_version"):
        out.append(f"meta.source_version {meta.get('source_version')!r} != "
                   f"snapshot source_version {snap.get('source_version')!r}")
    return out


def test_at_least_one_registry_snapshot_is_present():
    assert PRESENT, "no tools/<registry>_snapshot.meta.json found"


@pytest.mark.parametrize("stem", PRESENT)
def test_meta_file_satisfies_cc2_and_the_cadence_rule(stem):
    assert problems(TOOLS / f"{stem}_snapshot.meta.json", TOOLS / f"{stem}_snapshot.json") == []


@pytest.mark.parametrize("start, n, end", [
    ("2026-11-23", 3, "2027-02-23"),
    ("2026-11-23", 12, "2027-11-23"),
    ("2026-11-30", 3, "2027-02-28"),   # clamped
    ("2027-11-30", 3, "2028-02-29"),   # clamped, leap year
    ("2026-01-31", 1, "2026-02-28"),   # clamped
    ("2026-12-15", 1, "2027-01-15"),   # year rollover
])
def test_add_months(start, n, end):
    assert add_months(date.fromisoformat(start), n) == date.fromisoformat(end)


GOOD = {
    "source": "x", "source_version": "1.2.3", "vendored_at": "2026-11-30",
    "meta": {"source": "x", "source_version": "1.2.3", "vendored_at": "2026-11-30",
             "review_by": "2027-02-28", "refresh_cadence": "quarterly"},
}


def _write(tmp_path, doc, snapshot_version="1.2.3"):
    m, s = tmp_path / "x_snapshot.meta.json", tmp_path / "x_snapshot.json"
    m.write_text(json.dumps(doc), encoding="utf-8")
    s.write_text(json.dumps({"source_version": snapshot_version}), encoding="utf-8")
    return m, s


def test_good_fixture_passes_including_month_end_clamp(tmp_path):
    assert problems(*_write(tmp_path, GOOD)) == []


def _bad(change):
    doc = json.loads(json.dumps(GOOD))
    change(doc)
    return doc


@pytest.mark.parametrize("doc, snapshot_version, expect", [
    (_bad(lambda d: d.pop("meta")), "1.2.3", "no meta object"),
    (_bad(lambda d: d["meta"].pop("refresh_cadence")), "1.2.3", "meta lacks refresh_cadence"),
    (_bad(lambda d: d["meta"].update(source=7)), "1.2.3", "meta.source is not a string"),
    (_bad(lambda d: d["meta"].update(source_version="1.2")), "1.2.3", "meta.source_version is not SemVer"),
    (_bad(lambda d: d["meta"].update(review_by="2027-02-30")), "1.2.3", "meta.review_by is not a YYYY-MM-DD date"),
    (_bad(lambda d: d["meta"].update(refresh_cadence="weekly")), "1.2.3", "not in ['monthly', 'quarterly', 'yearly']"),
    (_bad(lambda d: d["meta"].update(review_by="2027-03-02")), "1.2.3", "!= vendored_at + 1 quarterly period (2027-02-28)"),
    (_bad(lambda d: d["meta"].update(refresh_cadence="yearly")), "1.2.3", "!= vendored_at + 1 yearly period (2027-11-30)"),
    (_bad(lambda d: d.update(vendored_at="2026-11-29")), "1.2.3", "vendored_at: top level '2026-11-29' != meta '2026-11-30'"),
    (GOOD, "1.2.4", "!= snapshot source_version '1.2.4'"),
], ids=["a-no-meta", "a-missing-key", "a-source-type", "a-semver", "a-date",
        "b-cadence", "c-month-end-clamp", "c-wrong-period", "d-copies-differ", "e-snapshot-version"])
def test_each_rule_is_enforced(tmp_path, doc, snapshot_version, expect):
    found = problems(*_write(tmp_path, doc, snapshot_version))
    assert any(expect in p for p in found), found
