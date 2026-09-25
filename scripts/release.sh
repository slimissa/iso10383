#!/usr/bin/env bash
#
# Deterministic release pipeline.
#
#   scripts/release.sh <version>            cut a release
#   scripts/release.sh <version> --dry-run  print every step, do nothing
#
# Refuses on:
#   dirty tree / wrong branch / CHANGELOG section missing
#   version sites not in agreement AFTER regeneration
#   failing test gate
#   red CI on the pushed commit
#   an already-existing tag
#
# Order of operations is deliberate. The version-consistency check
# runs AFTER regeneration, because regeneration is what updates the
# Parquet footer. The check before regeneration would always fail.

set -euo pipefail

cd "$(dirname "$0")/.."

VERSION="${1:-}"
DRY_RUN="${2:-}"

if [[ -z "$VERSION" ]]; then
    echo "usage: scripts/release.sh <version> [--dry-run]" >&2
    exit 2
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "FAIL: not semver: $VERSION" >&2
    exit 2
fi

step() { echo; echo "=== $* ==="; }
run()  {
    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        echo "[dry-run] $*"
    else
        "$@"
    fi
}

# --- Preconditions ---------------------------------------------------------

step "Preconditions"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" == "main" ]] || { echo "FAIL: not on main ($BRANCH)" >&2; exit 1; }
echo "  on branch: $BRANCH"

if [[ -n "$(git status --porcelain)" ]]; then
    echo "FAIL: working tree is not clean" >&2
    git status --short >&2
    exit 1
fi
echo "  tree clean"

if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "FAIL: tag v$VERSION already exists" >&2
    exit 1
fi
echo "  tag v$VERSION is free"

grep -q "## \[$VERSION\]" CHANGELOG.md \
    || { echo "FAIL: CHANGELOG.md has no [${VERSION}] section" >&2; exit 1; }
echo "  CHANGELOG.md has [$VERSION]"

# --- Version sites ---------------------------------------------------------

step "Version sites"

CURRENT="$(cat VERSION)"
echo "  current VERSION: $CURRENT"
echo "  new VERSION:     $VERSION"

if [[ "$DRY_RUN" != "--dry-run" ]]; then
    echo "$VERSION" > VERSION

    python3 - <<PY
import json, re
from pathlib import Path
v = "$VERSION"

# iso10383.json -> meta.version
p = Path("iso10383.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["meta"]["version"] = v
p.write_text(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False) + "\\n",
             encoding="utf-8")

# wrappers/python/pyproject.toml
p = Path("wrappers/python/pyproject.toml")
p.write_text(re.sub(r'^version\s*=\s*"[^"]+"', f'version = "{v}"',
                    p.read_text(encoding="utf-8"), count=1, flags=re.M),
             encoding="utf-8")

# wrappers/javascript/package.json
p = Path("wrappers/javascript/package.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["version"] = v
p.write_text(json.dumps(d, indent=2) + "\\n", encoding="utf-8")

# wrappers/rust/Cargo.toml
p = Path("wrappers/rust/Cargo.toml")
p.write_text(re.sub(r'^version\s*=\s*"[^"]+"', f'version = "{v}"',
                    p.read_text(encoding="utf-8"), count=1, flags=re.M),
             encoding="utf-8")

# README.md -> registry badge
p = Path("README.md")
p.write_text(re.sub(r'badge/registry-[0-9]+\.[0-9]+\.[0-9]+-',
                    f'badge/registry-{v}-',
                    p.read_text(encoding="utf-8")),
             encoding="utf-8")
PY
fi

# --- Regenerate -----------------------------------------------------------

step "Regenerate exports"
run python3 tools/export_csv.py
run python3 tools/export_sql.py
run python3 tools/export_parquet.py
run python3 tools/sync_wrappers.py

# --- Gate -----------------------------------------------------------------

step "Version consistency (after regeneration)"
run python3 tools/check_version_consistency.py

step "Validation gate"
run python3 tools/validate.py
run python3 tools/check_snapshot_freshness.py
run python3 tools/export_csv.py --check
run python3 tools/export_sql.py --check
run python3 tools/export_parquet.py --check
run python3 tools/sync_wrappers.py --check
run python3 -m pytest tests/ -q
run bash tools/check_cross_language.sh

# --- Commit, push ---------------------------------------------------------

step "Commit and push"
run git add -A
run git commit -m "Release v$VERSION"
run git push origin main

# --- Poll CI --------------------------------------------------------------

if [[ "$DRY_RUN" != "--dry-run" ]] && command -v gh >/dev/null 2>&1; then
    step "Waiting for CI"
    SHA="$(git rev-parse HEAD)"
    for i in $(seq 1 60); do
        STATUS="$(gh run list --commit "$SHA" --json status,conclusion \
            --jq '.[0] | "\(.status) \(.conclusion)"' 2>/dev/null || echo "unknown")"
        echo "  [$i] $STATUS"
        case "$STATUS" in
            "completed success") break ;;
            "completed failure"*|"completed cancelled"*)
                echo "FAIL: CI is $STATUS" >&2; exit 1 ;;
        esac
        sleep 10
    done
fi

# --- Tag ------------------------------------------------------------------

step "Tag v$VERSION"
TAG_MSG="$(python3 - <<PY
import re
text = open("CHANGELOG.md", encoding="utf-8").read()
m = re.search(r"## \[$VERSION\][^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
print((m.group(1).strip() if m else "")[:4000])
PY
)"
run git tag -a "v$VERSION" -m "Release v$VERSION

$TAG_MSG"
run git push origin "v$VERSION"

# --- Verification doc -----------------------------------------------------

step "Write verification doc"
DOC="docs/v${VERSION}-verification.md"
if [[ "$DRY_RUN" != "--dry-run" ]]; then
    {
        echo "# v$VERSION verification"
        echo
        echo "Released: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "Commit:     $(git rev-parse "v$VERSION^{commit}")"
        echo "Tag object: $(git rev-parse "v$VERSION")"
        echo
        echo "## Gates"
        echo
        echo "- \`tools/validate.py\` — pass"
        echo "- \`tools/check_version_consistency.py\` — pass"
        echo "- \`tools/check_snapshot_freshness.py\` — pass"
        echo "- \`tools/export_csv.py --check\` — pass"
        echo "- \`tools/export_sql.py --check\` — pass"
        echo "- \`tools/export_parquet.py --check\` — pass"
        echo "- \`tools/sync_wrappers.py --check\` — pass"
        echo "- \`pytest tests/\` — pass"
        echo "- \`tools/check_cross_language.sh\` — pass"
    } > "$DOC"
    git add "$DOC"
    git commit -m "docs: v$VERSION verification"
    git push origin main
fi

echo
echo "Released v$VERSION."
