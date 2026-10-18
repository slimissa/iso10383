#!/usr/bin/env python3
"""Compare tools/exchange_calendar_snapshot.json against the live
Exchange Calendar registry.

Exit 0 if in sync. Exit 1 if drifted and --strict.

Exit 1 if the sibling is unreachable: a comparison that could not run is
not a pass (docs/RELEASE_PATTERN.md, operator-hygiene rule 7). Pass
--advisory to exit 0 in that case instead; the note still prints.

Compares two things: the MIC set, and the version label (sidecar
source_version vs upstream meta.version). A MIC-set difference
fails under --strict. A version difference is only a warning on
stderr ("version drift") and never fails.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SNAPSHOT = Path(__file__).parent / "exchange_calendar_snapshot.json"
LOCAL_META = Path(__file__).parent / "exchange_calendar_snapshot.meta.json"
REPO = "https://github.com/slimissa/exchange-calendar.git"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--advisory", action="store_true",
                   help="Exit 0 when the sibling is unreachable, instead "
                        "of failing")
    args = p.parse_args(argv)

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snap_mics = set(snap["mics"])
    local_version = json.loads(
        LOCAL_META.read_text(encoding="utf-8")).get("source_version")
    live_version = None

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

            # Upstream declares its version at meta.version in calendar.json
            # (the repo's VERSION file carries the same value). The clone is
            # already on disk, so no second request is needed. Fallback:
            # VERSION. If neither exists the version is not compared; no
            # version is ever guessed.
            live_version = None
            cal = Path(td) / "calendar.json"
            if cal.exists():
                live_version = (json.loads(cal.read_text(encoding="utf-8"))
                                .get("meta", {}).get("version"))
            if live_version is None and (Path(td) / "VERSION").exists():
                live_version = (Path(td) / "VERSION").read_text(
                    encoding="utf-8").strip() or None
    except Exception as e:
        print(f"note: sibling unreachable ({e})", file=sys.stderr)
        if args.advisory:
            return 0
        print("FAIL: the sibling could not be reached, so nothing was "
              "compared (pass --advisory to tolerate this)", file=sys.stderr)
        return 1

    added = sorted(live_mics - snap_mics)
    removed = sorted(snap_mics - live_mics)
    mics_ok = not added and not removed

    if live_version is None:
        print("note: upstream declares no version; version not compared",
              file=sys.stderr)
    version_drift = live_version is not None and live_version != local_version
    if version_drift:
        print(f"warning: version drift: snapshot source_version {local_version}, "
              f"upstream version {live_version}; does not fail.",
              file=sys.stderr)

    if mics_ok:
        if version_drift:
            print(f"OK: MIC set is current ({len(snap_mics)} MICs)")
        else:
            print(f"OK: snapshot is current ({len(snap_mics)} MICs, "
                  f"version {local_version})")
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
