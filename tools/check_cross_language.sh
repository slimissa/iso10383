#!/usr/bin/env bash
#
# Run every wrapper's test suite in one command.
#
# Each wrapper reads the same tests/cross_language_consistency.json.
# This script verifies that all four languages agree on the same
# expectations against the same bundled snapshot.
#
# Usage:
#   bash tools/check_cross_language.sh
#
# Exit codes:
#   0  every wrapper passed
#   1  at least one wrapper failed
#   2  a required tool is not installed

set -euo pipefail

cd "$(dirname "$0")/.."

failures=0
ran=0

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
    echo
fi

# --- Rust ---

if have cargo; then
    run "rust (cargo test)" \
        bash -c 'cd wrappers/rust && cargo test --quiet'
else
    echo "=== rust (cargo test) ==="
    echo "    SKIP: cargo not installed"
    echo
fi

# --- Go ---

if have go; then
    run "go (go test)" \
        bash -c 'cd wrappers/go && go test ./... -count=1'
else
    echo "=== go (go test) ==="
    echo "    SKIP: go not installed"
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
echo "OK: $ran suite(s) passed, all wrappers agree"
