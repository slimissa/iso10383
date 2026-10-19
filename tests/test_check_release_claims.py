"""AST test for check_release_claims.py: aliased clock reads.

The absence claims in tools/release_claims.json are substring checks, so
an alias (`import datetime as dt; dt.datetime.now()`) defeats them. This
test walks the AST of each generator and fails on any call that reads the
clock, aliased or not. Defense in depth; the manifest claim is precise,
the AST test is comprehensive.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

GEN_FILES = [
    ROOT / "tools" / "gen_iso3166_snapshot.py",
    ROOT / "tools" / "gen_exchange_calendar_snapshot.py",
]

# attr names whose parent chain must resolve to a clock source
FIXED_ATTRS = {"now", "today", "time", "uuid4"}

# names that, if they resolve to the clock source, make a call a clock read
CLOCK_SOURCES = {"datetime", "date", "time", "uuid", "random"}

# For `random.`, method name is unconstrained (random.random(), random.uniform()).
# Detected by checking func.value is a Name whose id is `random` or an alias
# that resolves to it.


def _module_aliases(tree: ast.Module) -> dict[str, str]:
    """Map alias -> canonical name for `import X as Y` and `from X import Y as Z`."""
    aliases: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                local = a.asname or a.name.split(".")[0]
                aliases[local] = a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                local = a.asname or a.name
                aliases[local] = a.name
    return aliases


def _resolve(chain: ast.expr, aliases: dict[str, str]) -> str | None:
    """Return the canonical root of an attribute chain, or None."""
    node = chain
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    return None


def _clock_reads(tree: ast.Module) -> list[tuple[int, str]]:
    aliases = _module_aliases(tree)
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        root = _resolve(func.value, aliases)
        # Random: method name unconstrained
        if root == "random":
            hits.append((node.lineno, f"random.{func.attr}()"))
            continue
        # Fixed-method clock sources
        if func.attr in FIXED_ATTRS and root in {"datetime", "date", "time", "uuid"}:
            hits.append((node.lineno, f"{root}.{func.attr}()"))
    return hits


@pytest.mark.parametrize("path", GEN_FILES, ids=lambda p: p.name)
def test_no_clock_read_in_generator(path: Path):
    assert path.is_file(), f"missing: {path}"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits = _clock_reads(tree)
    assert not hits, "\n".join(
        f"{path.name}:{lineno}: {call}" for lineno, call in hits)


def test_aliased_datetime_is_detected():
    src = "import datetime as dt\ndt.datetime.now()\n"
    tree = ast.parse(src)
    assert _clock_reads(tree), "aliased datetime.now not caught"


def test_aliased_random_is_detected():
    src = "import random as rnd\nrnd.uniform(0, 1)\n"
    tree = ast.parse(src)
    assert _clock_reads(tree), "aliased random.uniform not caught"


def test_from_import_is_detected():
    src = "from datetime import datetime as dtn\ndtn.now()\n"
    tree = ast.parse(src)
    assert _clock_reads(tree), "from-imported datetime.now not caught"


def test_clean_source_has_no_hits():
    src = "def f(x):\n    return x + 1\n"
    tree = ast.parse(src)
    assert _clock_reads(tree) == []
