#!/usr/bin/env bash
#
# Run every wrapper's test suite in one command.
#
# Each wrapper reads the same tests/cross_language_consistency.json.
# This script runs each wrapper's own suite against that shared fixture
# and reports which suites ran and which were skipped. It does not diff
# wrapper output: each suite checks the fixture independently.
#
# Usage:
#   bash tools/check_cross_language.sh [--strict]
#
# Exit codes:
#   0  every suite that ran passed (skipped suites are reported)
#   1  a suite failed, or --strict and a suite was skipped
#   2  python3 is not installed, or an unknown argument was given
#
# --strict is for the release gate: a missing toolchain must not pass
# silently.

set -euo pipefail

cd "$(dirname "$0")/.."

failures=0
ran=0
strict=0
skipped=()

for arg in "$@"; do
    case "$arg" in
        --strict) strict=1 ;;
        *) echo "FAIL: unknown argument: $arg" >&2; exit 2 ;;
    esac
done

have() { command -v "$1" >/dev/null 2>&1; }

run() {
    local label="$1"; shift
    ran=$((ran + 1))
    echo "=== $label ==="
    if "$@"; then
        echo "    OK"
    else
        echo "    FAIL"
        failures=$((failures + 1))
    fi
    echo
}

# --- Preflight ---

if ! have python3; then
    echo "FAIL: python3 not found" >&2
    exit 2
fi

# --- Python ---

run "python (pytest)" \
    python3 -m pytest -q wrappers/python/tests

# --- JavaScript ---

if have node; then
    run "javascript (node --test)" \
        bash -c 'cd wrappers/javascript && node --test'
else
    echo "=== javascript (node --test) ==="
    echo "    SKIP: node not installed"
    skipped+=("javascript")
    echo
fi

# --- Rust ---

if have cargo; then
    run "rust (cargo test)" \
        bash -c 'cd wrappers/rust && cargo test --quiet'
else
    echo "=== rust (cargo test) ==="
    echo "    SKIP: cargo not installed"
    skipped+=("rust")
    echo
fi

# --- Go ---

if have go; then
    run "go (go test)" \
        bash -c 'cd wrappers/go && go test ./... -count=1'
else
    echo "=== go (go test) ==="
    echo "    SKIP: go not installed"
    skipped+=("go")
    echo
fi

# --- Bundled snapshots in sync ---

run "sync_wrappers (bundled copies)" \
    python3 tools/sync_wrappers.py --check

# --- Summary ---

echo "================================"
if [[ "$failures" -gt 0 ]]; then
    echo "FAIL: $failures of $ran suite(s) failed"
    exit 1
fi
if [[ "${#skipped[@]}" -gt 0 ]]; then
    if [[ "$strict" -eq 1 ]]; then
        echo "FAIL: ${#skipped[@]} suite(s) skipped (SKIP: ${skipped[*]}); --strict requires every suite to run"
        exit 1
    fi
    echo "OK: $ran suite(s) passed, ${#skipped[@]} skipped (SKIP: ${skipped[*]})"
    echo "    Skipped suites were not tested."
    exit 0
fi
echo "OK: $ran suite(s) passed, 0 skipped"
