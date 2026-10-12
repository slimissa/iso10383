"""Tests for the claim-checking tools.

Each test pins one way a check used to pass because it could not see the
defect: an `absent` claim that was never implemented, an unclosed code
fence, a snapshot whose metadata disagrees with it, a Parquet footer that
was skipped when pyarrow was missing, a manifest key that was ignored.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import check_mojibake  # noqa: E402
import check_release_claims  # noqa: E402
import check_snapshot_freshness  # noqa: E402
import check_version_consistency  # noqa: E402

FENCE = "`" * 3


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

    # A missing file satisfies `absent`; pair it with an existence claim.
    ok, _ = check_release_claims.check_claim(
        {"file": "gone.md", "absent": "x"})
    assert ok
    ok, _ = check_release_claims.check_claim({"file": "gone.md"})
    assert not ok


def test_list_prints_claims_without_checking(capsys):
    assert check_release_claims.main(["1.0.4", "--list"]) == 0
    out = capsys.readouterr().out
    assert "[1.0.4]" in out
    assert "[doc-facts]" in out


def test_odd_fence_count_is_detected(tmp_path, capsys):
    bad = tmp_path / "bad.md"
    bad.write_text(f"{FENCE}python\nprint(1)\n\nprose after the fence\n",
                   encoding="utf-8")
    assert check_mojibake.count_fences(bad) == 1
    assert check_mojibake.main(["--path", str(tmp_path)]) == 1
    assert "bad.md" in capsys.readouterr().out

    bad.write_text(f"{FENCE}python\nprint(1)\n{FENCE}\n", encoding="utf-8")
    assert check_mojibake.count_fences(bad) == 2
    assert check_mojibake.main(["--path", str(tmp_path)]) == 0

    # The skip marker opts a file out of both rules.
    bad.write_text("# mojibake-scan: skip\n" + FENCE + "python\n",
                   encoding="utf-8")
    assert check_mojibake.count_fences(bad) is None


def test_snapshot_meta_version_mismatch_is_detected(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(check_snapshot_freshness, "TOOLS", tmp_path)
    snap = tmp_path / "x_snapshot.json"
    meta = tmp_path / "x_snapshot.meta.json"
    snap.write_text(json.dumps({"source_version": "1.0.0", "count": 0}),
                    encoding="utf-8")
    meta.write_text(json.dumps({"source_version": "2.0.0",
                                "meta": {"review_by": "2999-01-01"}}),
                    encoding="utf-8")

    assert check_snapshot_freshness.main(["--today", "2026-01-01"]) == 1
    err = capsys.readouterr().err
    assert "source_version mismatch" in err
    assert "1.0.0" in err and "2.0.0" in err

    meta.write_text(json.dumps({"source_version": "1.0.0",
                                "meta": {"review_by": "2999-01-01"}}),
                    encoding="utf-8")
    assert check_snapshot_freshness.main(["--today", "2026-01-01"]) == 0


def test_unreadable_parquet_fails_instead_of_skipping(
        monkeypatch, capsys):
    # A None entry in sys.modules makes `import pyarrow.parquet` raise
    # ImportError, which is what a runner without pyarrow sees.
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", None)

    with pytest.raises(check_version_consistency.SiteUnreadable):
        check_version_consistency.read_parquet_version()

    assert check_version_consistency.main() == 1
    assert "iso10383.parquet" in capsys.readouterr().err


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
