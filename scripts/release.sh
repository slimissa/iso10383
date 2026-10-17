#!/usr/bin/env bash
#
# Deterministic release pipeline.
#
#   scripts/release.sh <version>            cut a release
#   scripts/release.sh <version> --dry-run  print every step without
#                                            changing files or pushing.
#                                            Read-only checks (git fetch,
#                                            git ls-remote, gh availability,
#                                            branch and tree checks) still run.
#
# Refuses on:
#   dirty tree / wrong branch / CHANGELOG section missing
#   HEAD different from a freshly fetched origin/main
#   VERSION already equal to the target
#   version sites not in agreement AFTER regeneration
#   failing test gate
#   red CI on the pushed commit
#   the gh CLI missing (CI could not be polled, so nothing is tagged)
#   an already-existing tag (local or on origin)
#
# Order of operations is deliberate. The version-consistency check
# runs AFTER regeneration, because regeneration is what updates the
# Parquet footer. The check before regeneration would always fail.
#
# Conforms to docs/RELEASE_PATTERN.md (eight invariants).
#
# Step 4 shape: multi-generator. Four generators (export_csv,
# export_sql, export_parquet, sync_wrappers) regenerate thirteen
# artifacts: nine distribution exports and four wrapper copies of
# iso10383.json. check_version_consistency.py then compares all
# nine version sites. Each generator is re-run with --check in the
# gate; that catches a generator that is not deterministic, not
# drift against HEAD (the files were just regenerated). See
# RELEASE_PATTERN.md, "Two shapes of step 4".
#
# Divergences:
#   - poll scope: one per-push workflow (validate.yml). When a second
#     is added, port ISO 4217's check_workflows_covered.
#   - tag-move procedure: ADR 0005 § Scope. Recovery-only.

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

check_no_orphan_variables() {
    # A variable expanded in a heredoc but never assigned fails at
    # expansion time under set -u. By then the release has started.
    # This runs before step 0 and warns on the class.
    #
    # Adapted from ISO 3166 v1.6.3.
    local orphans
    orphans="$(grep -nE '\$\{[A-Z_]+\}|\$[A-Z_]{3,}' scripts/release.sh \
        | grep -vE '^\s*#' \
        | grep -oE '\$\{?[A-Z_]+' \
        | sort -u \
        | while read -r v; do
            v="${v#\$}"
            v="${v#\{}"
            if ! grep -qE "(^|\s)${v}=" scripts/release.sh; then
                echo "$v"
            fi
        done || true)"

    if [ -n "$orphans" ]; then
        echo "  WARN orphan variables (expanded nowhere assigned):"
        echo "$orphans" | sed 's/^/    /'
    fi
}

step() { echo; echo "=== $* ==="; }
run()  {
    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        echo "[dry-run] $*"
    else
        "$@"
    fi
}

# gate: run a gate command, record "<exit code>|<command>" for the
# verification doc, and stop the release if it failed. The doc is written
# from this log, so a gate added here cannot be missing from the doc.
GATE_LOG=()
gate() {
    local rc=0
    run "$@" || rc=$?
    GATE_LOG+=("$rc|$*")
    if [[ "$rc" -ne 0 ]]; then
        echo "FAIL: gate failed (exit $rc): $*" >&2
        exit "$rc"
    fi
}

# --- Preconditions ---------------------------------------------------------

step "Preconditions"

check_no_orphan_variables

git fetch origin main \
    || { echo "FAIL: git fetch origin main failed" >&2; exit 1; }
echo "  fetched origin/main"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" == "main" ]] || { echo "FAIL: not on main ($BRANCH)" >&2; exit 1; }
echo "  on branch: $BRANCH"

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse origin/main)"
[[ "$LOCAL_SHA" == "$REMOTE_SHA" ]] || {
    echo "FAIL: HEAD ($LOCAL_SHA) != origin/main ($REMOTE_SHA)" >&2
    exit 1
}
echo "  HEAD matches origin/main"

if [[ -n "$(git status --porcelain)" ]]; then
    echo "FAIL: working tree is not clean" >&2
    git status --short >&2
    exit 1
fi
echo "  tree clean"

if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "FAIL: tag v$VERSION already exists locally" >&2
    exit 1
fi
# Capture the output instead of piping into grep -q: under pipefail,
# grep -q can exit early and fail the pipeline even when the tag exists.
REMOTE_TAG="$(git ls-remote --tags origin "refs/tags/v$VERSION")" \
    || { echo "FAIL: git ls-remote against origin failed" >&2; exit 1; }
if [[ -n "$REMOTE_TAG" ]]; then
    echo "FAIL: tag v$VERSION already exists on origin" >&2
    exit 1
fi
echo "  tag v$VERSION is free (local and origin)"

grep -q "## \[$VERSION\]" CHANGELOG.md \
    || { echo "FAIL: CHANGELOG.md has no [${VERSION}] section" >&2; exit 1; }
echo "  CHANGELOG.md has [$VERSION]"

command -v gh >/dev/null 2>&1 || {
    echo "FAIL: gh CLI is required to poll CI before tagging" >&2
    exit 1
}
echo "  gh CLI present"

# --- Version sites ---------------------------------------------------------

step "Version sites"

CURRENT="$(cat VERSION)"
echo "  current VERSION: $CURRENT"
echo "  new VERSION:     $VERSION"

