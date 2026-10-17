"""Tests for tools/check_mojibake.py.

Corrupted text is built at run time from real characters, so this file
holds no corrupted sequence and does not trip the check it tests.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import check_mojibake as cm  # noqa: E402


def _corrupt(text: str, codec: str) -> bytes:
    return text.encode("utf-8").decode(codec).encode("utf-8")


CORRUPTED = [
    ("em dash read as cp1252", _corrupt("\u2014", "cp1252")),
    ("euro sign read as cp1252", _corrupt("\u20ac", "cp1252")),
    ("em dash read as latin-1", _corrupt("\u2014", "latin-1")),
    ("infinity sign read as latin-1", _corrupt("\u221e", "latin-1")),
    ("accented letter read as latin-1", _corrupt("\u00f4", "latin-1")),
    ("replacement character", "\ufffd".encode("utf-8")),
]

CLEAN = [
    "em dash \u2014 and en dash \u2013",
    "euro \u20ac and rupee \u20b9",
    "check mark \u2705 and box \u251c\u2500",
    "accents \u00f4 \u00e7 \u00f1",
    "plain ascii",
]


def _scan(tmp_path, data):
    p = tmp_path / "sample.txt"
    p.write_bytes(data)
    return cm.scan_file(p)


@pytest.mark.parametrize("label,data", CORRUPTED, ids=[c[0] for c in CORRUPTED])
def test_every_corruption_class_is_detected(tmp_path, label, data):
    assert _scan(tmp_path, b"before " + data + b" after"), label


@pytest.mark.parametrize("text", CLEAN)
def test_genuine_characters_are_not_flagged(tmp_path, text):
    assert _scan(tmp_path, text.encode("utf-8")) == []


def test_skip_marker_is_honoured(tmp_path):
    data = b"# mojibake-scan: skip\n" + _corrupt("\u2014", "cp1252")
    assert _scan(tmp_path, data) == []


def test_checker_does_not_trip_over_its_own_source():
    assert cm.scan_file(PROJECT_ROOT / "tools" / "check_mojibake.py") == []


def test_docstring_names_u201a_and_does_not_call_it_an_em_dash():
    doc = cm.__doc__
    assert "U+201A" in doc
    first = doc.split("U+201A", 1)[1].split("\n\n", 1)[0]
    assert "It is not an em dash." in first


def test_docstring_states_that_provenance():
    doc = cm.__doc__
    assert "Mathematical Operators" in doc and "General Punctuation" in doc
    assert "which no pattern covers" in doc


def test_new_patterns_catch_their_classes():
    """The two added patterns each match a real corruption class."""
    import re
    # Pattern 4: "â€" prefix (A-circumflex + euro), catches em-dash as cp1252
    assert re.search(cm.MOJIBAKE_PATTERNS[4], _corrupt("\u2014", "cp1252"))
    # Pattern 5: U+FFFD replacement character
    assert re.search(cm.MOJIBAKE_PATTERNS[5], "\ufffd".encode("utf-8"))


def test_cli_exit_code_follows_scan(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_bytes(_corrupt("\u2014", "cp1252"))
    r = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "tools" / "check_mojibake.py"),
         "--path", str(p)],
        capture_output=True, text=True, timeout=60)
    assert r.returncode == 1
    p.write_bytes(b"clean\n")
    r = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "tools" / "check_mojibake.py"),
         "--path", str(p)],
        capture_output=True, text=True, timeout=60)
    assert r.returncode == 0
