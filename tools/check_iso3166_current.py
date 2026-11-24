#!/usr/bin/env python3
"""Compare tools/iso3166_snapshot.json against the ISO 3166 registry at
the sibling's latest release tag.

The upstream side is iso3166.json at the highest vX.Y.Z tag of
slimissa/iso3166 (git ls-remote; tools/sibling_tags.py), never main:
unreleased work on the sibling's main does not reach this check. The tag
is cross-checked against the file's meta.version; if they disagree, FAIL.

Exit 0 if in sync. Exit 1 if drifted and --strict.

Exit 1 if the sibling is unreachable: a comparison that could not run is
not a pass (docs/RELEASE_PATTERN.md, operator-hygiene rule 7). Pass
--advisory to exit 0 in that case instead; the note still prints.

Exit 1 if the file at the tag cannot be read as expected (missing file,
missing key, or an empty code set): "upstream format changed at vX.Y.Z".
That is never reported as stale and never passes, even with --advisory.

Advisory in v1.0.0 per D6. Blocking in v1.0.1.

Compares two things: the alpha-2 code set, and the version label
(snapshot source_version vs the tag's version). A code-set difference
fails under --strict. A version difference is only a warning on stderr
("version drift") and fails only with --fail-on-version-drift (the
release gate; docs/RELEASE_PATTERN.md).
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import sibling_tags

SNAPSHOT = Path(__file__).parent / "iso3166_snapshot.json"
LOCAL_META = Path(__file__).parent / "iso3166_snapshot.meta.json"
REPO = "https://github.com/slimissa/iso3166.git"
RAW = "https://raw.githubusercontent.com/slimissa/iso3166"


def tag_url(tag: str) -> str:
    """iso3166.json at a tag: the URL form gen_iso3166_snapshot.py uses."""
    return f"{RAW}/{tag}/iso3166.json"


class FormatChanged(Exception):
    """The file at the tag is not in the shape this check reads."""


def read_upstream(data) -> tuple[set[str], str]:
    """(alpha-2 set, meta.version) from iso3166.json; FormatChanged if unreadable."""
    if not isinstance(data, dict):
        raise FormatChanged("iso3166.json is not a JSON object")
    countries = data.get("countries")
    if not isinstance(countries, dict) or "active" not in countries:
        raise FormatChanged("key countries.active is missing")
    active = countries["active"]
    if not isinstance(active, list):
        raise FormatChanged("countries.active is not a list")
    codes = set()
    for c in active:
        if not isinstance(c, dict) or "alpha_2" not in c:
            raise FormatChanged("an entry of countries.active has no alpha_2")
        codes.add(c["alpha_2"])
    if not codes:
        raise FormatChanged("countries.active yields an empty alpha-2 set")
    version = data.get("meta", {}).get("version") if isinstance(data.get("meta"), dict) else None
    if not version:
        raise FormatChanged("key meta.version is missing")
    return codes, version


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
        with urllib.request.urlopen(tag_url(tag), timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"FAIL: upstream format changed at {tag}: iso3166.json "
                  f"not found at the tag ({tag_url(tag)})", file=sys.stderr)
            return 1
        return unreachable(e)
    except Exception as e:
        return unreachable(e)
    try:
        live_codes, file_version = read_upstream(json.loads(raw))
    except json.JSONDecodeError:
        print(f"FAIL: upstream format changed at {tag}: iso3166.json is "
              f"not valid JSON", file=sys.stderr)
        return 1
    except FormatChanged as e:
        print(f"FAIL: upstream format changed at {tag}: {e}", file=sys.stderr)
        return 1
    if file_version != tag_version:
        print(f"FAIL: tag {tag} but iso3166.json meta.version is "
              f"{file_version!r}; the sibling's tag and file disagree",
              file=sys.stderr)
        return 1

    added = sorted(live_codes - snap_codes)
    removed = sorted(snap_codes - live_codes)
    codes_ok = not added and not removed

    # The upstream version is the tag's, already cross-checked against
    # iso3166.json meta.version above. The local side is source_version
    # (snapshot and sidecar already agree, checked above). A version bump
    # with an identical code set is "version drift": the label fell behind,
    # the content did not. It is a warning; only --fail-on-version-drift
    # (the release gate) fails on it. Content drift (the code set) is what
    # --strict fails on.
    live_version = tag_version
    version_drift = live_version != local_version
    if version_drift:
        if getattr(args, "fail_on_version_drift", False):
            print(f"FAIL: version drift with --fail-on-version-drift "
                  f"(snapshot {local_version}, upstream {tag})",
                  file=sys.stderr)
            return 1
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
