#!/usr/bin/env python3
"""Compare tools/iso4217_snapshot.json against the live ISO 4217 registry.

Exit 0 if in sync (or if the sibling is unreachable).
Exit 1 if drifted and --strict.

The ISO 4217 snapshot does not yet exist. This script exits 0 with a
note when the snapshot is absent.
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

SNAPSHOT = Path(__file__).parent / "iso4217_snapshot.json"
LIVE_URL = "https://raw.githubusercontent.com/slimissa/iso4217/main/iso4217.json"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()

    if not SNAPSHOT.is_file():
        print(f"note: {SNAPSHOT.name} not present yet; nothing to check")
        return 0

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snap_codes = set(snap["codes"])

    try:
        with urllib.request.urlopen(LIVE_URL, timeout=30) as r:
            live_data = json.loads(r.read())
    except Exception as e:
        print(f"note: sibling unreachable ({e})", file=sys.stderr)
        return 0

    live_codes = {c["code"] for c in live_data.get("currencies", {}).get("active", [])}

    added = sorted(live_codes - snap_codes)
    removed = sorted(snap_codes - live_codes)

    if not added and not removed:
        print(f"OK: snapshot is current ({len(snap_codes)} codes)")
        return 0

    print(f"stale: {len(added)} added, {len(removed)} removed since the snapshot")

    if args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
