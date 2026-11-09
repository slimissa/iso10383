#!/usr/bin/env python3
"""Generate registry_release.json: the self-description of one release.

The file lists every artifact a consumer might load (with its SHA-256
and size), the counts the documentation quotes, the source the registry
was derived from, and the vendored snapshots with their pinned versions.
It is generated, never hand-edited: `--check` regenerates in memory and
compares bytes, and `scripts/release.sh` runs both the generation (in the
regeneration step) and `--check` (as the last gate).

Usage:
    python3 tools/gen_registry_release.py [--check] [--version V]
                                          [--tag T] [--out PATH]

    (no flag)   write registry_release.json at the repository root
    --check     regenerate in memory and compare bytes with --out
    --version V release version; must equal VERSION and meta.version
                (default: the contents of VERSION)
    --tag T     git tag name (default: v<version>)
    --out PATH  output path (default: registry_release.json)

Inputs read:
    VERSION, iso10383.json, schema.json, the nine flat exports, the four
    bundled wrapper copies, tools/*_snapshot.json and their .meta.json,
    CHANGELOG.md (the release date), tools/release_claims.json (claim
    counts), tests/test_counts.json (declared test counts, optional).
    docs/v<version>-verification.md is read only to confirm that its
    Commit and Tag object lines are well-formed 40-hex values when the
    file exists.

Design decisions (recorded in the v1.1.2 bundle's SPEC.md):
    * `commit` and `tag_object` are always null in the committed file. The
      file ships inside the release commit and cannot contain that commit's
      SHA, and the tag object does not exist yet. The authoritative values
      are in docs/v<version>-verification.md and in the git tag.
    * `counts.tests` is null when tests/test_counts.json does not exist.
      Documentation must not quote a test count that is not declared there.
    * `distribution` is always "source-only": no wrapper is published.

Exit codes:
    0  generated, or --check matched
    1  --check found the file stale or missing, a verification document is
       malformed, or the output does not match registry_release.schema.json
    2  an input is missing, malformed, or the versions disagree
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "registry_release.json"
SCHEMA = ROOT / "registry_release.schema.json"

REGISTRY = "iso10383"
DISTRIBUTION = "source-only"

LAYER1 = ["iso10383.json", "schema.json"]
LAYER2 = [
    "iso10383.csv", "iso10383.european.csv", "iso10383.excel.csv",
    "iso10383.mysql.sql", "iso10383.parquet", "iso10383.postgresql.sql",
    "iso10383.sql", "iso10383.sqlite.sql", "iso10383.tsv",
]
LAYER3 = [
    "wrappers/go/data/iso10383.json",
    "wrappers/javascript/src/data/iso10383.json",
    "wrappers/python/src/iso10383/data/iso10383.json",
    "wrappers/rust/data/iso10383.json",
]
SNAPSHOTS = [
    "tools/exchange_calendar_snapshot",
    "tools/iso3166_snapshot",
]
TEST_KEYS = ("root", "python", "javascript", "rust", "go")


class InputError(Exception):
    """An input is missing or malformed (exit 2)."""


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as e:
        raise InputError(f"cannot read {path.relative_to(ROOT)}: {e.strerror}")


def _json(rel: str) -> dict:
    try:
        return json.loads(_read(ROOT / rel).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise InputError(f"{rel}: not valid JSON ({e})")


def _entry(rel: str, layer: int) -> dict:
    data = _read(ROOT / rel)
    return {
        "path": rel,
        "layer": layer,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _release_date(version: str) -> str:
    text = _read(ROOT / "CHANGELOG.md").decode("utf-8")
    m = re.search(rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})\s*$",
                  text, flags=re.M)
    if not m:
        raise InputError(
            f"CHANGELOG.md has no heading '## [{version}] - YYYY-MM-DD'; "
            "write the release section (with its date) before generating")
    return m.group(1)


def _tests() -> dict | None:
    p = ROOT / "tests" / "test_counts.json"
    if not p.exists():
        return None
    d = _json("tests/test_counts.json")
    out = {}
    for k in TEST_KEYS:
        v = d.get(k)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            raise InputError(f"tests/test_counts.json: {k!r} must be a "
                             "non-negative integer")
        out[k] = v
    out["total"] = sum(out[k] for k in TEST_KEYS)
    return out


def _claims(version: str) -> dict:
    d = _json("tools/release_claims.json")
    lists = {k: v for k, v in d.items() if isinstance(v, list)}
    facts = len(lists.get("doc-facts", []))
    section = lists.get(version)
    return {
        "doc_facts": facts,
        "in_file": sum(len(v) for v in lists.values()),
        "verified": None if section is None else facts + len(section),
    }


def _check_verification_doc(version: str) -> list[str]:
    p = ROOT / "docs" / f"v{version}-verification.md"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    problems = []
    for label in ("Commit", "Tag object"):
        m = re.search(rf"^{label}:\s*([0-9a-f]{{40}})\s*$", text, flags=re.M)
        if not m:
            problems.append(f"{p.name}: no well-formed '{label}:' line "
                            "(40 lowercase hex characters)")
    return problems


def build(version: str, tag: str) -> dict:
    """Pure with respect to the working tree: same tree, same dict."""
    registry = _json("iso10383.json")
    schema = _json("schema.json")
    meta = registry["meta"]
    version_file = _read(ROOT / "VERSION").decode("utf-8").strip()
    if not (version == version_file == meta.get("version")):
        raise InputError(
            f"version disagreement: --version {version!r}, VERSION "
            f"{version_file!r}, iso10383.json meta.version "
            f"{meta.get('version')!r}")

    mics = registry["mics"]
    by_mic = {m["mic"]: m for m in mics}
    under_segment = sum(
        1 for m in mics
        if m["mic_type"] == "SEGMENT"
        and by_mic[m["operating_mic"]]["mic_type"] == "SEGMENT")
    c = meta["counts"]

    files = [_entry(p, 1) for p in LAYER1]
    files += [_entry(p, 2) for p in LAYER2]
    files += [_entry(p, 3) for p in LAYER3]
    files.sort(key=lambda f: (f["layer"], f["path"]))

    vendors = []
    for stem in SNAPSHOTS:
        sm = _json(f"{stem}.meta.json")
        computed = hashlib.sha256(_read(ROOT / f"{stem}.json")).hexdigest()
        declared = sm.get("snapshot_sha256")
        if declared is not None and declared != computed:
            raise SystemExit(
                f"{stem}.meta.json: snapshot_sha256 {declared} != "
                f"{computed} (actual hash of {stem}.json)")
        vendors.append({
            "name": sm["source"],
            "source_version": sm["source_version"],
            "vendored_at": sm["vendored_at"],
            "file": f"{stem}.json",
            "sha256": computed,
            "review_by": sm["meta"]["review_by"],
        })
    vendors.sort(key=lambda v: v["name"])

    return {
        "registry": REGISTRY,
        "version": version,
        "schema_version": schema["version"],
        "released": _release_date(version),
        "commit": None,
        "tag": tag,
        "tag_object": None,
        "distribution": DISTRIBUTION,
        "source": {
            "name": "SWIFT ISO10383_MIC.csv",
            "url": meta["source_url"],
            "snapshot": meta["source_snapshot"],
            "sha256": meta["source_hash"].removeprefix("sha256:"),
        },
        "files": files,
        "counts": {
            "operating": c["operating"], "segment": c["segment"],
            "active": c["active"], "updated": c["updated"],
            "expired": c["expired"], "total": c["total"],
            "countries": len({m["country_code"] for m in mics}),
            "market_categories": len({m["market_category"] for m in mics}),
            "segments_under_segment": under_segment,
            "broken_chains": len(meta.get("broken_chains", [])),
            "tests": _tests(),
            "claims": _claims(version),
        },
        "vendors": vendors,
    }


def render(d: dict) -> str:
    return json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def schema_problems(d: dict) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return []          # build-time dependency; absent => not validated
    schema = json.loads(_read(SCHEMA).decode("utf-8"))
    v = jsonschema.Draft7Validator(schema)
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in sorted(v.iter_errors(d), key=lambda e: list(e.absolute_path))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--version")
    ap.add_argument("--tag")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    try:
        version = a.version or _read(ROOT / "VERSION").decode("utf-8").strip()
        tag = a.tag or f"v{version}"
        d = build(version, tag)
        text = render(d)
        problems = schema_problems(d) + _check_verification_doc(version)
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if problems:
        for p in problems:
            print(f"error: {p}", file=sys.stderr)
        return 1
    out = a.out
    if a.check:
        try:
            current = out.read_bytes()
        except OSError:
            print(f"STALE: {out} is missing; run: make registry-release",
                  file=sys.stderr)
            return 1
        if current != text.encode("utf-8"):
            print(f"STALE: {out} differs from a fresh generation; run: "
                  "make registry-release", file=sys.stderr)
            return 1
        print(f"OK: {out.name} in sync ({len(d['files'])} files, "
              f"{len(d['vendors'])} vendors, bytes)")
        return 0
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {out}: v{version}, {len(d['files'])} files, "
          f"{len(d['vendors'])} vendors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
