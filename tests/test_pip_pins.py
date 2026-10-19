"""Every pip install line that mentions pyarrow must apply constraints.txt.

Output bytes (iso10383.parquet) depend on the pyarrow version, so
constraints.txt pins it. A workflow line that installs pyarrow without
`-c constraints.txt` would let CI drift from the committed file.

This is a structural check, not a string claim: it parses each workflow
as YAML, walks every job's steps, and inspects every `pip install` line
inside every `run:` block (and every string under a job's `strategy`,
where a matrix can carry an install command). A substring claim in
tools/release_claims.json cannot do this: it passes if one pinned line
exists, whatever other install lines are added beside it.
See docs/RELEASE_PATTERN.md rule 6d.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = [
    ROOT / ".github" / "workflows" / "validate.yml",
    ROOT / ".github" / "workflows" / "refresh.yml",
]

PIP_INSTALL = re.compile(r"\bpip3? install\b")
PYARROW = re.compile(r"\bpyarrow\b")
PIN = "-c constraints.txt"


def _logical_lines(block: str) -> list[str]:
    """Split a shell block into lines, joining backslash continuations,
    so `pip install \\\\\\n pyarrow` is seen as one line."""
    return re.sub(r"\\\n\s*", " ", block).splitlines()


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def offending_lines(text: str, path: str) -> list[str]:
    """Return one message per unpinned pyarrow install line in the
    workflow text. Empty list means the workflow is clean."""
    doc = yaml.safe_load(text)
    bad: list[str] = []
    for job_name, job in (doc.get("jobs") or {}).items():
        blocks: list[str] = []
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                blocks.append(step["run"])
        blocks.extend(_strings(job.get("strategy") or {}))
        for block in blocks:
            for line in _logical_lines(block):
                if (PIP_INSTALL.search(line) and PYARROW.search(line)
                        and PIN not in line):
                    bad.append(
                        f"{path}: job {job_name!r}: pyarrow installed "
                        f"without {PIN!r}: {line.strip()!r}")
    return bad


def _count_install_lines(text: str) -> int:
    doc = yaml.safe_load(text)
    n = 0
    for job in (doc.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                n += sum(1 for ln in _logical_lines(step["run"])
                         if PIP_INSTALL.search(ln))
    return n


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_every_pyarrow_install_is_pinned(workflow: Path):
    assert workflow.exists(), f"missing workflow: {workflow}"
    text = workflow.read_text(encoding="utf-8")
    bad = offending_lines(text, str(workflow.relative_to(ROOT)))
    assert not bad, "\n".join(bad)


def test_the_check_actually_sees_install_lines():
    """Guard against a vacuous pass: if the walker found no install
    lines, it is not looking at the workflows' real structure."""
    for wf in WORKFLOWS:
        assert _count_install_lines(wf.read_text(encoding="utf-8")) > 0, wf


BAD_RUN = """
jobs:
  scratch:
    runs-on: ubuntu-latest
    steps:
      - run: pip install -c constraints.txt pyarrow
      - run: |
          echo hello
          pip install jsonschema pyarrow pytest
"""

BAD_CONTINUATION = """
jobs:
  scratch:
    runs-on: ubuntu-latest
    steps:
      - run: |
          python -m pip install \\
            pyarrow pytest
"""

BAD_MATRIX = """
jobs:
  scratch:
    strategy:
      matrix:
        include:
          - setup: pip install pyarrow
    steps:
      - run: ${{ matrix.setup }}
"""

GOOD = """
jobs:
  scratch:
    runs-on: ubuntu-latest
    steps:
      - run: pip install -c constraints.txt jsonschema pyarrow pytest
      - run: pip install -e wrappers/python pytest
"""


def test_negative_unpinned_line_in_multiline_block_is_caught():
    bad = offending_lines(BAD_RUN, "scratch.yml")
    assert len(bad) == 1
    assert "job 'scratch'" in bad[0]
    assert "pip install jsonschema pyarrow pytest" in bad[0]


def test_negative_backslash_continuation_is_caught():
    assert len(offending_lines(BAD_CONTINUATION, "scratch.yml")) == 1


def test_negative_matrix_install_is_caught():
    assert len(offending_lines(BAD_MATRIX, "scratch.yml")) == 1


def test_positive_pinned_and_unrelated_lines_pass():
    assert offending_lines(GOOD, "scratch.yml") == []
