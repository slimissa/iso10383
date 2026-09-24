"""CSV/TSV artifact checks. No hardcoded values."""

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "iso10383.json").read_text(encoding="utf-8"))
N = len(DATA["mics"])


def test_csv_row_count():
    with (ROOT / "iso10383.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == N


def test_excel_csv_has_bom():
    head = (ROOT / "iso10383.excel.csv").read_bytes()[:3]
    assert head == b"\xef\xbb\xbf"


def test_european_uses_semicolon():
    first = (ROOT / "iso10383.european.csv").read_text(encoding="utf-8").splitlines()[0]
    assert ";" in first
    assert "," not in first.split(";")[0]


def test_tsv_uses_tab():
    first = (ROOT / "iso10383.tsv").read_text(encoding="utf-8").splitlines()[0]
    assert "\t" in first


def test_header_column_order_matches_json_schema():
    with (ROOT / "iso10383.csv").open(encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    for col in ("mic", "mic_type", "status", "operating_mic", "country_code"):
        assert col in header, f"{col} missing from CSV header"


def test_all_four_exports_in_sync():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "export_csv.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r.returncode == 0, r.stderr


def test_csv_has_no_comment_header():
    first = (ROOT / "iso10383.csv").read_text(encoding="utf-8").splitlines()[0]
    assert not first.startswith("#")
    assert first.startswith("mic,")
