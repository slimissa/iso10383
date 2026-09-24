"""Copy iso10383.json into wrapper bundle directories.

Wrappers do not exist yet (Phase 5). This tool is written now so CI can
call it once they do, and so the interface is stable.

Each wrapper directory listed below receives a byte-identical copy of
iso10383.json at a known location. `--check` verifies the copies match.

Usage:
  python3 tools/sync_wrappers.py             # write copies
  python3 tools/sync_wrappers.py --check     # verify copies
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SOURCE = Path("iso10383.json")

# (wrapper_dir, target_path_inside_wrapper)
TARGETS = [
    ("wrappers/go/data/iso10383.json", None),
    ("wrappers/rust/data/iso10383.json", None),
]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    if not SOURCE.is_file():
        print(f"missing: {SOURCE}", file=sys.stderr)
        return 1

    if args.check:
        drift = []
        for target, _ in TARGETS:
            path = Path(target)
            if not path.is_file():
                drift.append(f"missing: {target}")
            elif path.read_bytes() != SOURCE.read_bytes():
                drift.append(f"stale:   {target}")
        if drift:
            for d in drift:
                print(d, file=sys.stderr)
            # Not a failure while wrappers do not exist.
            print(f"note: {len(drift)} target(s) not yet present",
                  file=sys.stderr)
            return 0
        print(f"OK: {len(TARGETS)} wrapper copies in sync")
        return 0

    for target, _ in TARGETS:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SOURCE, path)
        print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
