#!/usr/bin/env python3
"""scripts/prepare_release.py: the CHANGELOG half of a release (closes RCP-25).
Turns '## [Unreleased]' into '## [VERSION] - DATE', leaves a fresh empty [Unreleased],
and adds the compare link. scripts/release.sh does everything else.
Usage (repo root, on main): python3 scripts/prepare_release.py VERSION DATE [--prev X.Y.Z]
Refuses (writes nothing) if [Unreleased] is not the first '## [' heading, has no real content,
contains a placeholder that release.sh would refuse, or if VERSION already has a section."""
import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"\[(TODO|TBD|PASTE|N|M|K|J)\]")


def prepare(text, version, date, prev=None):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("bad version or date")
    if f"## [{version}]" in text:
        raise ValueError(f"[{version}] already present")
    heads = list(re.finditer(r"^## \[(.+?)\]", text, re.M))
    if not heads or heads[0].group(1) != "Unreleased":
        raise ValueError("[Unreleased] is not the first '## [' heading")
    if len(heads) < 2:
        raise ValueError("no previous release heading")
    prev = prev or heads[1].group(1)
    i, j = heads[0].start(), heads[1].start()
    body = text[i:j].split("\n", 1)[1].strip("\n")
    if body.strip() in ("", "Nothing yet.") or "### " not in body:
        raise ValueError("[Unreleased] has no real content")
    if PLACEHOLDER.search(body):
        raise ValueError("placeholder in the body (release.sh would refuse the tag)")
    sep = bool(re.search(r"\n---\s*$", body))
    body = re.sub(r"\n+---\s*$", "", body).strip("\n")
    s = "---\n\n" if sep else ""
    out = text[:i] + f"## [Unreleased]\n\nNothing yet.\n\n{s}## [{version}] - {date}\n\n{body}\n\n{s}" + text[j:]
    link = f"[{version}]: https://github.com/slimissa/iso10383/compare/v{prev}...v{version}"
    um = re.search(r"^\[Unreleased\]: (.*)$", out, re.M)
    if um:
        out = out.replace(um.group(0), re.sub(r"v[0-9.]+\.\.\.HEAD", f"v{version}...HEAD", um.group(0)), 1)
    pm = re.search(rf"^\[{re.escape(prev)}\]: .*$", out, re.M)
    if pm:
        out = out[:pm.start()] + link + "\n" + out[pm.start():]
    else:
        am = re.search(r"^\[\d+\.\d+\.\d+\]: ", out, re.M)
        out = (out[:am.start()] + link + "\n" + out[am.start():]) if am else out.rstrip("\n") + "\n\n" + link + "\n"
    return out


def main(argv):
    a = [x for x in argv if not x.startswith("--")]
    if len(a) < 2:
        print("usage: prepare_release.py VERSION DATE [--prev X.Y.Z]", file=sys.stderr)
        return 2
    prev = argv[argv.index("--prev") + 1] if "--prev" in argv else None
    p = Path("CHANGELOG.md")
    try:
        new = prepare(p.read_text(encoding="utf-8"), a[0], a[1], prev)
    except ValueError as e:
        print("ABORT, nothing written:", e, file=sys.stderr)
        return 1
    p.write_text(new, encoding="utf-8")
    print(f"ok: [{a[0]}] - {a[1]} created from [Unreleased]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
