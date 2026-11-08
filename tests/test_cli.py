"""CLI subcommand, exit code, and output-mode tests."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "iso10383_cli.py"


def run(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True, text=True, cwd=ROOT,
    )


@pytest.mark.parametrize("args", [
    ["lookup", "XNYS"],
    ["list", "--country", "US"],
    ["segments", "XJPX"],
    ["parent", "XTKS"],
    ["expired", "--since", "2024-01-01"],
    ["validate", "XNYS", "XLON", "XTKS"],
    ["search", "nasdaq"],
    ["info"],
    ["check"],
])
def test_subcommand_runs(args):
    r = run(*args)
    assert r.returncode == 0, f"{args}: {r.stderr}"


def test_lookup_unknown_is_2():
    # "ZZZ" is three characters, so it is not the MIC pattern: a usage error.
    # (It used to be the lowercase "zzzz", which only failed because the CLI
    # was case-sensitive.)
    assert run("lookup", "ZZZ").returncode == 2


def test_lookup_missing_exits_1():
    # QQQQ is a valid MIC pattern but is not in the registry.
    assert run("lookup", "QQQQ").returncode == 1


def test_validate_missing_exits_1():
    assert run("validate", "XNYS", "QQQQ").returncode == 1


def test_missing_registry_is_3():
    r = run("--registry", "/nope.json", "info")
    assert r.returncode == 3


def test_json_mode_after_subcommand():
    r = run("lookup", "XNYS", "--json")
    assert r.returncode == 0
    obj = json.loads(r.stdout)
    assert obj["mic"] == "XNYS"


def test_csv_header_matches_artifact():
    r = run("lookup", "XNYS", "--csv")
    assert r.returncode == 0
    first = r.stdout.splitlines()[0]
    artifact = (ROOT / "iso10383.csv").read_text(encoding="utf-8").splitlines()[0]
    assert first == artifact


def test_tsv_header_matches_artifact():
    r = run("lookup", "XNYS", "--tsv")
    first = r.stdout.splitlines()[0]
    artifact = (ROOT / "iso10383.tsv").read_text(encoding="utf-8").splitlines()[0]
    assert first == artifact


def test_raw_mode():
    r = run("segments", "XJPX", "--raw", "mic")
    assert r.returncode == 0
    lines = [l for l in r.stdout.splitlines() if l]
    assert "XTKS" in lines


def test_cli_is_case_insensitive():
    """Every MIC and filter argument folds case, as the four wrappers do.
    Each lowercase invocation must give the same non-empty answer as its
    uppercase twin: a matched-zero-rows answer is a failure of the fold."""
    pairs = [
        (["lookup", "xnys"], ["lookup", "XNYS"]),
        (["segments", "xjpx", "--raw", "mic"], ["segments", "XJPX", "--raw", "mic"]),
        (["parent", "xtks"], ["parent", "XTKS"]),
        (["validate", "xnys", "xlon"], ["validate", "XNYS", "XLON"]),
        (["list", "--country", "us", "--raw", "mic"], ["list", "--country", "US", "--raw", "mic"]),
        (["list", "--status", "active", "--raw", "mic"], ["list", "--status", "ACTIVE", "--raw", "mic"]),
        (["list", "--category", "rmkt", "--raw", "mic"], ["list", "--category", "RMKT", "--raw", "mic"]),
        (["list", "--mic-type", "segment", "--raw", "mic"], ["list", "--mic-type", "SEGMENT", "--raw", "mic"]),
    ]
    for lower, upper in pairs:
        a, b = run(*lower), run(*upper)
        assert a.returncode == 0 and b.returncode == 0, (lower, a.stderr, b.stderr)
        assert a.stdout == b.stdout, lower
        assert a.stdout.strip(), f"{lower}: zero rows"
