#!/usr/bin/env python3
"""Verify every version site agrees.

Sites:
  VERSION                              (text file)
  CHANGELOG.md                         (top released heading)
  iso10383.json                        (meta.version)
  iso10383.parquet                     (footer iso10383.version)
  wrappers/python/pyproject.toml       (version)
  wrappers/python/src/iso10383/__init__.py (__version__)
  wrappers/javascript/package.json     (version)
  wrappers/rust/Cargo.toml             (version)
  README.md                            (badge)

Every site must be present and readable at v1.x. A site that exists but
cannot be read (for example iso10383.parquet when pyarrow is not
installed) is a failure, never a skip.

The schema has its own version, independent of the registry version:
schema.json "version" must equal the README schema badge.

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


class SiteUnreadable(Exception):
    """A site that exists but cannot be read. A failure, never a skip."""


def read_parquet_version() -> str | None:
    p = ROOT / "iso10383.parquet"
    if not p.is_file():
        return None
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SiteUnreadable(
            f"iso10383.parquet exists but pyarrow is not importable "
            f"({exc}); install pyarrow"
        ) from exc
    md = pq.ParquetFile(p).schema_arrow.metadata or {}
    v = md.get(b"iso10383.version")
    if not v:
        raise SiteUnreadable(
            "iso10383.parquet footer has no iso10383.version key")
    return v.decode()


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


def read_python_dunder_version() -> str | None:
    p = ROOT / "wrappers" / "python" / "src" / "iso10383" / "__init__.py"
    if not p.is_file():
        return None
    m = re.search(r'^__version__\s*=\s*"([^"]+)"',
                  p.read_text(encoding="utf-8"), re.MULTILINE)
    if not m:
        raise SiteUnreadable(f"{p.name} has no __version__ assignment")
    return m.group(1)


def read_schema_version() -> str | None:
    p = ROOT / "schema.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("version")


def read_readme_schema_badge() -> str | None:
    p = ROOT / "README.md"
    if not p.is_file():
        return None
    m = re.search(r"badge/schema-([0-9]+\.[0-9]+\.[0-9]+)-",
                  p.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _major(version: str | None) -> int | None:
    try:
        return int((version or "").split(".")[0])
    except ValueError:
        return None


def main() -> int:
    readers = {
        "VERSION": read_version_file,
        "CHANGELOG.md": read_changelog_top,
        "iso10383.json meta.version": read_meta_version,
        "iso10383.parquet footer": read_parquet_version,
        "wrappers/python/pyproject.toml": read_pyproject_version,
        "wrappers/python/src/iso10383/__init__.py":
            read_python_dunder_version,
        "wrappers/javascript/package.json": read_package_json_version,
        "wrappers/rust/Cargo.toml": read_cargo_version,
        "README.md badge": read_readme_badge_version,
    }

    sites: dict[str, str | None] = {}
    unreadable: dict[str, str] = {}
    for name, reader in readers.items():
        try:
            sites[name] = reader()
        except SiteUnreadable as exc:
            sites[name] = None
            unreadable[name] = str(exc)

    present = {k: v for k, v in sites.items() if v is not None}
    missing = [k for k, v in sites.items()
               if v is None and k not in unreadable]

    print("Version sites:")
    for k in sites:
        marker = "  " if sites[k] is not None else (
            "!!" if k in unreadable else "??")
        print(f"  {marker} {k:<40} {sites[k]}")

    failed = False

    if unreadable:
        print(file=sys.stderr)
        for name, reason in unreadable.items():
            print(f"FAIL: {name}: {reason}", file=sys.stderr)
        failed = True

    if missing:
        major = _major(sites.get("VERSION"))
        print()
        if major is not None and major >= 1:
            print("FAIL: sites not present (every site is required at "
                  "v1.x):", file=sys.stderr)
            for k in missing:
                print(f"      {k}", file=sys.stderr)
            failed = True
        else:
            print("Sites not present (allowed while still pre-1.0):")
            for k in missing:
                print(f"      {k}")

    values = set(present.values())
    if len(values) > 1:
        print(file=sys.stderr)
        print(f"FAIL: version mismatch: {sorted(values)}", file=sys.stderr)
        failed = True

    schema_v = read_schema_version()
    badge_v = read_readme_schema_badge()
    print()
    print(f"Schema version: schema.json {schema_v}, README badge {badge_v}")
    if schema_v is None or badge_v is None or schema_v != badge_v:
        print("FAIL: schema.json version and the README schema badge "
              "must both exist and agree", file=sys.stderr)
        failed = True

    if failed:
        return 1

    print()
    print(f"OK: all sites agree on {present['VERSION']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
