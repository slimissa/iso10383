"""Generate tools/exchange_calendar_snapshot.json from Exchange Calendar.

Reads every MIC referenced by the exchanges/ directory of the sibling
repo at the tag named in tools/exchange_calendar_snapshot.meta.json
(source_version). Run this manually and commit; CI verifies freshness
with --check.

--check clones the same tag and compares the rendered output against
the committed file byte-for-byte.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "https://github.com/slimissa/exchange-calendar.git"
HERE = Path(__file__).parent
META = HERE / "exchange_calendar_snapshot.meta.json"
OUT = HERE / "exchange_calendar_snapshot.json"


def read_pinned_version() -> str:
    meta = json.loads(META.read_text(encoding="utf-8"))
    version = meta.get("source_version")
    if not version:
        sys.exit(f"{META.name}: source_version is missing; set it first")
    return version


def fetch_mics(version: str) -> list[str]:
    tag = f"v{version}"
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", tag, REPO, td],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cal = Path(td) / "calendar.json"
        if cal.exists():
            seen = json.loads(cal.read_text(encoding="utf-8")).get(
                "meta", {}).get("version")
            if seen != version:
                sys.exit(
                    f"{tag}: calendar.json declares meta.version={seen!r}, "
                    f"but the meta pins {version!r}; reconcile before writing")
        mics: set[str] = set()
        for f in (Path(td) / "exchanges").glob("*.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("mic"):
                mics.add(d["mic"])
            if d.get("code"):
                mics.add(d["code"])
    return sorted(mics)


def build_snapshot(version: str, mics: list[str]) -> dict:
    return {
        "source_url": REPO,
        "source_version": version,
        "count": len(mics),
        "mics": mics,
    }


def render(snapshot: dict) -> str:
    return json.dumps(snapshot, indent=2, sort_keys=True) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true",
                   help="Compare the committed snapshot to a fresh build")
    args = p.parse_args()

    version = read_pinned_version()
    mics = fetch_mics(version)
    expected = build_snapshot(version, mics)
    text = render(expected)

    if args.check:
        if not OUT.is_file():
            print(f"missing: {OUT}", file=sys.stderr)
            return 1
        committed = OUT.read_text(encoding="utf-8")
        if committed == text:
            print(f"OK: {OUT.name} is current ({len(mics)} MICs, v{version})")
            return 0
        print(f"stale: {OUT.name}", file=sys.stderr)
        try:
            cur = json.loads(committed)
            added = sorted(set(mics) - set(cur.get("mics", [])))
            removed = sorted(set(cur.get("mics", [])) - set(mics))
            if added:
                print(f"  added: {added[:10]}", file=sys.stderr)
            if removed:
                print(f"  removed: {removed[:10]}", file=sys.stderr)
        except json.JSONDecodeError:
            print("  committed file is not valid JSON", file=sys.stderr)
        return 1

    print(f"cloning {REPO} at v{version}")
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT}: {len(mics)} MICs (from v{version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
