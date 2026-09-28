#!/usr/bin/env python3
"""Check whether vendored snapshots are past their review_by date.

For each tools/*_snapshot.json, look for a sibling
tools/<stem>.meta.json. Read meta.review_by from the sibling when
present, from the snapshot's own embedded meta block when not.

Three states for review_by:

  ISO date (YYYY-MM-DD)  -> fail if past today
  "closed"               -> never checked (static snapshot)
  null or missing        -> warn, do not fail

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


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--today", default=date.today().isoformat(),
                   help="Override today's date (YYYY-MM-DD). For tests.")
    args = p.parse_args()

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