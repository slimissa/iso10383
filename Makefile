# Build targets for the registry.
#
# `make package` is idempotent and is the one command to run after
# modifying iso10383.json: it regenerates the flat exports (CSV, SQL,
# Parquet) and the four wrapper copies of iso10383.json. Running it twice
# changes nothing the second time. The release gate checks the same
# generators with --check.
#
# `make build-wheel` builds the Python wheel and sdist from the fresh
# bundle; it needs the `build` package (pip install build).
# `make test` runs the root suite and every wrapper's suite; it needs
# Node, Rust and Go (the cross-language check runs with --strict).

PYTHON ?= python3

.PHONY: package build-wheel test

package:
	$(PYTHON) tools/export_csv.py
	$(PYTHON) tools/export_sql.py
	$(PYTHON) tools/export_parquet.py
	$(PYTHON) tools/sync_wrappers.py

build-wheel: package
	@$(PYTHON) -c "import build" 2>/dev/null || { echo "build-wheel needs the 'build' package: pip install build" >&2; exit 1; }
	cd wrappers/python && $(PYTHON) -m build

test:
	$(PYTHON) -m pytest tests/ -q
	bash tools/check_cross_language.sh --strict
