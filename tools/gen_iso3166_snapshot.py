"""Generate tools/iso3166_snapshot.json from the ISO 3166 registry.

Fetches iso3166.json from the canonical repo. Run this manually and
commit the result; CI verifies freshness."""
import json, urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/slimissa/iso3166/main/iso3166.json"

with urllib.request.urlopen(URL, timeout=60) as r:
    data = json.loads(r.read())

active = data.get("countries", {}).get("active", [])
alpha2 = sorted(c["alpha_2"] for c in active)

out = {
    "source_url": URL,
    "source_version": data.get("meta", {}).get("version"),
    "count": len(alpha2),
    "alpha_2_set": alpha2,
}
path = Path(__file__).parent / "iso3166_snapshot.json"
path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"Wrote {path}: {len(alpha2)} codes")
