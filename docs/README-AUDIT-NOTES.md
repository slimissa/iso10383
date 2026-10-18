# README audit notes — the 2026-10-18 rewrite

Historical record of the measurement behind the current `README.md`. The tree audited was `23012da`; the README rewrite landed as `9c3d821`. Kept as a receipt, not as current documentation.

Tree audited: the zip `iso10383-main_1.zip`, archive comment `23012da63851eb7ef47368e3002237fb0b50ff66`, version 1.0.4. It has no `.git/`, so `git describe`, `git log`, `git ls-files` and `git status` could not run. `git ls-files` was replaced by the zip's own file list (125 files, the `git archive` of that commit).

## A. Required companion change (one line)

The old README badge said `tests-205`, and `tools/release_claims.json` pins that string (`README.md contains "tests-205"`). The measured total is **222**, so the new README says 222 and the manifest claim must change with it, or `check_release_claims.py` fails. The patch is `manifest-badge.patch` (one line, line 212). With it applied, `check_release_claims.py 1.0.4` reports `all 141 claim(s) verified`.

## B. Where the old README disagreed with the tree

| # | Old README said | Tree says | Handling |
|---|-----------------|-----------|----------|
| 1 | Tests badge and table: 205 (root 94) | Root 111 (a new `tests/test_check_mojibake.py` has 17); 111 + 29 + 28 + 26 + 28 = **222** | Corrected, badge and table both 222 |
| 2 | JSON example `"updated": "2026-09-28"` | `meta.updated` is `2026-09-23` | Corrected |
| 3 | "Zero runtime dependencies" | Rust wrapper depends on `serde` and `serde_json` | Stated per wrapper |
| 4 | `operating_mic` is a self-referencing FK (all dialects) | Only the PostgreSQL and SQLite files declare it; generic and MySQL do not | Per-dialect table |
| 5 | "Why": Tempus and LAS_Shell "use it", and so do Python, Go, Rust and JS libraries; consumers table says "Planned" | No artifact in the tree backs any of these; JOINS lists neither | Dropped the unbacked claims; Tempus and LAS_Shell appear only as "named intended consumers, no proof here" |
| 6 | Rust and Go return "borrowed references", Python and JS "fresh copies" | Not verified | Dropped |
| 7 | `go get github.com/slimissa/iso10383/wrappers/go`; PROVENANCE says "resolves from git via its own tag" and `cargo add --path` | Not verifiable here (no module proxy access, no tags). The `replace` form was run and works. | Replaced with the `replace` form |
| 8 | JS quick start `require("iso10383-registry")` | Works only after install; the path form `require("./wrappers/javascript")` was run | Used the path form |
| 9 | "What's next": two companions plus wrapper publication, "no other work is planned" | ADRs 0008 to 0012 and the script/tool headers carry more triggers | Replaced with a trigger table. Two rows (`check_workflows_covered`, ISO 4217 snapshot) come from the `release.sh` header and the `check_iso4217_current.py` docstring, not an ADR. |
| 10 | No Known limitations, FAQ, Where to start, Documentation index, CI table, validation table, Consumed-by proofs | Added from the tree | New sections |

## C. Differences between the brief and the tree

