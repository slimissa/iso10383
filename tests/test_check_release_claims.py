"""Tests for tools/check_release_claims.py.

Each test pins one way the claim checker used to pass, or could pass,
without seeing a defect: an `absent` claim that was never implemented, a
claim on a missing file that passed vacuously, a manifest key that was
ignored, a missing manifest or version that did not stop the run.

The AST test for the snapshot generators lives in test_generators.py.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import check_release_claims  # noqa: E402


def test_absent_fails_when_text_present(tmp_path, monkeypatch):
    monkeypatch.setattr(check_release_claims, "PROJECT_ROOT", tmp_path)
    (tmp_path / "doc.md").write_text("old text and new text\n",
                                     encoding="utf-8")

    ok, detail = check_release_claims.check_claim(
        {"file": "doc.md", "absent": "old text"})
    assert not ok
    assert "must be absent" in detail

    ok, _ = check_release_claims.check_claim(
        {"file": "doc.md", "absent": "never written"})
    assert ok

    # A missing file fails any claim, including absent-only ones.
    # Absent-only claims on missing files used to pass vacuously;
    # that is the class the fix at audit time closed.
    ok, detail = check_release_claims.check_claim(
        {"file": "gone.md", "absent": "x"})
    assert not ok
    assert "missing" in detail
    ok, _ = check_release_claims.check_claim({"file": "gone.md"})
    assert not ok


def test_list_prints_claims_without_checking(capsys):
    assert check_release_claims.main(["1.0.4", "--list"]) == 0
    out = capsys.readouterr().out
    assert "[1.0.4]" in out
    assert "[doc-facts]" in out


def test_manifest_has_no_unknown_keys():
    manifest = json.loads(
        (TOOLS / "release_claims.json").read_text(encoding="utf-8"))
    allowed = {"file", "contains", "absent"}
    sections = {k: v for k, v in manifest.items() if not k.startswith("_")}
    assert "doc-facts" in sections and sections["doc-facts"]
    for name, claims in sections.items():
        assert isinstance(claims, list), name
        for claim in claims:
            assert "file" in claim, (name, claim)
            assert set(claim) <= allowed, (name, sorted(set(claim) - allowed))


def test_missing_manifest_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(check_release_claims, "MANIFEST",
                        tmp_path / "no_such_manifest.json")
    with pytest.raises(SystemExit) as exc:
        check_release_claims.main(["1.0.4"])
    assert exc.value.code == 2
    assert "manifest not found" in capsys.readouterr().err


def test_unknown_version_exits_2(capsys):
    with pytest.raises(SystemExit) as exc:
        check_release_claims.main(["0.0.0"])
    assert exc.value.code == 2
    assert "no claims for version 0.0.0" in capsys.readouterr().err


def test_claim_with_unknown_key_exits_1(tmp_path, monkeypatch, capsys):
    # A misspelled key must fail the run, not silently weaken the claim.
    manifest = tmp_path / "release_claims.json"
    manifest.write_text(json.dumps({
        "1.0.4": [{"file": "doc.md", "containz": "text"}],
        "doc-facts": [],
    }), encoding="utf-8")
    (tmp_path / "doc.md").write_text("text\n", encoding="utf-8")
    monkeypatch.setattr(check_release_claims, "MANIFEST", manifest)
    monkeypatch.setattr(check_release_claims, "PROJECT_ROOT", tmp_path)

    assert check_release_claims.main(["1.0.4"]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "unknown claim key" in out
