"""SQL artifact checks. Loads SQLite in-memory, verifies invariants."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "iso10383.json").read_text(encoding="utf-8"))
N = len(DATA["mics"])
OPERATING = sum(1 for m in DATA["mics"] if m["mic_type"] == "OPERATING")


def _load(path):
    conn = sqlite3.connect(":memory:")
    conn.executescript(path.read_text(encoding="utf-8"))
    return conn


# Every dialect that SQLite can parse is loaded with foreign keys enforced,
# so a constraint that points at a table the file never creates fails here.
SQLITE_LOADABLE = [
    "iso10383.sql",
    "iso10383.postgresql.sql",
    "iso10383.sqlite.sql",
]


def _load_enforcing_fks(path, times=1):
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    sql = path.read_text(encoding="utf-8")
    for _ in range(times):
        conn.executescript(sql)
    return conn


@pytest.mark.parametrize("name", SQLITE_LOADABLE)
def test_sql_loads_with_foreign_keys_enforced(name):
    conn = _load_enforcing_fks(ROOT / name)
    assert conn.execute("SELECT COUNT(*) FROM mics").fetchone()[0] == N


@pytest.mark.parametrize("name", SQLITE_LOADABLE)
def test_sql_is_safe_to_run_twice(name):
    conn = _load_enforcing_fks(ROOT / name, times=2)
    assert conn.execute("SELECT COUNT(*) FROM mics").fetchone()[0] == N
    categories = conn.execute(
        "SELECT COUNT(*) FROM market_categories").fetchone()[0]
    assert categories == 16


def test_sqlite_idempotent():
    conn = sqlite3.connect(":memory:")
    for _ in range(2):
        conn.executescript((ROOT / "iso10383.sqlite.sql").read_text(encoding="utf-8"))
    assert conn.execute("SELECT COUNT(*) FROM mics").fetchone()[0] == N


def test_operating_mic_not_null():
    conn = _load(ROOT / "iso10383.sqlite.sql")
    n = conn.execute(
        "SELECT COUNT(*) FROM mics WHERE operating_mic IS NULL"
    ).fetchone()[0]
    assert n == 0


def test_operating_self_reference_count():
    conn = _load(ROOT / "iso10383.sqlite.sql")
    n = conn.execute(
        "SELECT COUNT(*) FROM mics WHERE mic = operating_mic"
    ).fetchone()[0]
    assert n == OPERATING


def test_market_categories_loaded():
    conn = _load(ROOT / "iso10383.sqlite.sql")
    n = conn.execute("SELECT COUNT(*) FROM market_categories").fetchone()[0]
    assert n >= 14


def test_foreign_key_to_self_resolves():
    conn = _load(ROOT / "iso10383.sqlite.sql")
    n = conn.execute("""
        SELECT COUNT(*) FROM mics a
        LEFT JOIN mics b ON a.operating_mic = b.mic
        WHERE b.mic IS NULL
    """).fetchone()[0]
    assert n == 0, f"{n} dangling parents"


def test_all_four_dialects_in_sync():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "export_sql.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r.returncode == 0, r.stderr
