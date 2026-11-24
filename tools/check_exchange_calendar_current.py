#!/usr/bin/env python3
"""Compare tools/exchange_calendar_snapshot.json against the Exchange
Calendar registry at the sibling's latest release tag.

The upstream side is a shallow clone of slimissa/exchange-calendar at
its highest vX.Y.Z tag (git ls-remote; tools/sibling_tags.py), never
main: unreleased work on the sibling's main does not reach this check.
The tag is cross-checked against calendar.json meta.version; if they
disagree, FAIL.

Exit 0 if in sync. Exit 1 if drifted and --strict.

Exit 1 if the sibling is unreachable: a comparison that could not run is
not a pass (docs/RELEASE_PATTERN.md, operator-hygiene rule 7). Pass
--advisory to exit 0 in that case instead; the note still prints.

Exit 1 if the tree at the tag cannot be read as expected (missing
exchanges/ or calendar.json, a missing key, or an empty MIC set):
"upstream format changed at vX.Y.Z". That is never reported as stale and
never passes, even with --advisory.

Compares two things: the MIC set, and the version label (sidecar
source_version vs the tag's version). A MIC-set difference fails under
--strict. A version difference is only a warning on stderr ("version
drift") and fails only with --fail-on-version-drift (the release gate;
docs/RELEASE_PATTERN.md).
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import sibling_tags

SNAPSHOT = Path(__file__).parent / "exchange_calendar_snapshot.json"
LOCAL_META = Path(__file__).parent / "exchange_calendar_snapshot.meta.json"
REPO = "https://github.com/slimissa/exchange-calendar.git"


class FormatChanged(Exception):
    """The tree at the tag is not in the shape this check reads."""


def read_upstream(root: Path) -> tuple[set[str], str]:
    """(MIC set, calendar.json meta.version) from a checkout; FormatChanged if unreadable.

    The MIC set is read exactly as gen_exchange_calendar_snapshot.py reads
    it: the mic and code fields of every exchanges/*.json.
    """
    ex = root / "exchanges"
    if not ex.is_dir():
        raise FormatChanged("directory exchanges/ is missing")
    mics = set()
    for f in sorted(ex.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raise FormatChanged(f"exchanges/{f.name} is not valid JSON")
        if not isinstance(d, dict):
            raise FormatChanged(f"exchanges/{f.name} is not a JSON object")
        if d.get("mic"):
            mics.add(d["mic"])
        if d.get("code"):
            mics.add(d["code"])
    if not mics:
        raise FormatChanged("exchanges/*.json yields an empty MIC set "
                            "(no mic or code key)")
    cal = root / "calendar.json"
    if not cal.is_file():
        raise FormatChanged("calendar.json is missing")
    try:
        meta = json.loads(cal.read_text(encoding="utf-8")).get("meta")
    except (json.JSONDecodeError, AttributeError):
        raise FormatChanged("calendar.json is not a JSON object")
    version = meta.get("version") if isinstance(meta, dict) else None
    if not version:
        raise FormatChanged("key meta.version is missing from calendar.json")
    return mics, version


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--fail-on-version-drift", action="store_true",
                   help="Treat version drift as a failure (release gate only).")
    p.add_argument("--advisory", action="store_true",
                   help="Exit 0 when the sibling is unreachable, instead "
                        "of failing")
    args = p.parse_args(argv)

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snap_mics = set(snap["mics"])
    local_version = json.loads(
        LOCAL_META.read_text(encoding="utf-8")).get("source_version")

    def unreachable(e) -> int:
        print(f"note: sibling unreachable ({e})", file=sys.stderr)
        if args.advisory:
            return 0
        print("FAIL: the sibling could not be reached, so nothing was "
              "compared (pass --advisory to tolerate this)", file=sys.stderr)
        return 1

    try:
        tag = sibling_tags.latest_semver_tag(REPO)
    except sibling_tags.NoReleaseTag as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        return unreachable(e)
    tag_version = tag[1:]
    print(f"upstream version: {tag} (latest release tag of {REPO})")

    try:
        with tempfile.TemporaryDirectory() as td:
            # Same clone form as gen_exchange_calendar_snapshot.py.
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", tag, REPO, td],
                check=True, capture_output=True,
            )
            live_mics, file_version = read_upstream(Path(td))
    except FormatChanged as e:
        print(f"FAIL: upstream format changed at {tag}: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        return unreachable(e)
    if file_version != tag_version:
        print(f"FAIL: tag {tag} but calendar.json meta.version is "
              f"{file_version!r}; the sibling's tag and file disagree",
              file=sys.stderr)
        return 1
    # The upstream version is the tag's, cross-checked just above.
    live_version = tag_version

    added = sorted(live_mics - snap_mics)
    removed = sorted(snap_mics - live_mics)
    mics_ok = not added and not removed

    version_drift = live_version != local_version
    if version_drift:
        if getattr(args, "fail_on_version_drift", False):
            print(f"FAIL: version drift with --fail-on-version-drift "
                  f"(snapshot {local_version}, upstream {tag})",
                  file=sys.stderr)
            return 1
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
