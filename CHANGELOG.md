# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The registry data version lives in `VERSION` and is mirrored to
`iso10383.json` -> `meta.version`. The CHANGELOG's top release heading
must match `VERSION`. CI enforces this once `check_version_consistency.py`
lands (Phase 6).

---

## [Unreleased]

_Nothing yet. The next release will be discovered from what consumers
ask for, not planned in advance (D14)._

---

## [1.0.0] - 2026-09-24

Four language wrappers, identical behavior, one shared contract.

### Added

- **Python wrapper** (`wrappers/python/`). `MICRegistry` class.
  `.by_mic(mic)`, `.segments(operating_mic)`, `.operating_mic(segment)`,
  `.parent(mic)`, `.root(mic)`, `.expired(since=None)`, `.all()`,
  `.counts()`, iteration. Bundles a byte-identical copy of
  `iso10383.json`.
- **JavaScript wrapper** (`wrappers/javascript/`). Same API surface as
  Python, camelCase. `new MICRegistry()`.
- **Rust wrapper** (`wrappers/rust/`). `Registry::load()`. Same API
  surface.
- **Go wrapper** (`wrappers/go/`). `LoadRegistry()`. Same API surface.
- **Shared contract fixture** at `tests/cross_language_consistency.json`.
  Every wrapper reads the same expectations. Adding a language does not
  require editing the fixture; adding a contract rule does.
- **`tools/check_cross_language.sh`**. Runs all four wrapper test
  suites and asserts every wrapper agrees on the same lookups:
  `XNYS`, `XEAS` (three-level chain), `XEQT` (intermediate segment),
  `XTKS` (segment), a missing MIC, an expired MIC, and a null field.

### Changed

- **`tools/sync_wrappers.py`** now targets all four wrapper bundle
  directories, not just Go and Rust. `--check` verifies all four copies
  are byte-identical to `iso10383.json`. The wrappers do not re-parse
  the JSON; they carry it verbatim.
- **`VERSION`** bumped to `0.2.0`. Registry data is unchanged at
  `1594 operating, 1289 segment, 2296 active, 21 updated, 566 expired,
  2883 total`.
- **Root README** gains a Wrappers section listing package names, the
  consistent API table, and the shared-fixture rule.

### Decisions

- **D15 — Wrappers bundle the registry.** Each wrapper carries a
  byte-identical copy of `iso10383.json` rather than loading from a
  path or network. Rationale: a wrapper that can be loaded from any
  directory without setup is a wrapper someone will use. CI verifies
  the copies match (`sync_wrappers.py --check`).
- **D16 — Wrapper versions track registry versions.** All four wrappers
  ship at `0.2.0` alongside the registry. Rationale: a wrapper version
  that drifts from the data version is a debugging tax. The wrapper's
  API version and the registry's data version are the same number, and
  the CHANGELOG notes both in one release.

---

### Stability

- The JSON contract, JSON Schema, nine distribution artifacts,
  CLI, and four wrappers are now stable under Semantic Versioning.
- Documentation: README, PROVENANCE, LAYERS, action_types, four
  ADRs, and CONTRIBUTING.

## [0.1.0] - 2026-09-23

Phases 0 through 4: foundation, fetcher, schema, validator, exports.

### Added

**Phase 0 — Foundation**

- Repository skeleton: `LICENSE` (Apache 2.0), `README.md` stub,
  `VERSION` (`0.1.0`), `.gitignore`, `.gitattributes` (forces LF for
  generated artifacts).
- `docs/decisions/v1.0.0-decisions.md` — D1 through D14, each with
  choice, alternatives, and rationale. The document is the contract;
  modifications require a signed ADR.
- `docs/source_format.md` — verbatim column headers, value sets, and
  the self-reference verdict, verified against the 2026-09-23 SWIFT
  snapshot.
- `docs/exchange_calendar_mics.txt` — the union of MICs referenced by
  the Exchange Calendar registry, used as the initial cross-reference
  check.
