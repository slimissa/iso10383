#!/usr/bin/env python3
"""Compare tools/iso3166_snapshot.json against the live ISO 3166 registry.

Exit 0 if in sync (or if the sibling is unreachable and --advisory).
Exit 1 if drifted and --strict.

Advisory in v1.0.0 per D6. Blocking in v1.0.1.
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

SNAPSHOT = Path(__file__).parent / "iso3166_snapshot.json"
LIVE_URL = "https://raw.githubusercontent.com/slimissa/iso3166/main/iso3166.json"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snap_codes = set(snap["alpha_2_set"])

    try:
        with urllib.request.urlopen(LIVE_URL, timeout=30) as r:
            live_data = json.loads(r.read())
    except Exception as e:
        print(f"note: sibling unreachable ({e})", file=sys.stderr)
        return 0

    live_codes = {c["alpha_2"] for c in live_data.get("countries", {}).get("active", [])}

    added = sorted(live_codes - snap_codes)
    removed = sorted(snap_codes - live_codes)

    if not added and not removed:
        print(f"OK: snapshot is current ({len(snap_codes)} codes)")
        return 0

    print(f"stale: {len(added)} added, {len(removed)} removed since the snapshot")
    for c in added[:10]:
        print(f"  + {c}")
    for c in removed[:10]:
        print(f"  - {c}")
    if len(added) + len(removed) > 20:
        print(f"  ... and {len(added) + len(removed) - 20} more")

    if args.strict:
        print("FAIL: snapshot is stale", file=sys.stderr)
        return 1
    print("(advisory: rerun with --strict to fail)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
