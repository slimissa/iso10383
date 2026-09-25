"""Layer tests for tools/validate.py."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "tools" / "validate.py"
REGISTRY = ROOT / "iso10383.json"


def run(*args, expect=None):
    r = subprocess.run(
        [sys.executable, str(VALIDATE), *args],
        capture_output=True, text=True, cwd=ROOT,
    )
    if expect is not None:
        assert r.returncode == expect, (
            f"exit {r.returncode} != {expect}\n"
            f"stdout: {r.stdout}\nstderr: {r.stderr}"
        )
    return r


def test_real_file_passes():
    r = run(str(REGISTRY), expect=0)
    assert "OK" in r.stdout


def test_strict_fails_on_warning():
    # The real file has one Exchange Calendar warning. --strict promotes.
    r = subprocess.run(
        [sys.executable, str(VALIDATE), str(REGISTRY), "--strict"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r.returncode == 1
    assert "FAIL" in r.stderr


def test_missing_registry_exits_2():
    run("/nope.json", expect=2)


def test_bad_json_exits_3(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    run(str(bad), expect=3)


def test_only_coverage():
    r = run(str(REGISTRY), "--only", "coverage", expect=0)
    assert "OK" in r.stdout


def test_skip_cross_reference():
    run(str(REGISTRY), "--skip", "cross-reference", expect=0)


def test_help_lists_every_layer():
    r = subprocess.run(
        [sys.executable, str(VALIDATE), "--help"],
        capture_output=True, text=True, cwd=ROOT,
    )
    for layer in ("schema", "integrity", "business",
                  "cross-reference", "ground-truth", "coverage"):
        assert layer in r.stdout, f"{layer} not in --help"


def test_cross_registry_default_is_blocking_on_unexpected_gap(tmp_path):
    """An unexpected Exchange Calendar gap is an error by default."""
    import json
    snapshot = json.loads(
        (ROOT / "tools" / "exchange_calendar_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    snapshot["mics"] = sorted(set(snapshot["mics"]) | {"ZZZZ"})
    p = tmp_path / "ec.json"
    p.write_text(json.dumps(snapshot), encoding="utf-8")

    r = subprocess.run(
        [sys.executable, str(VALIDATE), str(REGISTRY),
         "--exchange-calendar", str(p)],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r.returncode == 1
    assert "ZZZZ" in r.stderr
    assert "allowlist" in r.stderr


def test_cross_registry_advisory_opt_out(tmp_path):
    """--advisory turns the unexpected gap back into a warning."""
    import json
    snapshot = json.loads(
        (ROOT / "tools" / "exchange_calendar_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    snapshot["mics"] = sorted(set(snapshot["mics"]) | {"ZZZZ"})
    p = tmp_path / "ec.json"
    p.write_text(json.dumps(snapshot), encoding="utf-8")

    r = subprocess.run(
        [sys.executable, str(VALIDATE), str(REGISTRY),
         "--exchange-calendar", str(p), "--advisory"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r.returncode == 0
    assert "ZZZZ" in r.stderr
