"""Cross-wrapper consistency: bundled copies and versions."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_JSON = (ROOT / "iso10383.json").read_bytes()
VERSION = (ROOT / "VERSION").read_text().strip()


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
