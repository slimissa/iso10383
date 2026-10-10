"""Generate tools/exchange_calendar_snapshot.json from Exchange Calendar.

Reads all MICs referenced by the exchanges/ directory of the sibling
repo. Run this manually and commit; CI verifies freshness.

This script writes only exchange_calendar_snapshot.json. The sibling
tools/exchange_calendar_snapshot.meta.json (source_version, vendored_at,
vendored_from, review_by) is maintained by hand, like its ISO 3166
counterpart. It clones the sibling's default branch, so set
source_version and vendored_from to the tag whose HEAD you cloned.
"""
import json, subprocess, tempfile
from pathlib import Path

REPO = "https://github.com/slimissa/exchange-calendar.git"

with tempfile.TemporaryDirectory() as td:
    subprocess.run(
        ["git", "clone", "--depth", "1", REPO, td],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
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
path = Path(__file__).parent / "exchange_calendar_snapshot.json"
path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"Wrote {path}: {len(mics)} MICs")