- `CONTRIBUTING.md` — the four rules (no heredocs for patch scripts,
  `set -euo pipefail`, adversarial tests on `/tmp` copies, file-first),
  the source discipline, and the deterministic-write rule.

**Phase 1 — Fetcher and core JSON**

- `tools/fetch_swift_mic.py`. Parses the cached raw CSV into
  `iso10383.json`. Two phases, deliberately separated: `download()`
  (network, cached) and `parse()` (reads the cached file). CI re-runs
  the parse without hitting SWIFT.
- Closed value maps for `mic_type` (`OPRT` / `SGMT`), `status`
  (`ACTIVE` / `UPDATED` / `EXPIRED`), and `market_category` (16 codes).
  An unknown value raises at parse time; the fetcher fails on the row
  that triggered it.
- **Multi-level parent chain resolution** (`resolve_chain`). The
  2026-09-23 snapshot contains eight segments whose `operating_mic`
  points to another segment, not to an operating MIC. Example chain:
  `XEAS -> XEQT -> XBER`. The fetcher resolves the full chain and
  records broken chains (cycles, missing parents, chains deeper than
  8 levels) in `meta.broken_chains`.
- `iso10383.json` — `1594 operating, 1289 segment, 2296 active,
  21 updated, 566 expired, 2883 total`. `meta.source_hash` is a
  `sha256:` digest of the raw file.
- `tools/check_snapshot_freshness.py`. Fails at 60 days.
- Three adversarial fixtures: `tests/fixtures/valid_three_level.csv`,
  `tests/fixtures/bad_missing_parent.csv`,
  `tests/fixtures/bad_cycle.csv`.

**Phase 2 — Provenance**

- `docs/PROVENANCE.md`. Source of truth, file format, refresh cadence,
  audit procedure, known gaps, cross-registry snapshots, versioning.
  Appended with the Exchange Calendar gap note (see `[0.2.0]` below).

**Phase 3 — Schema and validator**

- `schema.json` — JSON Schema draft-07. `additionalProperties: false`
  at every object level. Closed enums for `mic_type`, `status`,
  `market_category`. `operating_mic` is a non-null string (D3).
- `tools/validate.py`. Six layers, run in order:
  1. schema
  2. integrity (patterns, dates)
  3. business (uniqueness, self-reference, expired-without-date)
  4. cross-reference (chain resolution **errors**; ISO 3166 and
     Exchange Calendar checks **warnings** in v1.0.0, per D6)
  5. ground truth (`XNYS`, `XLON`, `XTKS`, `XPAR`)
  6. coverage (`operating >= 1500`, `segment >= 1000`, `total >= 2500`)
- `tools/gen_iso3166_snapshot.py` and
  `tools/gen_exchange_calendar_snapshot.py`. Committed snapshots of the
  two sibling registries. No runtime dependency.
- Six adversarial fixtures in `tests/fixtures/validator/`, one per
  layer. Every one exits non-zero under `tools/validate.py`.

**Phase 4 — Exports**

- `tools/export_columns.py` — canonical column order, single source.
  `SQL_COLUMNS` is the FK-ready minimum; `CSV_COLUMNS` appends the
  human-analysis fields; Parquet uses `CSV_COLUMNS`.
- `tools/export_csv.py` — four files, four dialects:
  `iso10383.csv` (RFC 4180), `iso10383.excel.csv` (UTF-8 BOM),
  `iso10383.european.csv` (semicolon), `iso10383.tsv`.
- `tools/export_sql.py` — four dialects: ANSI SQL-92, PostgreSQL 12+,
  MySQL 8+ / MariaDB 10.4+, SQLite 3.37+. Two tables: `mics` and
  `market_categories`. Idempotent inserts per dialect
  (`ON CONFLICT DO NOTHING`, `INSERT IGNORE`, `INSERT OR IGNORE`).
  `operating_mic` is `NOT NULL` per D3.
