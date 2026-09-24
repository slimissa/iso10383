#!/usr/bin/env python3
"""Diff two iso10383 snapshots. Print the change summary.

  python3 tools/refresh_diff.py OLD.json NEW.json

Exit codes:
  0  no removals (NEW has every OLD mic)
  1  REMOVED > 0, requires human confirmation before merge
  2  usage error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def index(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {m["mic"]: m for m in data["mics"]}


WATCHED = ("market_name", "country_code", "market_category",
           "status", "operating_mic", "mic_type")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    old = index(Path(sys.argv[1]))
    new = index(Path(sys.argv[2]))

    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    common = set(old) & set(new)

    changed_fields: dict[str, list[str]] = {f: [] for f in WATCHED}
    for mic in sorted(common):
        for f in WATCHED:
            if old[mic].get(f) != new[mic].get(f):
                changed_fields[f].append(mic)

    def bucket(mics, which):
        op = sum(1 for m in mics if old.get(m, new.get(m))["mic_type"] == "OPERATING")
        sg = sum(1 for m in mics if old.get(m, new.get(m))["mic_type"] == "SEGMENT")
        return op, sg

    added_op, added_sg = bucket(added, "new")
    removed_op, removed_sg = bucket(removed, "old")
    expired_added = sum(1 for m in added if new[m]["status"] == "EXPIRED")

    print(f"NEW:      {added_op} operating, {added_sg} segment")
    print(f"EXPIRED:  {expired_added} of the new entries are already expired")
    changed_total = sum(len(v) for v in changed_fields.values())
    per_field = ", ".join(
        f"{f}={len(v)}" for f, v in changed_fields.items() if v
    ) or "none"
    print(f"CHANGED:  {changed_total} ({per_field})")
    print(f"REMOVED:  {len(removed)} ({removed_op} operating, {removed_sg} segment)")

    if removed:
        print()
        print("Removed MICs (need human confirmation):", file=sys.stderr)
        for m in removed[:20]:
            print(f"  {m}", file=sys.stderr)
        if len(removed) > 20:
            print(f"  ... and {len(removed) - 20} more", file=sys.stderr)
        print(file=sys.stderr)
        print("FAIL: REMOVED > 0. Confirm intentional before merging.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
