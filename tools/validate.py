"""Six-layer validator for iso10383.json.

Layers, run in order:

  1. schema         JSON Schema draft-07 (schema.json)
  2. integrity      patterns, date format, non-empty strings
  3. business       uniqueness, status/mic_type consistency,
                    operating MIC self-reference, segment not self-ref
  4. cross-ref      parent chain terminates at operating MIC;
                    country_code in iso3166_snapshot;
                    every exchange_calendar_snapshot MIC exists here
  5. ground truth   XNYS / XLON / XTKS / XPAR spot checks
  6. coverage       operating >= 1500, segment >= 1000, total >= 2500

Exit codes:
  0  pass
  1  data error
  2  usage error
  3  schema violation
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import jsonschema

MIC_RE = re.compile(r"^[A-Z0-9]{4}$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

GROUND_TRUTH = {
    "XNYS": {"mic_type": "OPERATING", "country_code": "US"},
    "XLON": {"mic_type": "OPERATING", "country_code": "GB"},
    "XTKS": {"mic_type": "OPERATING", "country_code": "JP"},
    "XPAR": {"mic_type": "OPERATING", "country_code": "FR"},
}

MIN_OPERATING = 1500
MIN_SEGMENT = 1000
MIN_TOTAL = 2500


def is_date(s: str) -> bool:
    if not DATE_RE.fullmatch(s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def chain_terminates(mic: str, by_mic: dict[str, dict[str, Any]],
                     max_depth: int = 8) -> tuple[bool, str]:
    seen = {mic}
    cur = by_mic[mic]["operating_mic"]
    for _ in range(max_depth):
        if cur in seen:
            return False, "cycle"
        seen.add(cur)
        parent = by_mic.get(cur)
        if parent is None:
            return False, "missing parent"
        if parent["mic_type"] == "OPERATING":
            return True, ""
        cur = parent["operating_mic"]
    return False, "chain too deep"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional(path: Path) -> Any | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict, schema: dict, iso3166: Any, exchange_mics: Any,
             skip: set[str]) -> list[str]:
    errs: list[str] = []

    def check(name: str) -> bool:
        return name not in skip

    # Layer 1: schema
    if check("schema"):
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            errs.append(f"[schema] {e.message} at {list(e.absolute_path)}")

    mics = data.get("mics", [])
    meta = data.get("meta", {})

    # Layer 2: integrity
    if check("integrity"):
        for m in mics:
            if not MIC_RE.fullmatch(m.get("mic", "")):
                errs.append(f"[integrity] {m.get('mic')}: bad mic")
            if not MIC_RE.fullmatch(m.get("operating_mic", "")):
                errs.append(f"[integrity] {m.get('mic')}: bad operating_mic")
            for f in ("creation_date", "last_update_date",
                      "last_validation_date", "expiration_date"):
                v = m.get(f)
                if v is not None and not is_date(v):
                    errs.append(f"[integrity] {m['mic']}: {f}={v!r} not a date")
            c = m.get("country_code")
            if c is not None and not COUNTRY_RE.fullmatch(c):
                errs.append(f"[integrity] {m['mic']}: country={c!r}")
        if not DATE_RE.fullmatch(meta.get("source_snapshot", "")):
            errs.append(f"[integrity] meta.source_snapshot not a date")

    # Layer 3: business
    if check("business"):
        seen: set[str] = set()
        for m in mics:
            mic = m["mic"]
            if mic in seen:
                errs.append(f"[business] duplicate mic {mic}")
            seen.add(mic)

            if m["mic_type"] == "OPERATING":
                if m["operating_mic"] != mic:
                    errs.append(
                        f"[business] {mic}: operating must self-reference, "
                        f"found {m['operating_mic']}"
                    )
            elif m["mic_type"] == "SEGMENT":
                if m["operating_mic"] == mic:
                    errs.append(f"[business] {mic}: segment self-references")

            if m["status"] == "EXPIRED" and not m.get("expiration_date"):
                errs.append(f"[business] {mic}: expired without expiration_date")

    # Layer 4: cross-reference
    if check("cross-reference"):
        by_mic = {m["mic"]: m for m in mics}
        for m in mics:
            if m["mic_type"] != "SEGMENT":
                continue
            ok, reason = chain_terminates(m["mic"], by_mic)
            if not ok:
                errs.append(f"[cross-ref] {m['mic']}: chain {reason}")

        if iso3166 is not None:
            alpha2 = set(iso3166.get("alpha_2_set", []))
            if not alpha2:
                alpha2 = {c["alpha_2"] for c in iso3166.get("countries", [])}
            for m in mics:
                c = m.get("country_code")
                if c and c not in alpha2:
                    errs.append(f"[cross-ref] {m['mic']}: country {c} not in ISO 3166")

        if exchange_mics is not None:
            have = {m["mic"] for m in mics}
            wanted = set(exchange_mics.get("mics", []))
            missing = sorted(wanted - have)
            if missing:
                errs.append(
                    f"[cross-ref] {len(missing)} MIC(s) referenced by "
                    f"Exchange Calendar not in registry: {missing[:10]}"
                )

    # Layer 5: ground truth
    if check("ground-truth"):
        by_mic = {m["mic"]: m for m in mics}
        for mic, expect in GROUND_TRUTH.items():
            m = by_mic.get(mic)
            if m is None:
                errs.append(f"[ground-truth] {mic} missing")
                continue
            for k, v in expect.items():
                if m.get(k) != v:
                    errs.append(
                        f"[ground-truth] {mic}.{k} = {m.get(k)!r}, want {v!r}"
                    )

    # Layer 6: coverage
    if check("coverage"):
        c = meta.get("counts", {})
        if c.get("operating", 0) < MIN_OPERATING:
            errs.append(f"[coverage] operating {c.get('operating')} < {MIN_OPERATING}")
        if c.get("segment", 0) < MIN_SEGMENT:
            errs.append(f"[coverage] segment {c.get('segment')} < {MIN_SEGMENT}")
        if c.get("total", 0) < MIN_TOTAL:
            errs.append(f"[coverage] total {c.get('total')} < {MIN_TOTAL}")

    return errs


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", nargs="?", type=Path, default=Path("iso10383.json"))
    p.add_argument("--schema", type=Path, default=Path("schema.json"))
    p.add_argument("--iso3166", type=Path, default=Path("tools/iso3166_snapshot.json"))
    p.add_argument("--exchange-calendar", type=Path,
                   default=Path("tools/exchange_calendar_snapshot.json"))
    p.add_argument("--only", action="append", default=[],
                   choices=["schema", "integrity", "business",
                            "cross-reference", "ground-truth", "coverage"])
    p.add_argument("--skip", action="append", default=[])
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if not args.path.is_file():
        print(f"not found: {args.path}", file=sys.stderr)
        return 2
    if not args.schema.is_file():
        print(f"not found: {args.schema}", file=sys.stderr)
        return 2

    data = load_json(args.path)
    schema = load_json(args.schema)
    iso = load_optional(args.iso3166)
    ec = load_optional(args.exchange_calendar)

    skip = set(args.skip)
    if args.only:
        all_layers = {"schema", "integrity", "business",
                      "cross-reference", "ground-truth", "coverage"}
        skip = all_layers - set(args.only)

    errs = validate(data, schema, iso, ec, skip)

    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        print(f"FAIL: {len(errs)} error(s)", file=sys.stderr)
        return 3 if any(e.startswith("[schema]") for e in errs) else 1

    if not args.quiet:
        print(f"OK: {len(data['mics'])} MICs validated")
        c = data["meta"]["counts"]
        print(f"    {c['operating']} operating, {c['segment']} segment, "
              f"{c['active']} active, {c['updated']} updated, "
              f"{c['expired']} expired, {c['total']} total")
        print(f"    0 broken chains")
    return 0


if __name__ == "__main__":
    sys.exit(main())
