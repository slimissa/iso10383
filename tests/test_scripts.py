"""Tests for scripts and documentation artifacts.

Three checks:
  - release.sh interpolates jq expressions correctly
  - release.sh records the tagged commit SHA, not HEAD
  - the v1.0.0 verification doc shows both the commit and tag object SHAs
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_SH = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
V1_0_0_DOC = (ROOT / "docs" / "v1.0.0-verification.md").read_text(
    encoding="utf-8"
)


def test_release_sh_jq_expression_interpolates():
    """The jq expression uses single backslashes, not double."""
    assert r'\(.status)' in RELEASE_SH
    assert r'\(.conclusion)' in RELEASE_SH
    assert r'\\(.status)' not in RELEASE_SH
    assert r'\\(.conclusion)' not in RELEASE_SH


def test_release_sh_records_tag_commit():
    """The verification doc references the tag's commit, not HEAD."""
    assert "v$VERSION^{commit}" in RELEASE_SH
    assert "Tag object:" in RELEASE_SH


def test_v1_0_0_doc_has_both_shas():
    """The corrected v1.0.0 doc shows both SHAs."""
    assert "753cbbb" in V1_0_0_DOC
    assert "737ac097" in V1_0_0_DOC
    assert "Tag object:" in V1_0_0_DOC
    assert "## Corrections" in V1_0_0_DOC