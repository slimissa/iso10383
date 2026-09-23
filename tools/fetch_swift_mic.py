"""ISO 10383 MIC registry fetcher.

Downloads and parses the SWIFT-published MIC file into iso10383.json.

Two phases, deliberately separated:
  download()  -- network, cached to raw/MIC_YYYYMMDD.csv
  parse()     -- reads the cached file, emits iso10383.json

The download is the only network step. The parse reads the cached file
so CI can re-run it without hitting SWIFT.

Ground truth: docs/source_format.md.

Design notes
------------
* Parsing and linking are separate steps. A row that is structurally
  malformed is a hard error (raise). A row that references a parent
  which does not resolve is a soft error (record, continue).
* A broken chain is a real-world condition, not a parse bug. The
  validator decides policy; the fetcher faithfully represents the source.
* Output is deterministic: sort_keys=True, entries sorted by mic, LF
  line endings, trailing newline. Two runs on the same input produce
  byte-identical output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterator

# --- Constants ---------------------------------------------------------------

SOURCE_URL = (
    "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv"
)

MIC_RE = re.compile(r"^[A-Z0-9]{4}$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
DATE_RE = re.compile(r"^\d{8}$")

MIC_TYPE_MAP: dict[str, str] = {
    "OPRT": "OPERATING",
    "SGMT": "SEGMENT",
}

STATUS_MAP: dict[str, str] = {
    "ACTIVE": "ACTIVE",
    "UPDATED": "UPDATED",
    "EXPIRED": "EXPIRED",
}

# Union of the 16 codes defined by the Release 2.0 factsheet. The current
# snapshot uses 14 of them; the enum is the union so a future assignment
# of ARMS or CTPS does not fail the schema. See D4.
MARKET_CATEGORY_SET: set[str] = {
    "ATSS", "APPA", "ARMS", "CTPS", "CASP", "DCMS", "IDQS", "MLTF",
    "NSPD", "OTFS", "OTHR", "RMOS", "RMKT", "SEFS", "SINT", "TRFS",
}

REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "MIC",
    "OPERATING MIC",
    "OPRT/SGMT",
    "MARKET NAME-INSTITUTION DESCRIPTION",
    "LEGAL ENTITY NAME",
    "LEI",
    "MARKET CATEGORY CODE",
    "ACRONYM",
    "ISO COUNTRY CODE (ISO 3166)",
    "CITY",
    "WEBSITE",
    "STATUS",
    "CREATION DATE",
    "LAST UPDATE DATE",
    "LAST VALIDATION DATE",
    "EXPIRY DATE",
    "COMMENTS",
})


# --- Small helpers -----------------------------------------------------------

def clean(raw: str | None) -> str | None:
    """Strip whitespace. Empty string becomes None."""
    if raw is None:
        return None
    raw = raw.strip()
    return raw or None


def to_iso_date(raw: str | None, row_num: int, mic: str, field: str) -> str | None:
    v = clean(raw)
    if v is None:
        return None
    if not DATE_RE.fullmatch(v):
        raise ValueError(
            f"row {row_num} (MIC {mic}): {field} not YYYYMMDD: {v!r}"
        )
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


# --- Download ----------------------------------------------------------------

def download(force: bool = False, target: Path | None = None) -> Path:
    """Download the current ISO 10383 CSV. Cached: pass force=True to refetch."""
    import urllib.request

    if target is None:
        target = Path("raw") / f"MIC_{date.today():%Y%m%d}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and not force:
        print(f"Using cached {target}")
        return target

    print(f"Downloading {SOURCE_URL}")
    print(f"         to {target}")
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as r:
        data = r.read()

    if len(data) < 100_000:
        raise RuntimeError(
            f"download too small ({len(data)} bytes); URL may have changed"
        )

    target.write_bytes(data)
    print(f"Wrote {len(data):,} bytes")
    return target


# --- Parse -------------------------------------------------------------------

def iter_rows(csv_path: Path) -> Iterator[tuple[int, dict[str, str]]]:
    """Yield (row_num, row_dict). Row 1 is the header, so the first data
    row is row_num=2. Missing required columns fail immediately."""
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        missing = REQUIRED_COLUMNS - set(headers)
        if missing:
            raise ValueError(
                f"{csv_path}: missing columns: {sorted(missing)}"
            )
        for i, row in enumerate(reader):
            yield i + 2, row


def build_entry(row: dict[str, str], row_num: int) -> dict[str, Any]:
    """Convert one CSV row to a JSON entry. Raises on structurally bad
    rows. Does not resolve operating_mic against the rest of the file."""
    mic = clean(row["MIC"])
    if mic is None:
        raise ValueError(f"row {row_num}: empty MIC")
    if not MIC_RE.fullmatch(mic):
        raise ValueError(f"row {row_num}: invalid MIC {mic!r}")

    os_flag = clean(row["OPRT/SGMT"])
    if os_flag not in MIC_TYPE_MAP:
        raise ValueError(
            f"row {row_num} (MIC {mic}): unknown OPRT/SGMT {os_flag!r}"
        )
    mic_type = MIC_TYPE_MAP[os_flag]

    operating_raw = clean(row["OPERATING MIC"])
    if operating_raw is None:
        raise ValueError(f"row {row_num} (MIC {mic}): empty OPERATING MIC")
    if not MIC_RE.fullmatch(operating_raw):
        raise ValueError(
            f"row {row_num} (MIC {mic}): invalid OPERATING MIC {operating_raw!r}"
        )

    if mic_type == "OPERATING":
        if operating_raw != mic:
            raise ValueError(
                f"row {row_num} (MIC {mic}): OPERATING MIC must self-reference; "
                f"found {operating_raw!r}"
            )
    else:  # SEGMENT
        if operating_raw == mic:
            raise ValueError(
                f"row {row_num} (MIC {mic}): SEGMENT must not self-reference"
            )

    status_raw = clean(row["STATUS"])
    if status_raw not in STATUS_MAP:
        raise ValueError(
            f"row {row_num} (MIC {mic}): unknown STATUS {status_raw!r}"
        )

    category_raw = clean(row["MARKET CATEGORY CODE"])
    if category_raw is not None and category_raw not in MARKET_CATEGORY_SET:
        raise ValueError(
            f"row {row_num} (MIC {mic}): unknown MARKET CATEGORY CODE "
            f"{category_raw!r}"
        )

    country = clean(row["ISO COUNTRY CODE (ISO 3166)"])
    if country is not None and not COUNTRY_RE.fullmatch(country):
        raise ValueError(
            f"row {row_num} (MIC {mic}): invalid country {country!r}"
        )

    return {
        "mic": mic,
        "mic_type": mic_type,
        "status": STATUS_MAP[status_raw],
        "operating_mic": operating_raw,
        "market_name": clean(row["MARKET NAME-INSTITUTION DESCRIPTION"]),
        "legal_entity_name": clean(row["LEGAL ENTITY NAME"]),
        "lei": clean(row["LEI"]),
        "market_category": category_raw,
        "acronym": clean(row["ACRONYM"]),
        "country_code": country,
        "city": clean(row["CITY"]),
        "website": clean(row["WEBSITE"]),
        "creation_date": to_iso_date(row["CREATION DATE"], row_num, mic, "CREATION DATE"),
        "last_update_date": to_iso_date(row["LAST UPDATE DATE"], row_num, mic, "LAST UPDATE DATE"),
        "last_validation_date": to_iso_date(row["LAST VALIDATION DATE"], row_num, mic, "LAST VALIDATION DATE"),
        "expiration_date": to_iso_date(row["EXPIRY DATE"], row_num, mic, "EXPIRY DATE"),
        "note": clean(row["COMMENTS"]),
    }


# --- Link --------------------------------------------------------------------

def resolve_chain(mic: str, by_mic: dict[str, dict[str, Any]],
                  max_depth: int = 8) -> dict[str, Any]:
    """Follow the parent chain from `mic` upward. Return a report:

    {"ok": True,  "terminates_at": "XBER", "depth": 2}
    {"ok": False, "reason": "...", "chain": [...]}
    """
    chain = [mic]
    seen = {mic}
    cur = by_mic[mic]["operating_mic"]
    depth = 0

    while depth < max_depth:
        chain.append(cur)
        if cur in seen:
            return {"ok": False, "reason": "cycle", "chain": chain}
        seen.add(cur)
        parent = by_mic.get(cur)
        if parent is None:
            return {"ok": False, "reason": "missing parent", "chain": chain}
        if parent["mic_type"] == "OPERATING":
            return {"ok": True, "terminates_at": cur, "depth": depth + 1}
        cur = parent["operating_mic"]
        depth += 1

    return {"ok": False, "reason": "chain too deep", "chain": chain}


def link_operating_mics(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Verify every segment's chain terminates at an operating MIC.

    Returns the list of segments whose chains are broken: cycles,
    missing parents, or chains deeper than 8 levels. The validator
    decides policy; the fetcher records.
    """
    by_mic = {e["mic"]: e for e in entries}
    broken: list[dict[str, Any]] = []

    for e in entries:
        if e["mic_type"] != "SEGMENT":
            continue
        report = resolve_chain(e["mic"], by_mic)
        if not report["ok"]:
            broken.append({
                "mic": e["mic"],
                "operating_mic": e["operating_mic"],
                "reason": report["reason"],
                "chain": report["chain"],
            })

    return broken

