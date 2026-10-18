#!/usr/bin/env python3
"""Compare tools/iso3166_snapshot.json against the live ISO 3166 registry.

Exit 0 if in sync. Exit 1 if drifted and --strict.

Exit 1 if the sibling is unreachable: a comparison that could not run is
not a pass (docs/RELEASE_PATTERN.md, operator-hygiene rule 7). Pass
--advisory to exit 0 in that case instead; the note still prints.

Advisory in v1.0.0 per D6. Blocking in v1.0.1.

Compares two things: the alpha-2 code set, and the version label
(snapshot source_version vs upstream meta.version). A code-set
difference fails under --strict. A version difference is only a
warning on stderr ("version drift") and never fails.
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

SNAPSHOT = Path(__file__).parent / "iso3166_snapshot.json"
LOCAL_META = Path(__file__).parent / "iso3166_snapshot.meta.json"
LIVE_URL = "https://raw.githubusercontent.com/slimissa/iso3166/main/iso3166.json"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--advisory", action="store_true",
                   help="Exit 0 when the sibling is unreachable, instead "
                        "of failing")
    args = p.parse_args(argv)

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snap_codes = set(snap["alpha_2_set"])

    # Precondition: the embedded and sidecar versions must agree
    # (check_snapshot_freshness.py enforces the same). If they do
    # not, there is no single local version to compare upstream to.
    meta = json.loads(LOCAL_META.read_text(encoding="utf-8"))
    local_version = meta.get("source_version")
    if snap.get("source_version") != local_version:
        print(f"FAIL: snapshot source_version "
              f"{snap.get('source_version')!r} != sidecar source_version "
              f"{local_version!r}; reconcile before comparing upstream",
              file=sys.stderr)
        return 1

    try:
        with urllib.request.urlopen(LIVE_URL, timeout=30) as r:
            live_data = json.loads(r.read())
    except Exception as e:
        print(f"note: sibling unreachable ({e})", file=sys.stderr)
        if args.advisory:
            return 0
        print("FAIL: the sibling could not be reached, so nothing was "
              "compared (pass --advisory to tolerate this)", file=sys.stderr)
        return 1

    live_codes = {c["alpha_2"] for c in live_data.get("countries", {}).get("active", [])}

    added = sorted(live_codes - snap_codes)
    removed = sorted(snap_codes - live_codes)
    codes_ok = not added and not removed

    # Upstream declares its version at meta.version in iso3166.json. The
    # local side is source_version (snapshot and sidecar already agree,
    # checked above). A version bump with an identical code set is
    # "version drift": the label fell behind, the content did not. Version
    # drift is a warning only; it never changes the exit code, even under
    # --strict. Content drift (the code set) is what --strict fails on.
    live_version = live_data.get("meta", {}).get("version")
    if live_version is None:
        print("note: upstream declares no meta.version; version not compared",
              file=sys.stderr)
    version_drift = live_version is not None and live_version != local_version
    if version_drift:
        print(f"warning: version drift: snapshot source_version {local_version}, "
              f"upstream meta.version {live_version}; does not fail.",
              file=sys.stderr)

    if codes_ok:
        if version_drift:
            print(f"OK: code set is current ({len(snap_codes)} codes)")
        else:
            print(f"OK: snapshot is current ({len(snap_codes)} codes, "
                  f"version {local_version})")
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
