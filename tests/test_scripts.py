"""Tests for scripts and documentation artifacts.

Five checks:
  - release.sh interpolates jq expressions correctly
  - release.sh records the tagged commit SHA, not HEAD
  - release.sh stages named paths, never git add -A/./--all
  - every path release.sh stages exists and covers what the generators write
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
    # Status is interpolated with no fallback: the exact form.
    assert r'\(.status)' in RELEASE_SH
    assert r'\\(.status)' not in RELEASE_SH

    # Conclusion has a // fallback: check the prefix, not the
    # closing-paren form. The exact string after .conclusion is
    # ' // "pending")' in the current block.
    assert r'\(.conclusion' in RELEASE_SH
    assert r'\\(.conclusion' not in RELEASE_SH


def test_release_sh_records_tag_commit():
    """The verification doc references the tag's commit, not HEAD."""
    assert "v$VERSION^{commit}" in RELEASE_SH
    assert "Tag object:" in RELEASE_SH


def _release_paths():
    block = RELEASE_SH.split("RELEASE_PATHS=(", 1)[1].split("\n)", 1)[0]
    return [line.strip() for line in block.splitlines() if line.strip()]


def test_release_sh_stages_explicit_paths():
    """The release commit stages named paths and shows what it staged."""
    for forbidden in ("git add -A", "git add .", "git add --all"):
        assert forbidden not in RELEASE_SH, forbidden
    assert "git diff --cached --stat" in RELEASE_SH
    assert 'git add -- "${RELEASE_PATHS[@]}"' in RELEASE_SH
    assert "git status --porcelain" in RELEASE_SH


def test_release_sh_staging_list_exists_in_tree():
    """Every path the release stages exists, and none is listed twice."""
    paths = _release_paths()
    assert paths
    assert len(paths) == len(set(paths))
    missing = [p for p in paths if not (ROOT / p).is_file()]
    assert not missing, missing
    # The list covers what the generators write, read from the generators.
    import export_csv
    import export_sql
    import sync_wrappers
    written = (set(export_csv.OUTPUTS) | set(export_sql.DIALECTS)
               | set(sync_wrappers.TARGETS)
               | {"iso10383.parquet", "registry_release.json", "VERSION",
                  "iso10383.json", "README.md"})
    assert written <= set(paths), sorted(written - set(paths))


def test_v1_0_0_doc_has_both_shas():
    """The corrected v1.0.0 doc shows both SHAs."""
    assert "753cbbb" in V1_0_0_DOC
    assert "737ac097" in V1_0_0_DOC
    assert "Tag object:" in V1_0_0_DOC
    assert "## Corrections" in V1_0_0_DOC