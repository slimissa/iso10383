#!/usr/bin/env python3
"""
tools/check_release_claims.py

Read tools/release_claims.json and verify every claim for a given
version against the current repository state.

Each claim is one of:

  {"file": "path"}                     — path must exist
  {"file": "path", "contains": "text"} — path must exist and include text
  {"file": "path", "absent": "text"}   — path must not include text
                                         (a missing path passes; pair the
                                         claim with a {"file": "path"}
                                         claim to require the path)

`contains` and `absent` may be combined in one claim. Any other key is
an error: a misspelled key must not silently weaken a claim.

The manifest holds two kinds of section: one list of claims per
released version (checked only for the version named on the command
line), and a "doc-facts" list checked on every run. Doc-facts are
claims about the documentation that must stay true on every commit:
counts, tool names, version strings, structural markers.

Usage:
    python3 tools/check_release_claims.py 1.6.5
    python3 tools/check_release_claims.py 1.6.5 --list
    python3 tools/check_release_claims.py 1.6.5 --json

Exit codes:
    0  all claims verified
    1  at least one claim failed
    2  fatal (manifest missing, version not in manifest, malformed entry)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = PROJECT_ROOT / "tools" / "release_claims.json"


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def load_manifest() -> dict:
    if not MANIFEST.exists():
        raise FatalError(f"manifest not found: {MANIFEST}")
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{MANIFEST}: invalid JSON: {exc}") from exc


ALLOWED_KEYS = {"file", "contains", "absent"}
DOC_FACTS_KEY = "doc-facts"


def describe_claim(claim: object) -> str:
    if not isinstance(claim, dict):
        return f"not an object: {claim!r}"
    parts = [str(claim.get("file", "<no file>"))]
    if "contains" in claim:
        parts.append(f"contains {claim['contains']!r}")
    if "absent" in claim:
        parts.append(f"absent {claim['absent']!r}")
    if len(parts) == 1:
        parts.append("exists")
    return ": ".join([parts[0], ", ".join(parts[1:])])


def check_claim(claim: dict) -> tuple[bool, str]:
    if "file" not in claim:
        return False, "claim has no 'file' key"
    unknown = sorted(set(claim) - ALLOWED_KEYS)
    if unknown:
        return False, (f"{claim['file']}: unknown claim key(s) {unknown}; "
                       f"allowed: contains, absent")
    path = PROJECT_ROOT / claim["file"]
    if not path.exists():
        if "absent" in claim and "contains" not in claim:
            return True, (f"{claim['file']} is missing, so it does not "
                          f"contain {claim['absent']!r}")
        return False, f"missing file: {claim['file']}"
    text = path.read_text(encoding="utf-8")
    notes = []
    if "contains" in claim:
        needle = claim["contains"]
        if needle not in text:
            return False, f"{claim['file']} does not contain {needle!r}"
        notes.append(f"contains {needle!r}")
    if "absent" in claim:
        needle = claim["absent"]
        if needle in text:
            return False, (f"{claim['file']} contains {needle!r}, "
                           f"which must be absent")
        notes.append(f"does not contain {needle!r}")
    if not notes:
        return True, f"{claim['file']} exists"
    return True, f"{claim['file']} " + " and ".join(notes)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="check_release_claims")
    p.add_argument("version")
    p.add_argument("--list", action="store_true",
                   help="Print claims without checking")
    p.add_argument("--json", action="store_true",
                   help="Machine-readable output")
    args = p.parse_args(argv)

    manifest = load_manifest()
    claims = manifest.get(args.version)
    if claims is None:
        raise FatalError(
            f"no claims for version {args.version} in {MANIFEST.name}. "
            f"Every release must have a manifest entry."
        )
    if not isinstance(claims, list):
        raise FatalError(f"claims for {args.version} is not a list")

    doc_facts = manifest.get(DOC_FACTS_KEY, [])
    if not isinstance(doc_facts, list):
        raise FatalError(f"{DOC_FACTS_KEY!r} is not a list")

    labelled = [(args.version, c) for c in claims]
    labelled += [(DOC_FACTS_KEY, c) for c in doc_facts]

    if args.list:
        for section, claim in labelled:
            print(f"[{section}] {describe_claim(claim)}")
        return 0

    results = []
    for section, claim in labelled:
        prefix = "" if section == args.version else f"[{section}] "
        if not isinstance(claim, dict):
            results.append((False, f"{prefix}not an object: {claim!r}"))
            continue
        ok, detail = check_claim(claim)
        results.append((ok, prefix + detail))

    if args.json:
        print(json.dumps({
            "version": args.version,
            "total": len(results),
            "passed": sum(1 for ok, _ in results if ok),
            "failed": sum(1 for ok, _ in results if not ok),
            "results": [{"ok": ok, "detail": d} for ok, d in results],
        }, indent=2))
    else:
        rule = "=" * 60
        print(rule)
        print(f"  release claims — v{args.version}")
        print(rule)
        for ok, detail in results:
            marker = "OK  " if ok else "FAIL"
            print(f"  [{marker}] {detail}")
        print(rule)
        failed = [d for ok, d in results if not ok]
        if failed:
            print(f"  {len(failed)} claim(s) failed")
        else:
            print(f"  all {len(results)} claim(s) verified")

    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