if [[ "$CURRENT" == "$VERSION" ]]; then
    echo "FAIL: VERSION is already $VERSION" >&2
    exit 1
fi

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

# wrappers/python/src/iso10383/__init__.py -> __version__
p = Path("wrappers/python/src/iso10383/__init__.py")
p.write_text(re.sub(r'^__version__\s*=\s*"[^"]+"', f'__version__ = "{v}"',
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
gate python3 tools/check_version_consistency.py

step "Validation gate"
gate python3 tools/validate.py
gate python3 tools/check_registry_freshness.py
gate python3 tools/check_snapshot_freshness.py
gate python3 tools/check_mojibake.py
gate python3 tools/check_release_claims.py "$VERSION"
gate python3 tools/check_iso3166_current.py --strict
gate python3 tools/check_exchange_calendar_current.py --strict
gate python3 tools/iso10383_cli.py check
gate python3 tools/export_csv.py --check
gate python3 tools/export_sql.py --check
gate python3 tools/export_parquet.py --check
gate python3 tools/sync_wrappers.py --check
gate python3 -m pytest tests/ -q
gate bash tools/check_cross_language.sh --strict
gate python3 tools/gen_iso3166_snapshot.py --check
gate python3 tools/gen_exchange_calendar_snapshot.py --check

# --- Commit, push ---------------------------------------------------------

step "Commit and push"
run git add -A
run git commit -m "Release v$VERSION"
run git push origin main

# --- Poll CI --------------------------------------------------------------
# Polls every per-push workflow for the release SHA. With one
# workflow today, this behaves like the earlier single-run check.
# When a second per-push workflow is added, port check_workflows_covered
# first: this poll sees only the runs that exist when it polls, and
# cannot tell that an expected workflow has not started yet.
#
# Ported from ISO 3166 v1.6.3, which adopted it from ISO 4217 at
# commit 1f38fb4 (function poll_ci).

CI_POLL_INTERVAL=15
CI_POLL_MAX=40

if [[ "$DRY_RUN" != "--dry-run" ]]; then
    step "Waiting for CI"

    SHA="$(git rev-parse HEAD)"
    elapsed=0
    CI_GREEN=false

    while [ "$elapsed" -lt $((CI_POLL_INTERVAL * CI_POLL_MAX)) ]; do
        sleep "$CI_POLL_INTERVAL"
        elapsed=$((elapsed + CI_POLL_INTERVAL))

        RUNS=$(gh run list --limit 30 \
            --json databaseId,headSha,status,conclusion,workflowName \
            --jq ".[] | select(.headSha == \"$SHA\") | \"\(.databaseId)|\(.status)|\(.conclusion // \"pending\")|\(.workflowName)\"" \
            2>/dev/null || echo "")

        if [ -z "$RUNS" ]; then
            echo "  no runs yet (${elapsed}s)"
            continue
        fi

        ALL_COMPLETE=true
        FAILED=false
        while IFS='|' read -r id status conclusion name; do
            if [ "$status" != "completed" ]; then
                ALL_COMPLETE=false
                break
            fi
            if [ "$conclusion" != "success" ]; then
                FAILED=true
                echo "  workflow '$name' (run $id) concluded '$conclusion'" >&2
            fi
        done <<< "$RUNS"

        if [ "$FAILED" = "true" ]; then
            echo "FAIL: CI failed on $SHA" >&2
            exit 1
        fi

        if [ "$ALL_COMPLETE" = "true" ]; then
            echo "  CI passed after ${elapsed}s"
            CI_GREEN=true
            break
        fi

        echo "  waiting... (${elapsed}s)"
    done

    if [ "$CI_GREEN" != "true" ]; then
        echo "FAIL: CI did not complete within " \
             "$((CI_POLL_INTERVAL * CI_POLL_MAX))s" >&2
        exit 1
    fi
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
[[ -n "$TAG_MSG" ]] || {
    echo "FAIL: CHANGELOG.md [$VERSION] section has no body" >&2
    exit 1
}
TAG_MSG_FILE="$(mktemp)"
printf 'Release v%s\n\n%s\n' "$VERSION" "$TAG_MSG" > "$TAG_MSG_FILE"
# Read the file back and verify it before anything is tagged.
[[ -s "$TAG_MSG_FILE" ]] || { echo "FAIL: empty tag message" >&2; exit 1; }
[[ "$(head -n 1 "$TAG_MSG_FILE")" == "Release v$VERSION" ]] || {
    echo "FAIL: tag message header is wrong" >&2
    exit 1
}
if grep -qE '\[(TODO|TBD|PASTE|N|M|K|J)\]' "$TAG_MSG_FILE"; then
    echo "FAIL: tag message contains a placeholder" >&2
    exit 1
fi
run git tag -a "v$VERSION" -F "$TAG_MSG_FILE" --cleanup=verbatim
rm -f "$TAG_MSG_FILE"
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
        echo "Exit codes, in the order the gates ran. A gate that failed would have stopped the release before this file was written."
        echo
        for g in "${GATE_LOG[@]}"; do
            echo "- \`${g#*|}\` — exit ${g%%|*}"
        done
        echo
        echo "Exit codes only. \`tools/check_cross_language.sh\` runs with --strict, so exit 0 means no suite was skipped."
    } > "$DOC"
    git add "$DOC"
    git commit -m "docs: v$VERSION verification"
    git push origin main
fi

echo
echo "Released v$VERSION."
