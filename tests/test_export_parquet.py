"""Parquet artifact checks via pyarrow. No hardcoded values."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow.parquet")

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "iso10383.json").read_text(encoding="utf-8"))
N = len(DATA["mics"])


@pytest.fixture(scope="module")
def pf():
    return pa.ParquetFile(ROOT / "iso10383.parquet")


def test_row_count(pf):
    assert pf.metadata.num_rows == N


def test_expected_columns(pf):
    names = set(pf.schema_arrow.names)
    for col in ("mic", "mic_type", "status", "operating_mic",
                "country_code", "market_category"):
        assert col in names


def test_footer_version_matches(pf):
    md = pf.schema_arrow.metadata or {}
    assert md.get(b"iso10383.version", b"").decode() == DATA["meta"]["version"]


def test_footer_source_hash_matches(pf):
    md = pf.schema_arrow.metadata or {}
    assert md.get(b"iso10383.source_hash", b"").decode() == DATA["meta"]["source_hash"]


def test_footer_source_snapshot_matches(pf):
    md = pf.schema_arrow.metadata or {}
    assert md.get(b"iso10383.source_snapshot", b"").decode() == DATA["meta"]["source_snapshot"]


def test_dates_are_typed(pf):
    for col in ("creation_date", "last_update_date",
                "last_validation_date", "expiration_date"):
        field = pf.schema_arrow.field(col)
        assert str(field.type).startswith("date32"), f"{col}: {field.type}"


def test_parquet_in_sync():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "export_parquet.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r.returncode == 0, r.stderr


def test_two_runs_byte_identical(tmp_path):
    """The pinned pyarrow version and the sorted footer make the file stable."""
    import subprocess
    a = tmp_path / "a.parquet"
    b = tmp_path / "b.parquet"
    for out in (a, b):
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools/export_parquet.py"),
             "-o", str(out)],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
    assert a.read_bytes() == b.read_bytes()


def test_metadata_keys_are_sorted(pf):
    md = pf.schema_arrow.metadata or {}
    keys = [k for k in md if k.startswith(b"iso10383.")]
    assert keys == sorted(keys), keys
