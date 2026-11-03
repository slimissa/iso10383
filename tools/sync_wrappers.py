#!/usr/bin/env python3
"""Copy iso10383.json into wrapper bundle directories.

Each wrapper ships a byte-identical copy of the root snapshot at a
known path. `--check` verifies the copies match a fresh build.

Usage:
  python3 tools/sync_wrappers.py             # write copies
  python3 tools/sync_wrappers.py --check     # verify copies
  python3 tools/sync_wrappers.py --check --allow-missing

--check fails (exit 1) on a missing target as well as on a stale one,
as check_version_consistency.py does for a missing version site.
--allow-missing downgrades a missing target to a note, for a checkout
where a wrapper has not been built yet; stale copies still fail.
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true",
                   help="Verify copies are in sync. A missing target fails.")
    p.add_argument("--allow-missing", action="store_true",
                   help="With --check, report a missing target as a note "
                        "instead of failing (wrappers still being built).")
    args = p.parse_args(argv)
    if args.allow_missing and not args.check:
        p.error("--allow-missing only applies with --check")

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
            print(f"missing: {m}",
                  file=sys.stdout if args.allow_missing else sys.stderr)
        if drift:
            print(f"FAIL: {len(drift)} artifact(s) out of sync",
                  file=sys.stderr)
            return 1
        if missing and not args.allow_missing:
            print(f"FAIL: {len(missing)} target(s) missing "
                  f"(--allow-missing to tolerate)", file=sys.stderr)
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
