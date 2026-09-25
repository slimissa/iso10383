"""Six-layer validator for iso10383.json.

Layers, run in order:

  1. schema         JSON Schema draft-07 (schema.json)
  2. integrity      patterns, date format, non-empty strings
  3. business       uniqueness, status/mic_type consistency,
                    operating MIC self-reference, segment not self-ref
  4. cross-ref      chain resolution (errors); ISO 3166 and Exchange
                    Calendar checks (warnings in v1.0.0, see D6)
  5. ground truth   spot checks for XNYS, XLON, XTKS, XPAR
  6. coverage       operating >= 1500, segment >= 1000, total >= 2500

Severity model:

  * Internal checks (1, 2, 3, 5, 6, and the chain-resolution part of
    layer 4) always produce errors.
  * Cross-registry checks (the ISO 3166 and Exchange Calendar parts
    of layer 4) are advisory in v1.0.0 (D6). They warn by default and
    promote to errors under --strict.

Exit codes:
  0  pass (may include warnings)
  1  data error
  2  usage error
  3  schema violation
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema

# MICs referenced by a sibling registry that are known to be absent
# from SWIFT's published file. Adding to this set requires an ADR
# amendment. See docs/decisions/0007-cross-registry-allowlist.md.
KNOWN_EXCHANGE_CALENDAR_GAPS = frozenset({
    "XBEK",  # Beirut Stock Exchange
    "XNBO",  # Nairobi Securities Exchange
    "XQSE",  # Qatar Exchange
})

MIC_RE = re.compile(r"^[A-Z0-9]{4}$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Country codes valid in the ISO 10383 source but not in ISO 3166-1
# alpha-2. "ZZ" is ISO 10383's placeholder for "no fixed country".
NON_ISO3166_PLACEHOLDERS = {"ZZ"}

GROUND_TRUTH: dict[str, dict[str, str]] = {
    "XNYS": {"mic_type": "OPERATING", "country_code": "US"},
    "XLON": {"mic_type": "OPERATING", "country_code": "GB"},
    "XTKS": {"mic_type": "SEGMENT", "country_code": "JP"},
    "XPAR": {"country_code": "FR"},
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
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[schema] {path}: {e}", file=sys.stderr)
        sys.exit(3)


def load_optional(path: Path) -> Any | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data, schema, iso3166, exchange_mics, skip, advisory=False):
    errors: list[str] = []
    warnings: list[str] = []

    def check(name: str) -> bool:
        return name not in skip

    mics = data.get("mics", [])
    meta = data.get("meta", {})

    if check("schema"):
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"[schema] {e.message} at {list(e.absolute_path)}")

    if check("integrity"):
        for m in mics:
            if not MIC_RE.fullmatch(m.get("mic", "")):
                errors.append(f"[integrity] {m.get('mic')}: bad mic")
            if not MIC_RE.fullmatch(m.get("operating_mic", "")):
                errors.append(f"[integrity] {m.get('mic')}: bad operating_mic")
            for f in ("creation_date", "last_update_date",
                      "last_validation_date", "expiration_date"):
                v = m.get(f)
                if v is not None and not is_date(v):
                    errors.append(f"[integrity] {m['mic']}: {f}={v!r} not a date")
            c = m.get("country_code")
            if c is not None and not COUNTRY_RE.fullmatch(c):
                errors.append(f"[integrity] {m['mic']}: country={c!r}")
        if not DATE_RE.fullmatch(meta.get("source_snapshot", "")):
            errors.append("[integrity] meta.source_snapshot not a date")

    if check("business"):
        seen: set[str] = set()
        for m in mics:
            mic = m["mic"]
            if mic in seen:
                errors.append(f"[business] duplicate mic {mic}")
            seen.add(mic)
            if m["mic_type"] == "OPERATING":
                if m["operating_mic"] != mic:
                    errors.append(
                        f"[business] {mic}: operating must self-reference, "
                        f"found {m['operating_mic']}"
                    )
            elif m["mic_type"] == "SEGMENT":
                if m["operating_mic"] == mic:
                    errors.append(f"[business] {mic}: segment self-references")
            if m["status"] == "EXPIRED" and not m.get("expiration_date"):
                errors.append(f"[business] {mic}: expired without expiration_date")

    if check("cross-reference"):
        by_mic = {m["mic"]: m for m in mics}
        # Internal: chain resolution. Always errors.
        for m in mics:
            if m["mic_type"] != "SEGMENT":
                continue
            ok, reason = chain_terminates(m["mic"], by_mic)
            if not ok:
                errors.append(f"[cross-ref] {m['mic']}: chain {reason}")

        # Cross-registry: blocking by default (D6, v1.0.1).
        # --advisory redirects unexpected gaps to warnings.
        unexpected_sink = warnings if advisory else errors

        if iso3166 is not None:
            alpha2 = set(iso3166.get("alpha_2_set", []))
            if not alpha2:
                alpha2 = {c["alpha_2"] for c in iso3166.get("countries", [])}
            for m in mics:
                c = m.get("country_code")
                if c and c not in alpha2 and c not in NON_ISO3166_PLACEHOLDERS:
                    unexpected_sink.append(
                        f"[cross-ref] {m['mic']}: country {c} not in ISO 3166"
                    )

        if exchange_mics is not None:
            have = {m["mic"] for m in mics}
            wanted = set(exchange_mics.get("mics", []))
            missing = sorted(wanted - have)

            known = [m for m in missing if m in KNOWN_EXCHANGE_CALENDAR_GAPS]
            unexpected = [m for m in missing
                          if m not in KNOWN_EXCHANGE_CALENDAR_GAPS]

            if known:
                warnings.append(
                    f"[cross-ref] {len(known)} MIC(s) missing and in the "
                    f"allowlist: {known}"
                )
            if unexpected:
                unexpected_sink.append(
                    f"[cross-ref] {len(unexpected)} MIC(s) referenced by "
                    f"Exchange Calendar but not in the registry and not in "
                    f"the allowlist: {unexpected[:10]}"
                )

    if check("ground-truth"):
        by_mic = {m["mic"]: m for m in mics}
        for mic, expect in GROUND_TRUTH.items():
            m = by_mic.get(mic)
            if m is None:
                errors.append(f"[ground-truth] {mic} missing")
                continue
            for k, v in expect.items():
                if m.get(k) != v:
                    errors.append(
                        f"[ground-truth] {mic}.{k} = {m.get(k)!r}, want {v!r}"
                    )

    if check("coverage"):
        c = meta.get("counts", {})
        if c.get("operating", 0) < MIN_OPERATING:
            errors.append(f"[coverage] operating {c.get('operating')} < {MIN_OPERATING}")
        if c.get("segment", 0) < MIN_SEGMENT:
            errors.append(f"[coverage] segment {c.get('segment')} < {MIN_SEGMENT}")
        if c.get("total", 0) < MIN_TOTAL:
            errors.append(f"[coverage] total {c.get('total')} < {MIN_TOTAL}")

    return errors, warnings


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", nargs="?", type=Path, default=Path("iso10383.json"))
    p.add_argument("--schema", type=Path, default=Path("schema.json"))
    p.add_argument("--iso3166", type=Path,
                   default=Path("tools/iso3166_snapshot.json"))
    p.add_argument("--exchange-calendar", type=Path,
                   default=Path("tools/exchange_calendar_snapshot.json"))
    p.add_argument("--only", action="append", default=[],
                   choices=["schema", "integrity", "business",
                            "cross-reference", "ground-truth", "coverage"])
    p.add_argument("--skip", action="append", default=[])
    p.add_argument("--strict", action="store_true",
                   help="Promote all warnings to errors.")
    p.add_argument("--advisory", action="store_true",
                   help="Revert cross-registry checks to advisory. "
                        "Unexpected gaps become warnings, not errors.")
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

    errors, warnings = validate(data, schema, iso, ec, skip, advisory=args.advisory)

    if args.strict and warnings:
        errors.extend(warnings)
        warnings = []

    for w in warnings:
        print(w, file=sys.stderr)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(f"FAIL: {len(errors)} error(s)", file=sys.stderr)
        return 3 if any(e.startswith("[schema]") for e in errors) else 1

    if not args.quiet:
        label = "OK (with warnings)" if warnings else "OK"
        print(f"{label}: {len(data['mics'])} MICs validated")
        c = data["meta"]["counts"]
        print(
            f"    {c['operating']} operating, "
            f"{c['segment']} segment, "
            f"{c['active']} active, "
            f"{c['updated']} updated, "
            f"{c['expired']} expired, "
            f"{c['total']} total"
        )
        print("    0 broken chains")
    return 0


if __name__ == "__main__":
    sys.exit(main())
