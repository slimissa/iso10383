#!/usr/bin/env python3
"""Compare tools/exchange_calendar_snapshot.json against the live
Exchange Calendar registry.

Exit 0 if in sync (or if the sibling is unreachable and --advisory).
Exit 1 if drifted and --strict.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SNAPSHOT = Path(__file__).parent / "exchange_calendar_snapshot.json"
REPO = "https://github.com/slimissa/exchange-calendar.git"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snap_mics = set(snap["mics"])

    try:
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(
                ["git", "clone", "--depth", "1", REPO, td],
                check=True, capture_output=True,
            )
            live_mics = set()
            for f in (Path(td) / "exchanges").glob("*.json"):
                d = json.loads(f.read_text(encoding="utf-8"))
                if d.get("mic"):
                    live_mics.add(d["mic"])
                if d.get("code"):
                    live_mics.add(d["code"])
    except Exception as e:
        print(f"note: sibling unreachable ({e})", file=sys.stderr)
        return 0

    added = sorted(live_mics - snap_mics)
    removed = sorted(snap_mics - live_mics)

    if not added and not removed:
        print(f"OK: snapshot is current ({len(snap_mics)} MICs)")
        return 0

    print(f"stale: {len(added)} added, {len(removed)} removed since the snapshot")
    for m in added[:10]:
        print(f"  + {m}")
    for m in removed[:10]:
        print(f"  - {m}")

    if args.strict:
        print("FAIL: snapshot is stale", file=sys.stderr)
        return 1
    print("(advisory: rerun with --strict to fail)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
