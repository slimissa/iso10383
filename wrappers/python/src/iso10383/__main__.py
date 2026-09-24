"""Console shim that locates tools/iso10383_cli.py in a source checkout.

When the wrapper is installed from PyPI without the repo, this shim
prints a one-line message and exits 3. The CLI is a repo artifact for
now; it moves into the package in a later phase.
"""

import importlib.util
import sys
from pathlib import Path


def _find_cli() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "tools" / "iso10383_cli.py"
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    cli = _find_cli()
    if cli is None:
        print(
            "iso10383: CLI not found. Install the repo or run "
            "tools/iso10383_cli.py directly.",
            file=sys.stderr,
        )
        return 3
    sys.path.insert(0, str(cli.parent))
    spec = importlib.util.spec_from_file_location("_cli", cli)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.main()


if __name__ == "__main__":
    sys.exit(main())
