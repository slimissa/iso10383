"""Generate tools/iso3166_snapshot.json from the ISO 3166 registry.

Fetches iso3166.json at the tag named in tools/iso3166_snapshot.meta.json
(source_version). Run this manually and commit the result; CI verifies
freshness.

The meta is the source of the pin. Set source_version first, then run
this script; it fetches that tag's URL, verifies the fetched
meta.version, and writes the snapshot. A tag that is not what the meta
claims is refused.
"""

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


def main() -> None:
    version = read_pinned_version()
    url = f"{REPO}/v{version}/iso3166.json"
    print(f"fetching {url}")
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.loads(r.read())
    seen = data.get("meta", {}).get("version")
    if seen != version:
        sys.exit(
            f"v{version}: iso3166.json declares meta.version={seen!r}, "
            f"but the meta pins {version!r}; reconcile before writing"
        )
    active = data.get("countries", {}).get("active", [])
    alpha2 = sorted(c["alpha_2"] for c in active)
    out = {
        "source_url": url,
        "source_version": version,
        "count": len(alpha2),
        "alpha_2_set": alpha2,
    }
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"Wrote {OUT}: {len(alpha2)} codes (from v{version})")


if __name__ == "__main__":
    main()
