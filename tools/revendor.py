#!/usr/bin/env python3
"""Re-vendor a sibling snapshot in one command.

    python3 tools/revendor.py {iso3166|exchange_calendar|all} \
        [--to X.Y.Z | --latest] [--date YYYY-MM-DD] [--check]

For each sibling, in this order:
  (a) resolve the target version: --to X.Y.Z, or --latest (the default),
      the sibling's highest vX.Y.Z tag (tools/sibling_tags.py);
  (b) set the top-level source_version in tools/<sibling>_snapshot.meta.json;
  (c) run the existing generator's own functions (fetch, build_snapshot,
      render) and write tools/<sibling>_snapshot.json;
  (d) recompute upstream_sha256 from the tag, as README section 9 states:
      Exchange Calendar = SHA-256 of checksums.json at the tag,
      ISO 3166 = SHA-256 of iso3166.json at the tag;
  (e) set snapshot_sha256, vendored_from and vendored_at (--date, default
      today in UTC);
  (f) set meta.review_by = vendored_at + 1 cadence period (tools/cadence.py),
      keeping meta.refresh_cadence as it is;
  (g) write source, source_version and vendored_at at the top level and in
      "meta", equal;
  (h) print a summary: version, set change, dates, hashes.

--check writes nothing. It exits 1 if a re-vendor would change the version,
the snapshot or a hash, and 0 if the snapshot is already current. The dates
are compared only when --date is given (without it, "today" would always
differ from the recorded vendored_at).

It writes only the two files per sibling named above. iso10383.json, the
exports, CHANGELOG.md and tools/release_claims.json stay human steps; a
reminder lists them. --to needs a single sibling (the two siblings have
unrelated version numbers). Exit 2 on a usage error.
"""

import argparse
import hashlib
import importlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cadence  # noqa: E402
import sibling_tags  # noqa: E402

ROOT = HERE.parent  # tests point this at a scratch tree

SIBLINGS = {
    "iso3166": {
        "generator": "gen_iso3166_snapshot",
        "fetch": "fetch_alpha2",
        "set_key": "alpha_2_set",
        "repo": "https://github.com/slimissa/iso3166.git",
        "upstream_url": "https://raw.githubusercontent.com/slimissa/iso3166/v{v}/iso3166.json",
        "vendored_from": "https://github.com/slimissa/iso3166/blob/v{v}/iso3166.json",
    },
    "exchange_calendar": {
        "generator": "gen_exchange_calendar_snapshot",
        "fetch": "fetch_mics",
        "set_key": "mics",
        "repo": "https://github.com/slimissa/exchange-calendar.git",
        "upstream_url": "https://raw.githubusercontent.com/slimissa/exchange-calendar/v{v}/checksums.json",
        "vendored_from": "https://github.com/slimissa/exchange-calendar/blob/v{v}/calendar.json",
    },
}

REMINDER = """\
Still manual (revendor.py never touches them):
  - CHANGELOG.md [Unreleased]: versions from -> to, set change, both upstream_sha256
  - tools/release_claims.json: the next version's source_version claims
  - if a set changed: python3 tools/validate.py and the iso10383.json cross-checks
  - python3 -m pytest tests/ -q, then the release (scripts/release.sh)"""


def fetch_bytes(url: str) -> bytes:
    """The file the sibling publishes at a tag (raw.githubusercontent.com)."""
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def plan(name: str, version: str, vendored_at: str) -> dict:
    """Everything a re-vendor of `name` to `version` would write. No writes."""
    s = SIBLINGS[name]
    tools = ROOT / "tools"
    meta_path = tools / f"{name}_snapshot.meta.json"
    snap_path = tools / f"{name}_snapshot.json"
    meta_text = meta_path.read_text(encoding="utf-8")
    meta = json.loads(meta_text)
    cad = meta.get("meta", {}).get("refresh_cadence")
    if cad not in cadence.CADENCE_MONTHS:
        raise SystemExit(f"{meta_path.name}: meta.refresh_cadence {cad!r} is not one of "
                         f"{sorted(cadence.CADENCE_MONTHS)}; set it first")

    # (c) the generator's own functions: fetch at the tag (it refuses a tag
    # whose file declares another meta.version), build, render.
    gen = importlib.import_module(s["generator"])
    items = getattr(gen, s["fetch"])(version)
    snap_text = gen.render(gen.build_snapshot(version, items))

    # (d) upstream_sha256, from the tag
    upstream = sha256(fetch_bytes(s["upstream_url"].format(v=version)))

    # (b), (e), (f), (g): same key order as the committed file
    new = json.loads(meta_text)
    new["source_version"] = version
    new["vendored_at"] = vendored_at
    new["vendored_from"] = s["vendored_from"].format(v=version)
    new["upstream_sha256"] = upstream
    new["snapshot_sha256"] = sha256(snap_text.encode("utf-8"))
    m = new.setdefault("meta", {})
    m["source"] = new.get("source", m.get("source"))
    m["source_version"] = version
    m["vendored_at"] = vendored_at
    m["review_by"] = cadence.review_by(vendored_at, cad)
    m["refresh_cadence"] = cad
    new_meta_text = json.dumps(new, indent=2, ensure_ascii=False) + "\n"

    old_snap_text = snap_path.read_text(encoding="utf-8") if snap_path.is_file() else ""
    old_items = set(json.loads(old_snap_text).get(s["set_key"], [])) if old_snap_text else set()
    return {
        "name": name, "meta_path": meta_path, "snap_path": snap_path,
        "old_meta": meta, "new_meta": new,
        "old_meta_text": meta_text, "new_meta_text": new_meta_text,
        "old_snap_text": old_snap_text, "new_snap_text": snap_text,
        "added": sorted(set(items) - old_items), "removed": sorted(old_items - set(items)),
    }