- **Claims count.** Brief: 141 claims, 100 doc-facts. Measured: **147** entries (6 for 1.0.3, 5 for 1.0.4, **136** doc-facts). `check_release_claims.py 1.0.4` verifies 141 (136 + 5). The README says 147 total and 141 checked.
- **CI job count command.** `grep -c '^ [a-z-]*:' .github/workflows/validate.yml` returns 0 (one-space indent). With two spaces it returns 8, because `push:` matches and the `[a-z-]` class excludes `workflow_dispatch`. Parsing the YAML gives **7** jobs, which is what the README says.
- **`examples/` directory.** None exists, so the worked example is a reproducible CLI and pandas session. Every output in it was produced from this tree.
- **"Do not invent a second axis."** `check_version_consistency.py` also checks `schema.json` `version` (1.0.0) against the schema badge. The README states nine registry sites and describes the schema check separately as a non-site.
- **Gate count.** `scripts/release.sh` has **17** `gate` calls (the brief's list omitted version consistency). The README lists all 17 in order.
- **Brief's `tests-242`** appears nowhere in the tree; 222 was measured.

## D. Documents and tools that disagree with the tree

**Fixed** in the commit after the README rewrite (all four). The findings are
kept here as the record of what the audit found, not as open items.

1. `tools/iso10383_cli.py` module docstring says "Eight subcommands" and lists eight; there are nine (`check` is missing from the list).
2. `tools/validate.py` module docstring (lines 1 to 31) says cross-registry checks are advisory and warn by default; the code blocks by default since v1.0.1 and `--advisory` downgrades.
3. `CONTRIBUTING.md` § Getting started "Expected on a clean checkout" shows `OK (with warnings)`, `66 passed` and `all wrappers agree`; actual: `OK: 2883 MICs validated`, `111 passed`, `OK: 5 suite(s) passed, 0 skipped`. It also lists `pyarrow >= 14`, while `constraints.txt` pins `==25.0.1`.
4. `docs/PROVENANCE.md` § Distribution describes `cargo add --path wrappers/rust` and a Go module resolved "via its own tag"; neither is verifiable from the tree.

## E. Could not be verified from this tree

- Everything git: commit identity beyond the archive comment, commit count, tag objects, history. The new README states no git-derived fact.
- Rust (cargo 1.75 from apt) and Go (1.22) suites were run and pass (26 and 28); CI uses stable Rust, so a toolchain-version difference is possible.
- PostgreSQL 12+ and MySQL 8+ load claims. SQLite was loaded (3.45.1, foreign keys on, run twice, 2,883 and 16 rows). PostgreSQL and MySQL were not run; their version floors come from the generator headers and the old README.
- Asset Identifiers and Corporate Actions edges, and Exchange Calendar's `exchanges/*.json`, are reported as `docs/JOINS.md` records them. The Exchange Calendar MIC set was compared with the live sibling by `check_exchange_calendar_current.py --strict` (exit 0).
- SWIFT's publication timing ("second Monday", "effective the fourth Monday") and GLEIF's 1,024-pair figure come from `docs/PROVENANCE.md` and ADR 0008, not from the source.
- `refresh.yml` and `release.sh` were read, not executed.
- GitHub runner behaviour (job success, badge state).

## F. Self-check results (run against the final README in a working copy)

| # | Check | Result |
|---|-------|--------|
| 1 | Relative links resolve | 0 unresolved (all `.md` files) |
| 2 | Numbers trace to commands | See table G |
| 3 | Project-structure paths vs the file list | 124 listed, 124 present (README itself excluded); listed but absent: none; present but unlisted: none |
| 4 | Checklist sections | All 23 present; 24 numbered sections; Where to start 10 roles; Known limitations 14 items; FAQ 11 questions |
| 5 | Placeholders (`TBD`, `TODO`, `PASTE`, `[output`) | none |
| 6 | Mojibake and fences | `check_mojibake.py --path README.md`: OK, 1 file; 56 fences (even) |
| 7 | Badge equals table equals sum | 222 = 222 = 111 + 29 + 28 + 26 + 28 |
| 8 | Versioning lists the verified sites | 9 rows, matching the 9 lines `check_version_consistency.py` prints |
| 9 | CI table vs workflows | `validate.yml`, `refresh.yml` (2 files, 2 rows) |
| 10 | Anti-patterns | No `will include`, `planned to`, `eleven sites`, `twenty-two`, `stores-200`, `check_amendments`; the one `planned` is JOINS' own label for Corporate Actions |

Regression on the working copy with the new README and the manifest patch: `validate.py` 0, `check_version_consistency.py` 0, `check_release_claims.py 1.0.4` 0 (141), `check_mojibake.py` 0 (118 files), `export_parquet.py --check` 0, `sync_wrappers.py --check` 0, `pytest tests/` 0 (111).

## G. Number trace

| Number | Command or file |
|--------|-----------------|
| 2,883 / 1,594 / 1,289 / 2,296 / 21 / 566 / 0 broken | `validate.py`, `iso10383_cli.py check`, `meta.counts` |
| 1,281 and 8 segments by depth; 8 chains | parent-walk script over `iso10383.json` |
| 149 country values, 148 plus `ZZ`, `ZZ` = 3 MICs | set arithmetic against `tools/iso3166_snapshot.json` |
| 14 of 16 categories and per-code counts | `Counter` over `market_category` |
| Null counts per field; 44 digit-bearing MICs; `3579` | `Counter` over `iso10383.json` |
| 17 columns, 2,883 rows, 1 row group, SNAPPY, 4 footer keys | `pyarrow.parquet.ParquetFile` |
| 11 SQL columns, 16 category rows, 2,883 inserts, FK per dialect, `BEGIN`/`COMMIT` | grep and parse of the four `.sql` files |
| 4 CSV/TSV files, 17 columns, 2,884 lines, BOM only on `excel.csv`, no CRLF | byte inspection |
| 111 / 29 / 28 / 26 / 28 tests | `pytest`, `pytest`, `node --test`, `cargo test`, `go test -v` |
| 147 / 136 / 141 claims | `release_claims.json`, `check_release_claims.py 1.0.4` |
| 7 jobs; 17 gates | `validate.yml`; `grep -c '^gate ' scripts/release.sh` |
| 252 codes v1.6.9; 74 MICs v2.15.4; review_by dates | snapshots and `.meta.json` |
| 68 / 3 / 3 split of the 74 | set comparison with `iso10383.json` |
| 82 expired since 2024; 182 active DE; 81 search hits; 2024/2025/2026 expiries 26/24/32 | CLI and pandas, outputs pasted in the README |
