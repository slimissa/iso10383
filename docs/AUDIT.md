# Tool inventory

The current state of every committed-artifact producer and every
validator, at the registry version in `VERSION`. This file answers
"does this tool run, and where" — the rule lives in
[`RELEASE_PATTERN.md`](./RELEASE_PATTERN.md) § Rule A / Rule B.

Regenerated or hand-edited per release. Do not add policy here; the
policy is in RELEASE_PATTERN.md.

## Category A — committed-artifact producers

Every producer has a `--check` mode and appears in CI and in the
release gate.

| Producer | Artifact | `--check` | CI job | Gate step |
|----------|----------|-----------|--------|-----------|
| `tools/fetch_swift_mic.py` | `iso10383.json` | no (`--strict` breaks on broken chains; parser refuses malformed rows) | — | — |
| `tools/export_csv.py` | 4 CSV/TSV files | yes | `check-exports` | 10 |
| `tools/export_sql.py` | 4 SQL files | yes | `check-exports` | 11 |
| `tools/export_parquet.py` | 1 Parquet file | yes (bytes) | `check-exports` | 12 |
| `tools/sync_wrappers.py` | 4 wrapper bundles | yes | `check-exports` | 13 |
| `tools/gen_iso3166_snapshot.py` | `tools/iso3166_snapshot.json` | yes (bytes, pinned tag) | `check-snapshots` | 16 |
| `tools/gen_exchange_calendar_snapshot.py` | `tools/exchange_calendar_snapshot.json` | yes (bytes, pinned tag) | `check-snapshots` | 17 |

`fetch_swift_mic.py` has no `--check`: Layer 0 is a network input, not
a regenerable artifact, and the parser is the check. If a future
release adds a Layer-0-to-Layer-1 check, add the row.

## Category B — validators

| Validator | What it checks | CI job | Gate step |
|-----------|----------------|--------|-----------|
| `tools/validate.py` | Schema, integrity, business, cross-ref, ground truth, coverage | `validate-json` | 2 |
| `tools/check_version_consistency.py` | Nine version sites + schema badge | `validate-json` | 1 |
| `tools/check_registry_freshness.py` | `meta.source_snapshot` age | `validate-json` | 3 |
| `tools/check_snapshot_freshness.py` | Vendored `review_by` dates | `validate-json` | 4 |
| `tools/check_release_claims.py` | Manifest claims | `validate-json` | 6 |
| `tools/check_mojibake.py` | UTF-8 / Latin-1 corruption, fence parity | `check-mojibake` | 5 |
| `tools/check_iso3166_current.py --strict` | Snapshot vs live sibling | `validate-json` | 7 |
| `tools/check_exchange_calendar_current.py --strict` | Snapshot vs live sibling | `validate-json` | 8 |
| `tools/iso10383_cli.py check` | Registry invariants read through the CLI | `check-cli` | 9 |
| `bash tools/check_cross_language.sh --strict` | Four wrapper suites agree | `check-cross-language` | 15 |
| `tests/test_pip_pins.py` | Every pyarrow install line pinned | `validate-json` | 14 |
| `tests/test_check_release_claims.py` | AST: no aliased clock reads in generators | `validate-json` (via `pytest tests/`) | via `pytest tests/` |
| `tests/` (all) | Root suite | `validate-json` | 14 (via `pytest`) |
| `wrappers/*/tests` (all) | Per-wrapper suites | `check-wrappers` | via `check_cross_language.sh` |

## Category C — enrichment / scheduled tools

Tools that run outside CI and the release gate.

| Tool | What it does | Runs where |
|------|--------------|------------|
| `tools/refresh_diff.py` | ADDED / CHANGED / REMOVED between two registry files | `refresh.yml` (PR body) |
| `tools/check_iso4217_current.py` | No-op: no ISO 4217 snapshot exists | Not in CI, retained as future |
| `tools/export_columns.py` | Column order; not a producer | Imported by exporters |
| `.github/workflows/refresh.yml` | Monthly fetch, diff, PR | Scheduled |

## Rule

Every producer in Category A has a `--check` mode. Every `--check` runs
in CI and in the release gate. Every validator in Category B runs in
CI and in the release gate. A tool that runs in only one place is a
finding against this file.

See [`RELEASE_PATTERN.md`](./RELEASE_PATTERN.md) § Rule A (non-zero
exit halts) and § Rule B (every tool proves its own reachability).
