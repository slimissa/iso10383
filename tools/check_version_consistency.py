#!/usr/bin/env python3
"""Verify every version site agrees.

Sites:
  VERSION                              (text file)
  CHANGELOG.md                         (top released heading)
  iso10383.json                        (meta.version)
  iso10383.parquet                     (footer iso10383.version)
  wrappers/python/pyproject.toml       (version)
  wrappers/javascript/package.json     (version)
  wrappers/rust/Cargo.toml             (version)
  README.md                            (badge, if present)

Exit 0 if all agree, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_version_file() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def read_changelog_top() -> str | None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    # The top released heading: skip [Unreleased].
    for m in re.finditer(r"^## \[([^\]]+)\]", text, re.MULTILINE):
        tag = m.group(1)
        if tag.lower() == "unreleased":
            continue
        return tag
    return None


def read_meta_version() -> str | None:
    p = ROOT / "iso10383.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))["meta"]["version"]


def read_parquet_version() -> str | None:
    p = ROOT / "iso10383.parquet"
    if not p.is_file():
        return None
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return None
    md = pq.ParquetFile(p).schema_arrow.metadata or {}
    v = md.get(b"iso10383.version")
    return v.decode() if v else None


def read_pyproject_version() -> str | None:
    p = ROOT / "wrappers" / "python" / "pyproject.toml"
    if not p.is_file():
        return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', p.read_text(encoding="utf-8"),
                  re.MULTILINE)
    return m.group(1) if m else None


def read_package_json_version() -> str | None:
    p = ROOT / "wrappers" / "javascript" / "package.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("version")


def read_cargo_version() -> str | None:
    p = ROOT / "wrappers" / "rust" / "Cargo.toml"
    if not p.is_file():
        return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', p.read_text(encoding="utf-8"),
                  re.MULTILINE)
    return m.group(1) if m else None


def read_readme_badge_version() -> str | None:
    p = ROOT / "README.md"
    if not p.is_file():
        return None
    text = p.read_text(encoding="utf-8")
    m = re.search(r"badge/registry-([0-9]+\.[0-9]+\.[0-9]+)-", text)
    return m.group(1) if m else None


def main() -> int:
    sites = {
        "VERSION": read_version_file(),
        "CHANGELOG.md": read_changelog_top(),
        "iso10383.json meta.version": read_meta_version(),
        "iso10383.parquet footer": read_parquet_version(),
        "wrappers/python/pyproject.toml": read_pyproject_version(),
        "wrappers/javascript/package.json": read_package_json_version(),
        "wrappers/rust/Cargo.toml": read_cargo_version(),
        "README.md badge": read_readme_badge_version(),
    }

    present = {k: v for k, v in sites.items() if v is not None}
    missing = [k for k, v in sites.items() if v is None]

    print("Version sites:")
    for k in sites:
        marker = "  " if sites[k] is not None else "??"
        print(f"  {marker} {k:<40} {sites[k]}")

    if missing:
        print()
        print("Sites not present (allowed while still pre-1.0):")
        for k in missing:
            print(f"      {k}")

    values = set(present.values())
    if len(values) > 1:
        print(file=sys.stderr)
        print(f"FAIL: version mismatch: {sorted(values)}", file=sys.stderr)
        return 1

    print()
    print(f"OK: all present sites agree on {present['VERSION']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
