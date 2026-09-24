"""Make the wrapper and the anchor module importable during pytest."""

import sys
from pathlib import Path

_tests = Path(__file__).resolve().parent
_src = _tests.parent / "src"

sys.path.insert(0, str(_tests))
sys.path.insert(0, str(_src))
