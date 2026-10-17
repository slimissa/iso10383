"""Generate tools/iso3166_snapshot.json from the ISO 3166 registry.

Fetches iso3166.json at the tag named in tools/iso3166_snapshot.meta.json
(source_version). Run this manually and commit the result; CI verifies
freshness with --check.

The meta is the source of the pin. Set source_version first, then run
this script; it fetches that tag's URL, verifies the fetched
meta.version, and writes the snapshot. A tag that is not what the meta
claims is refused.

--check fetches the same tag and compares the rendered output against
the committed file byte-for-byte. The render is deterministic (sorted
keys, LF, trailing newline), so byte identity is the correct test.
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

REPO = "https://raw.githubusercontent.com/slimissa/iso3166"
HERE = Path(__file__).parent
META = HERE / "iso3166_snapshot.meta.json"
OUT = HERE / "iso3166_snapshot.json"


def read_pinned_version() -> str:
    meta = json.loads(META.read_text(encoding="utf-8"))
    version = meta.get("source_version")
    if not version:
        sys.exit(f"{META.name}: source_version is missing; set it first")
    return version


def fetch_alpha2(version: str) -> list[str]:
    url = f"{REPO}/v{version}/iso3166.json"
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.loads(r.read())
    seen = data.get("meta", {}).get("version")
    if seen != version:
        sys.exit(
            f"v{version}: iso3166.json declares meta.version={seen!r}, "
            f"but the meta pins {version!r}; reconcile before writing")
    active = data.get("countries", {}).get("active", [])
    return sorted(c["alpha_2"] for c in active)


def build_snapshot(version: str, alpha2: list[str]) -> dict:
    """Pure: the snapshot dict for the given version and codes."""
    return {
        "source_url": f"{REPO}/v{version}/iso3166.json",
        "source_version": version,
        "count": len(alpha2),
        "alpha_2_set": alpha2,
    }


def render(snapshot: dict) -> str:
    return json.dumps(snapshot, indent=2, sort_keys=True) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true",
                   help="Compare the committed snapshot to a fresh build")
    args = p.parse_args()

    version = read_pinned_version()
    alpha2 = fetch_alpha2(version)
    expected = build_snapshot(version, alpha2)
    text = render(expected)

    if args.check:
        if not OUT.is_file():
            print(f"missing: {OUT}", file=sys.stderr)
            return 1
        committed = OUT.read_text(encoding="utf-8")
        if committed == text:
            print(f"OK: {OUT.name} is current "
                  f"({len(alpha2)} codes, v{version})")
            return 0
        print(f"stale: {OUT.name}", file=sys.stderr)
        try:
            cur = json.loads(committed)
            if cur.get("source_version") != version:
                print(f"  source_version: committed {cur.get('source_version')!r}, "
                      f"expected {version!r}", file=sys.stderr)
            if cur.get("count") != len(alpha2):
                print(f"  count: committed {cur.get('count')}, "
                      f"expected {len(alpha2)}", file=sys.stderr)
            added = sorted(set(alpha2) - set(cur.get("alpha_2_set", [])))
            removed = sorted(set(cur.get("alpha_2_set", [])) - set(alpha2))
            if added:
                print(f"  added: {added[:10]}", file=sys.stderr)
            if removed:
                print(f"  removed: {removed[:10]}", file=sys.stderr)
        except json.JSONDecodeError:
            print("  committed file is not valid JSON", file=sys.stderr)
        return 1

    print(f"fetching {REPO}/v{version}/iso3166.json")
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT}: {len(alpha2)} codes (from v{version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
