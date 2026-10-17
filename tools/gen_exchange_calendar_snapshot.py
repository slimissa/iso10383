"""Generate tools/exchange_calendar_snapshot.json from Exchange Calendar.

Reads every MIC referenced by the exchanges/ directory of the sibling
repo, at the tag named in tools/exchange_calendar_snapshot.meta.json
(source_version). Run this manually and commit; CI verifies freshness.

The meta is the source of the pin. Set source_version first, then run
this script; it clones that tag, verifies that the cloned calendar.json
declares the same version, and writes the snapshot. A tag that is not
what the meta claims is refused, so the meta and the content cannot
silently diverge.
"""

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


def main() -> None:
    version = read_pinned_version()
    tag = f"v{version}"
    print(f"cloning {REPO} at {tag}")
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", tag, REPO, td],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        cal = Path(td) / "calendar.json"
        if cal.exists():
            seen = json.loads(cal.read_text(encoding="utf-8")).get(
                "meta", {}).get("version")
            if seen != version:
                sys.exit(
                    f"{tag}: calendar.json declares meta.version={seen!r}, "
                    f"but the meta pins {version!r}; reconcile before writing"
                )
        mics: set[str] = set()
        for f in (Path(td) / "exchanges").glob("*.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("mic"):
                mics.add(d["mic"])
            if d.get("code"):
                mics.add(d["code"])

    out = {
        "source_url": REPO,
        "count": len(mics),
        "mics": sorted(mics),
    }
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"Wrote {OUT}: {len(mics)} MICs (from {tag})")


if __name__ == "__main__":
    main()