# --- Assemble ----------------------------------------------------------------

def assemble(entries: list[dict[str, Any]], broken: list[dict[str, Any]],
             version: str, snapshot_date: str, source_hash: str) -> dict[str, Any]:
    status_counts = Counter(e["status"] for e in entries)
    operating = sum(1 for e in entries if e["mic_type"] == "OPERATING")
    segment = sum(1 for e in entries if e["mic_type"] == "SEGMENT")

    return {
        "meta": {
            "version": version,
            "updated": snapshot_date,
            "source_snapshot": snapshot_date,
            "source_url": SOURCE_URL,
            "source_hash": source_hash,
            "counts": {
                "operating": operating,
                "segment": segment,
                "expired": status_counts.get("EXPIRED", 0),
                "active": status_counts.get("ACTIVE", 0),
                "updated": status_counts.get("UPDATED", 0),
                "total": len(entries),
            },
            "broken_chains": broken,
        },
        "mics": sorted(entries, key=lambda e: e["mic"]),
    }


# --- Write -------------------------------------------------------------------

def write_json(data: dict[str, Any], path: Path) -> None:
    """Deterministic write: sorted keys, LF, trailing newline."""
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


# --- Entry point -------------------------------------------------------------

def parse(csv_path: Path, version: str, snapshot_date: str) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for row_num, row in iter_rows(csv_path):
        entries.append(build_entry(row, row_num))

    seen: set[str] = set()
    for e in entries:
        if e["mic"] in seen:
            raise ValueError(f"duplicate MIC in file: {e['mic']}")
        seen.add(e["mic"])

    broken = link_operating_mics(entries)
    source_hash = sha256_of(csv_path)
    return assemble(entries, broken, version, snapshot_date, source_hash)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fetch_swift_mic",
        description="Parse the ISO 10383 MIC CSV into iso10383.json.",
    )
    parser.add_argument(
        "--raw", type=Path,
        help="Path to a cached raw CSV. Defaults to the newest raw/MIC_*.csv.",
    )
    parser.add_argument(
        "--download", action="store_true",
        help="Download a fresh copy before parsing.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="With --download: refetch even if a cached file exists.",
    )
    parser.add_argument(
        "--out", "-o", type=Path, default=Path("iso10383.json"),
        help="Output JSON path (default: iso10383.json).",
    )
    parser.add_argument(
        "--version", default="0.1.0",
        help="Value for meta.version (default: 0.1.0).",
    )
    parser.add_argument(
        "--snapshot-date", default=date.today().isoformat(),
        help="Value for meta.source_snapshot, YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Fail if any broken chains are found.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and report, do not write the JSON.",
    )
    args = parser.parse_args(argv)

    raw = args.raw
    if args.download:
        raw = download(force=args.force, target=raw)
    elif raw is None:
        candidates = sorted(Path("raw").glob("MIC_*.csv"))
        if not candidates:
            print(
                "No raw/MIC_*.csv found. Use --download or --raw PATH.",
                file=sys.stderr,
            )
            return 2
        raw = candidates[-1]

    print(f"Parsing {raw}")
    data = parse(raw, args.version, args.snapshot_date)

    c = data["meta"]["counts"]
    print(
        f"  {c['operating']} operating, "
        f"{c['segment']} segment, "
        f"{c['active']} active, "
        f"{c['updated']} updated, "
        f"{c['expired']} expired, "
        f"{c['total']} total"
    )

    broken = data["meta"]["broken_chains"]
    if broken:
        print(f"  {len(broken)} broken chain(s):")
        for b in broken[:10]:
            chain = " -> ".join(b["chain"])
            print(f"    {chain}  ({b['reason']})")
        if len(broken) > 10:
            print(f"    ... and {len(broken) - 10} more")

    if args.strict and broken:
        print("FAIL: --strict and broken chains exist", file=sys.stderr)
        return 1

    if args.dry_run:
        print("Dry run: not writing JSON.")
        return 0

    write_json(data, args.out)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())