- `tools/export_parquet.py` — typed columns (`mic` string,
  `operating_mic` string, dictionary-encoded `mic_type` / `status` /
  `market_category` / `country_code`, `date32` dates). Footer metadata
  carries `iso10383.version`, `.updated`, `.source_snapshot`,
  `.source_hash`.
- `tools/sync_wrappers.py` — copies the registry into wrapper bundle
  directories. `--check` verifies copies are byte-identical.
- Nine committed artifacts at repo root: four SQL, four CSV/TSV, one
  Parquet. Every exporter has `--check`; a stale artifact fails CI.

**Documentation**

- `docs/LAYERS.md` — the RAW / CURATED / AGGREGATED model, mirroring
  ISO 4217.
- `docs/action_types.md` — the reference for `OPERATING` vs `SEGMENT`
  semantics, self-reference policy, and chain depth. 571 lines.
- `docs/decisions/` — four ADRs beyond `v1.0.0-decisions.md`, covering
  the source format, the operating/segment model, the monthly refresh
  cadence, and the market-category code set.

### Changed

- `docs/decisions/v1.0.0-decisions.md`:
  - **D3 amended** after the first parse attempt failed on a real
    three-level chain. The original D3 assumed a two-level hierarchy.
    The amendment names the multi-level case and the consequence
    (chain resolution, not one-hop lookup).
  - **D4 amended** to include the full 16-code union rather than the
    14 codes currently assigned. `ARMS` and `CTPS` are defined but not
    present in the snapshot; including them means a future assignment
    does not fail the schema.
- `tools/validate.py` returns `(errors, warnings)`. Cross-registry
  checks are advisory in v1.0.0 per D6. `--strict` promotes warnings to
  errors. `ZZ` (ISO 10383's "no fixed country" placeholder) is skipped
  in the ISO 3166 check.
- Ground truth corrected: `XTKS` is a `SEGMENT` under `XJPX`, not an
  operating MIC. `XPAR` drops the `mic_type` assertion.

### Fixed

- The fetcher's first run raised on `XEAS -> XEQT`: an eight-row
  three-level chain, not a bug. Resolved by `resolve_chain`, which
  follows parent chains of any depth.
- `tools/export_parquet.py --check` compares schema metadata and row
  count, not bytes. Parquet embeds a creation timestamp; byte
  comparison is not stable.
- `tests/fixtures/validator/*.json` originally passed `--check` even
  when the fixture was corrupted. Fixed: the loop reads `$?` into
  `code` before `basename` runs. All six fixtures now exit non-zero.

### Decisions

- **D1** — New repository, not a monorepo.
- **D2** — One array, not three. `mic_type` ∈ {`OPERATING`, `SEGMENT`},
  `status` ∈ {`ACTIVE`, `UPDATED`, `EXPIRED`}.
- **D3** — Self-reference is the pattern; hierarchy is multi-level.
  Operating MICs self-reference; segments point to a parent of any
  type; chains terminate at an operating MIC.
- **D4** — `market_category` uses the 16 ISO codes exactly.
- **D5** — Closed enums; unknown value raises at parse time.
- **D6** — Cross-registry validation via committed snapshots. Advisory
  in v1.0.0; blocking in v1.0.1.
- **D7** — Tooling: copy and adapt, no shared library.
- **D8** — Versioning: single source, all references agree.
- **D9** — Monthly refresh cadence, gated. CI fails at 60 days.
- **D10** — `REMOVED > 0` is a hard failure.
- **D11** — Out of scope for v1.0.0: operating hours, MIC-to-LEI,
  MIC-to-BIC, MIC-to-ISIN, trading currency per MIC, regulatory status.
- **D12** — `release.sh` ported before v1.0.0.
- **D13** — `CONTRIBUTING.md` written before the code.
- **D14** — Don't write v1.1.0's roadmap.

---

## References

[Unreleased]: https://github.com/slimissa/iso10383/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/slimissa/iso10383/releases/tag/v1.0.0
[0.1.0]: https://github.com/slimissa/iso10383/releases/tag/v0.1.0
