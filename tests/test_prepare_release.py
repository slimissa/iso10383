"""scripts/prepare_release.py: the CHANGELOG step of a release."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "prepare_release", Path(__file__).resolve().parent.parent / "scripts" / "prepare_release.py")
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)

BASE = ("# Changelog\n\n---\n\n## [Unreleased]\n\n### Changed\n- a\n\n---\n\n## [1.1.3] - 2026-11-09\n\n### Fixed\n- z\n\n"
        "[Unreleased]: https://x/compare/v1.1.3...HEAD\n[1.1.3]: https://x/compare/v1.1.2...v1.1.3\n")


def test_prepare_creates_heading_empty_unreleased_and_links():
    out = pr.prepare(BASE, "1.1.4", "2026-11-09")
    assert "## [Unreleased]\n\nNothing yet." in out
    assert "## [1.1.4] - 2026-11-09\n\n### Changed\n- a" in out
    assert "[Unreleased]: https://x/compare/v1.1.4...HEAD" in out
    assert "[1.1.4]: https://github.com/slimissa/iso10383/compare/v1.1.3...v1.1.4\n[1.1.3]:" in out


def test_prepare_keeps_separators_between_sections():
    out = pr.prepare(BASE, "1.1.4", "2026-11-09")
    assert out.index("## [Unreleased]") < out.index("---\n\n## [1.1.4]") < out.index("---\n\n## [1.1.3]")


@pytest.mark.parametrize("text", [
    BASE.replace("### Changed\n- a\n", "Nothing yet.\n"),
    BASE.replace("- a", "- [TODO] a"),
    BASE.replace("## [Unreleased]", "## [1.1.4] - 2026-11-09\n\n### Changed\n- q\n\n## [Unreleased]", 1),
])
def test_prepare_refuses_bad_changelogs(text):
    with pytest.raises(ValueError):
        pr.prepare(text, "1.1.4", "2026-11-09")


def test_prepare_refuses_existing_version_and_bad_arguments():
    done = pr.prepare(BASE, "1.1.4", "2026-11-09")
    with pytest.raises(ValueError):
        pr.prepare(done, "1.1.4", "2026-11-09")
    with pytest.raises(ValueError):
        pr.prepare(BASE, "1.1", "2026-11-09")
