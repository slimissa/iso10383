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
    assert run("lookup", "zzzz").returncode == 2


def test_lookup_missing_is_1():
    # AAAAA is valid pattern but not present.
    assert run("lookup", "QQQQ").returncode in (0, 1)
    r = run("validate", "XNYS", "QQQQ")
    assert r.returncode == 1


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
