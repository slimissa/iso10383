"""The fetcher's input-shape contract (ADR 0003): a new column is a schema
change and requires a code change, not a silent absorb."""

from pathlib import Path

import pytest

import fetch_swift_mic as fetch  # tools/ is on sys.path via conftest.py

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_fetcher_raises_on_unknown_column():
    with pytest.raises(ValueError, match="unexpected columns"):
        fetch.parse(FIXTURES / "valid_seventeen_plus_one.csv", "0.0.0", "2026-01-01")


def test_fetcher_accepts_the_standard_columns():
    # The same three rows as the fixture above, without the extra column.
    data = fetch.parse(FIXTURES / "valid_three_level.csv", "0.0.0", "2026-01-01")
    assert len(data["mics"]) == 3
    assert data["meta"]["broken_chains"] == []
