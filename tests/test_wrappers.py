"""Cross-wrapper consistency: bundled copies and versions."""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROOT_JSON = (ROOT / "iso10383.json").read_bytes()
VERSION = (ROOT / "VERSION").read_text().strip()


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import sync_wrappers  # noqa: E402

BUNDLES = {
    "python":     "wrappers/python/src/iso10383/data/iso10383.json",
    "javascript": "wrappers/javascript/src/data/iso10383.json",
    "rust":       "wrappers/rust/data/iso10383.json",
    "go":         "wrappers/go/data/iso10383.json",
}


def test_all_bundles_byte_identical():
    for lang, rel in BUNDLES.items():
        p = ROOT / rel
        assert p.is_file(), f"{lang}: missing {rel}"
        assert p.read_bytes() == ROOT_JSON, f"{lang}: drifted"


def test_shared_fixture_present():
    fix = ROOT / "tests" / "cross_language_consistency.json"
    assert fix.is_file()
    data = json.loads(fix.read_text(encoding="utf-8"))
    assert len(data["cases"]) >= 14


def test_python_manifest_version():
    text = (ROOT / "wrappers/python/pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m and m.group(1) == VERSION


def test_javascript_manifest_version():
    data = json.loads((ROOT / "wrappers/javascript/package.json").read_text(encoding="utf-8"))
    assert data["version"] == VERSION


def test_rust_manifest_version():
    text = (ROOT / "wrappers/rust/Cargo.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m and m.group(1) == VERSION


def test_registry_meta_version_matches_version_file():
    data = json.loads((ROOT / "iso10383.json").read_text(encoding="utf-8"))
    assert data["meta"]["version"] == VERSION


def test_sync_check_fails_on_missing_target(tmp_path, monkeypatch, capsys):
    source = tmp_path / "iso10383.json"
    source.write_bytes(ROOT_JSON)
    targets = [tmp_path / rel for rel in BUNDLES.values()]
    for t in targets:
        t.parent.mkdir(parents=True)
        t.write_bytes(ROOT_JSON)
    monkeypatch.setattr(sync_wrappers, "SOURCE", source)
    monkeypatch.setattr(sync_wrappers, "TARGETS", [str(t) for t in targets])

    assert sync_wrappers.main(["--check"]) == 0

    targets[0].unlink()
    assert sync_wrappers.main(["--check"]) == 1
    assert "missing" in capsys.readouterr().err
    assert sync_wrappers.main(["--check", "--allow-missing"]) == 0

    # --allow-missing tolerates absence, not drift.
    targets[1].write_bytes(ROOT_JSON + b" ")
    assert sync_wrappers.main(["--check", "--allow-missing"]) == 1

    # The flag means nothing without --check.
    with pytest.raises(SystemExit) as exc:
        sync_wrappers.main(["--allow-missing"])
    assert exc.value.code == 2
