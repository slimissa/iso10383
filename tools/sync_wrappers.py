#!/usr/bin/env python3
"""Copy iso10383.json into wrapper bundle directories.

Each wrapper ships a byte-identical copy of the root snapshot at a
known path. `--check` verifies the copies match a fresh build.

Usage:
  python3 tools/sync_wrappers.py             # write copies
  python3 tools/sync_wrappers.py --check     # verify copies

Targets that do not yet exist are reported but do not fail the check.
Phase 7's CI promotes missing targets to a hard failure.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SOURCE = Path("iso10383.json")

TARGETS = [
    "wrappers/python/src/iso10383/data/iso10383.json",
    "wrappers/javascript/src/data/iso10383.json",
    "wrappers/rust/data/iso10383.json",
    "wrappers/go/data/iso10383.json",
]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true",
                   help="Verify copies are in sync. Missing targets are notes, "
                        "not failures, while wrappers are still being built.")
    args = p.parse_args()

    if not SOURCE.is_file():
        print(f"missing: {SOURCE}", file=sys.stderr)
        return 1

    if args.check:
        drift: list[str] = []
        missing: list[str] = []
        for target in TARGETS:
            path = Path(target)
            if not path.is_file():
                missing.append(target)
            elif path.read_bytes() != SOURCE.read_bytes():
                drift.append(target)
        for d in drift:
            print(f"stale:   {d}", file=sys.stderr)
        for m in missing:
            print(f"missing: {m}")
        if drift:
            print(f"FAIL: {len(drift)} artifact(s) out of sync",
                  file=sys.stderr)
            return 1
        if missing:
            print(f"note: {len(missing)} target(s) not yet present")
        else:
            print(f"OK: {len(TARGETS)} wrapper copies in sync")
        return 0

    for target in TARGETS:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SOURCE, path)
        print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
