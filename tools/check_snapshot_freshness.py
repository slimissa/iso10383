#!/usr/bin/env python3
"""Check whether vendored snapshots are past their review_by date.

Two mechanisms keep a vendored snapshot honest, and this tool is only
one of them. This one is scheduled re-verification: it fails when
review_by has passed, whether or not anything upstream changed. The
other is the cross-reference check in tools/check_iso3166_current.py
and tools/check_exchange_calendar_current.py, against the same
snapshots: it fails when a value the consumer holds no longer resolves
in the snapshot, whether or not review_by is due. One catches drift by
the calendar, the other by content. Neither replaces the other.

For each tools/*_snapshot.json, look for a sibling
tools/<stem>.meta.json. Read meta.review_by from the sibling when
present, from the snapshot's own embedded meta block when not.

Three states for review_by:

  ISO date (YYYY-MM-DD)  -> fail if past today
  "closed"               -> never checked (static snapshot)
  null or missing        -> warn, do not fail

Version agreement: when both the snapshot and its sibling .meta.json
declare a source_version, the two must be equal. A snapshot that says
it came from one version while its metadata says another is a
provenance claim nothing else would catch. A snapshot that declares no
source_version (the Exchange Calendar snapshot) is not compared.

Exit codes:
  0  every snapshot fresh (warnings allowed)
  1  at least one snapshot past its review_by date
  2  malformed metadata (bad JSON, invalid date)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[snapshot] {path.name}: invalid JSON: {e}", file=sys.stderr)
        sys.exit(2)


def read_review_by(snapshot: Path) -> tuple[str | None, str]:
    """Return (review_by, source_label).

    review_by is the raw value: an ISO date string, "closed", or None.
    source_label names where it was read from, for reporting.
    """
    sibling = snapshot.parent / (snapshot.stem + ".meta.json")
    if sibling.is_file():
        meta = load_json(sibling)
        value = (meta.get("meta") or {}).get("review_by")
        return value, sibling.name

    data = load_json(snapshot)
    value = (data.get("meta") or {}).get("review_by")
    return value, f"{snapshot.name} (embedded)"


def read_version_pair(snapshot: Path) -> tuple[str | None, str | None]:
    """Return (snapshot source_version, sibling meta source_version)."""
    data = load_json(snapshot)
    sibling = snapshot.parent / (snapshot.stem + ".meta.json")
    meta = load_json(sibling) if sibling.is_file() else {}
    return data.get("source_version"), meta.get("source_version")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--today", default=date.today().isoformat(),
                   help="Override today's date (YYYY-MM-DD). For tests.")
    args = p.parse_args(argv)

    try:
        today = datetime.strptime(args.today, "%Y-%m-%d").date()
    except ValueError:
        print(f"invalid --today: {args.today!r}", file=sys.stderr)
        return 2

    snapshots = sorted(TOOLS.glob("*_snapshot.json"))
    if not snapshots:
        print("no snapshot files found under tools/", file=sys.stderr)
        return 2

    failures: list[str] = []
    warnings: list[str] = []
    fresh = 0

    for snap in snapshots:
        review_by, source_label = read_review_by(snap)

        snap_version, meta_version = read_version_pair(snap)
        if snap_version and meta_version and snap_version != meta_version:
            failures.append(
                f"[snapshot] {snap.name}: source_version mismatch: the "
                f"snapshot declares {snap_version}, its metadata declares "
                f"{meta_version}"
            )
            continue

        if review_by == "closed":
            fresh += 1
            continue

        if not review_by:
            warnings.append(
                f"[snapshot] {snap.name}: review_by unset "
                f"(source: {source_label})"
            )
            continue

        try:
            due = datetime.strptime(review_by, "%Y-%m-%d").date()
        except ValueError:
            print(
                f"[snapshot] {snap.name}: invalid review_by {review_by!r}",
                file=sys.stderr,
            )
            return 2

        if today > due:
            failures.append(
                f"[snapshot] {snap.name}: past review_by {review_by} "
                f"(source: {source_label})"
            )
        else:
            fresh += 1

    for w in warnings:
        print(w, file=sys.stderr)

    if failures:
        for f in failures:
            print(f, file=sys.stderr)
        print(f"FAIL: {len(failures)} snapshot(s) stale", file=sys.stderr)
        return 1

    label = "OK (with warnings)" if warnings else "OK"
    print(f"{label}: {fresh} snapshot(s) fresh")
    return 0


if __name__ == "__main__":
    sys.exit(main())