DATE_KEYS = {"vendored_at", "review_by"}


def _without_dates(d: dict) -> dict:
    out = {k: v for k, v in d.items() if k not in DATE_KEYS}
    if isinstance(out.get("meta"), dict):
        out["meta"] = {k: v for k, v in out["meta"].items() if k not in DATE_KEYS}
    return out


def is_current(p: dict, compare_dates: bool) -> bool:
    if p["new_snap_text"] != p["old_snap_text"]:
        return False
    if compare_dates:
        return p["new_meta_text"] == p["old_meta_text"]
    return _without_dates(p["new_meta"]) == _without_dates(p["old_meta"])


def summary(p: dict) -> str:
    o, n = p["old_meta"], p["new_meta"]
    sets = "no set change" if not (p["added"] or p["removed"]) else \
        f"set change: added {p['added'] or 'none'}, removed {p['removed'] or 'none'}"
    return "\n".join([
        f"{p['name']}: {o.get('source_version')} -> {n['source_version']}; {sets}",
        f"  vendored_at {o.get('vendored_at')} -> {n['vendored_at']}, "
        f"review_by {o.get('meta', {}).get('review_by')} -> {n['meta']['review_by']} "
        f"({n['meta']['refresh_cadence']})",
        f"  vendored_from {n['vendored_from']}",
        f"  upstream_sha256 {n['upstream_sha256']}",
        f"  snapshot_sha256 {n['snapshot_sha256']}",
    ])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sibling", choices=[*SIBLINGS, "all"])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--to", metavar="X.Y.Z", help="target version (one sibling only)")
    g.add_argument("--latest", action="store_true",
                   help="the sibling's highest vX.Y.Z tag (the default)")
    ap.add_argument("--date", metavar="YYYY-MM-DD",
                    help="vendored_at (default: today in UTC)")
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 if a re-vendor would change anything")
    args = ap.parse_args(argv)

    names = list(SIBLINGS) if args.sibling == "all" else [args.sibling]
    if args.to is not None:
        if len(names) != 1:
            ap.error("--to needs a single sibling; the siblings' versions are unrelated")
        if not sibling_tags.TAG_RE.match(f"refs/tags/v{args.to}"):
            ap.error(f"--to {args.to!r} is not X.Y.Z")
    if args.date is not None:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            ap.error(f"--date {args.date!r} is not YYYY-MM-DD")
    vendored_at = args.date or today_utc()

    plans = []
    for name in names:
        version = args.to or sibling_tags.latest_semver_tag(SIBLINGS[name]["repo"])[1:]
        plans.append(plan(name, version, vendored_at))

    if args.check:
        behind = [p for p in plans if not is_current(p, compare_dates=args.date is not None)]
        for p in plans:
            state = "would change" if p in behind else "current"
            print(f"{p['name']}: {state} (snapshot {p['old_meta'].get('source_version')}, "
                  f"target {p['new_meta']['source_version']})")
            if p in behind:
                print(summary(p))
        return 1 if behind else 0

    for p in plans:
        p["snap_path"].write_text(p["new_snap_text"], encoding="utf-8")
        p["meta_path"].write_text(p["new_meta_text"], encoding="utf-8")
        print(summary(p))
    print(REMINDER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
