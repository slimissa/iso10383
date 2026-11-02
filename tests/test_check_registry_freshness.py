"""Tests for tools/check_registry_freshness.py.

The tool used to read the real clock, so no test could cross the
60-day boundary without waiting for it. --today (the same override
check_snapshot_freshness.py has) makes the boundary testable.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import check_registry_freshness  # noqa: E402

SNAPSHOT = date(2026, 1, 1)


def _registry(tmp_path, snapshot=SNAPSHOT):
    p = tmp_path / "iso10383.json"
    p.write_text(
        json.dumps({"meta": {"source_snapshot": snapshot.isoformat()}}),
        encoding="utf-8")
    return p


def _run(path, *extra):
    return check_registry_freshness.main([str(path), *extra])


def test_today_on_the_last_fresh_day_exits_0(tmp_path, capsys):
    p = _registry(tmp_path)
    today = SNAPSHOT + timedelta(days=60)
    assert _run(p, "--today", today.isoformat()) == 0
    assert "60 days old" in capsys.readouterr().out


def test_today_one_day_past_the_limit_exits_1(tmp_path, capsys):
    p = _registry(tmp_path)
    today = SNAPSHOT + timedelta(days=61)
    assert _run(p, "--today", today.isoformat()) == 1
    assert "61 days old" in capsys.readouterr().err


def test_max_days_applies_to_the_overridden_today(tmp_path):
    p = _registry(tmp_path)
    today = (SNAPSHOT + timedelta(days=11)).isoformat()
    assert _run(p, "--today", today, "--max-days", "11") == 0
    assert _run(p, "--today", today, "--max-days", "10") == 1


def test_invalid_today_exits_2(tmp_path, capsys):
    p = _registry(tmp_path)
    assert _run(p, "--today", "01/01/2026") == 2
    assert "invalid --today" in capsys.readouterr().err


def test_missing_file_exits_2(tmp_path, capsys):
    assert _run(tmp_path / "nope.json", "--today", "2026-01-02") == 2
    assert "not found" in capsys.readouterr().err


def test_bundled_registry_crosses_the_boundary_on_demand(capsys):
    snap = json.loads((ROOT / "iso10383.json").read_text(
        encoding="utf-8"))["meta"]["source_snapshot"]
    d = date.fromisoformat(snap)
    registry = str(ROOT / "iso10383.json")
    fresh = (d + timedelta(days=60)).isoformat()
    stale = (d + timedelta(days=61)).isoformat()
    assert check_registry_freshness.main([registry, "--today", fresh]) == 0
    assert check_registry_freshness.main([registry, "--today", stale]) == 1
