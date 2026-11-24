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
#
# `make registry-release` regenerates registry_release.json. Run it after
# `make package` and after any change to a file the manifest lists.
#
# `make revendor SIBLING=all` re-vendors the sibling snapshots to their
# latest release tags (tools/revendor.py; SIBLING is iso3166,
# exchange_calendar or all). Extra flags go in ARGS, e.g. ARGS=--check or
# SIBLING=iso3166 ARGS="--to 1.12.13". It needs the network, writes only
# tools/*_snapshot.json and *.meta.json, and is not part of package or test.

PYTHON ?= python3
SIBLING ?= all
ARGS ?=

.PHONY: package build-wheel test registry-release revendor

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

registry-release:
	$(PYTHON) tools/gen_registry_release.py --version "$$(cat VERSION)"

revendor:
	$(PYTHON) tools/revendor.py $(SIBLING) $(ARGS)
