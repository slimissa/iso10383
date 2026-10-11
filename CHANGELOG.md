# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The registry data version lives in `VERSION` and is mirrored to
`iso10383.json` -> `meta.version`. The CHANGELOG's top release heading
must match `VERSION`. CI enforces this with
`tools/check_version_consistency.py`.

---

## [Unreleased]

## [1.0.4] - 2026-09-28

### Added

- `docs/JOINS.md` — the MIC join graph from the leaf side. Names
  every registry that references `mic`, the field on each, and the
  granularity (operating / segment / either). Surfaces the
  distinction no root registry can see.

### Changed

- `scripts/release.sh` polls every per-push workflow for the
  release SHA, not just the first. With one workflow today, the
  behavior is identical; when a second is added, the poll already
  covers it. Ported from ISO 3166 v1.6.3, which adopted it from
  ISO 4217 at commit `1f38fb4`.
- `docs/RELEASE_PATTERN.md` names the monthly-cadence shape:
  `meta.source_snapshot` as the freshness field for a registry
  whose source is a calendar publication, 60 days as two missed
  cycles. Contributed by ISO 10383.

### Fixed

- None. Registry data, schema, CLI, and wrapper APIs unchanged
  from v1.0.3.
  
## [1.0.3] - 2026-09-28

### Added

- `scripts/release.sh` preflight `check_no_orphan_variables` — warns
  on variables that are expanded but never assigned. Catches the
  class of failure that produced ISO 3166's v1.6.2 partial release.
  Deferred from v1.0.2 due to a patch anchor mismatch.
- `tools/check_release_claims.py` and `tools/release_claims.json` —
  a release-claims gate that fails the release if the CHANGELOG's
  `[X.Y.Z]` section claims something the tree does not contain.
  Adopted from ISO 3166 v1.6.5.

### Changed

- `.github/workflows/validate.yml` and `scripts/release.sh` run the
  release-claims check.

### Fixed

- None. Registry data, schema, CLI, and wrapper APIs unchanged from
  v1.0.2.

## [1.0.2] - 2026-09-28

### Added

- `tools/check_snapshot_freshness.py` — checks each vendored snapshot
  against its `meta.review_by` date. Reads the date from a sibling
  `tools/<stem>.meta.json` when present, from the snapshot's own
  embedded `meta` block when not. Three states: ISO date (fail if
  past), `closed` (never checked), `null` (warn only).
- `tools/iso3166_snapshot.meta.json` and
  `tools/exchange_calendar_snapshot.meta.json` — vendoring metadata
  for the two cross-registry snapshots.
- `tools/check_mojibake.py` — scans committed files for the four byte
  patterns that indicate a decode/encode cycle went wrong. Adopted
  from ISO 3166 v1.5.3. `CONTRIBUTING.md` § Mojibake describes the
  skip marker.
- `docs/RELEASE_PATTERN.md` — the co-authored release-pattern
  document. ISO 10383's copy records this registry's divergences:
  one per-push workflow (the pattern assumes the general case), and
  the ADR 0005 tag-move exception.
- `scripts/release.sh` preflight `check_no_orphan_variables` — warns
  on variables that are expanded but never assigned. Catches the
  class of failure that produced ISO 3166's v1.6.2 partial release.
- ADR 0005 Scope section, citing `RELEASE_PATTERN.md`'s
  tag-immutability exception. Names both cases: pipeline-failure
  before verification, and post-tag-step failure.

### Changed

- `tools/check_snapshot_freshness.py` renamed to
  `tools/check_registry_freshness.py`. The old name collided with
  ISO 4217's and ISO 3166's tool of the same name, which answers a
  different question. The rename matches the split ISO 4217
  established: registry freshness is one tool, snapshot freshness
  is another.
- `scripts/release.sh` header cites `docs/RELEASE_PATTERN.md` and
  records the two divergences.

### Fixed

- None. This release is a housekeeping release. The registry data,
  schema, CLI, and wrapper APIs are unchanged from v1.0.1.

## [1.0.1] - 2026-09-25

### Added

- ADR 0005, tag discipline: a release tag is created only after the CI
  run on the pushed commit completes successfully, and the verification
  document records the commit SHA and the tag-object SHA on separate
  lines.
- ADR 0006, CI toolchain parity: every CI job installs every package
  its code imports, and `tools/check_cross_language.sh` is the canary.
  A follow-up to the three CI-only failures found during the v1.0.0
  release.
- ADR 0007, cross-registry allowlist: `tools/validate.py` separates
  expected Exchange Calendar gaps from unexpected ones with an explicit
  allowlist (`KNOWN_EXCHANGE_CALENDAR_GAPS`); adding to it requires an
  ADR amendment.
- `docs/v1.0.1-verification.md`, recording the nine gates that passed.

### Changed

- Cross-registry validation is blocking by default (D6). A MIC that
  Exchange Calendar references, that is absent from `iso10383.json`
  and not in the allowlist, now fails `tools/validate.py`.
  `--advisory` restores the v1.0.0 behavior.

## [1.0.0] - 2026-09-24

### Added

- `iso10383.json`: one array of Market Identifier Codes parsed from
  SWIFT's published ISO 10383 file. Each entry is an operating or a
  segment MIC; operating MICs reference themselves and segment MICs
  point to a parent (D2, D3, ADR 0002). `market_category` uses the 16
  ISO codes exactly, as a closed enum (D4, D5, ADR 0004).
- `schema.json` and the six-layer validator `tools/validate.py`.
- SQL, CSV and Parquet exports, each generated by a tool with a
  `--check` mode (`export_sql.py`, `export_csv.py`, `export_parquet.py`).
- Four language wrappers (Python, JavaScript, Rust, Go), each bundling
  a byte-identical copy of the registry, with package versions that
  track the registry version (D15, D16), and `tools/sync_wrappers.py`.
- The command-line interface `tools/iso10383_cli.py`, with a `check-cli`
  CI job.
- `tools/check_version_consistency.py` (D8) and `scripts/release.sh`
  (D12).
- Cross-registry validation against committed snapshots of ISO 3166 and
  Exchange Calendar (D6), advisory in this release. Three Exchange
  Calendar MICs absent from the registry (`XBEK`, `XNBO`, `XQSE`) were
  reported as warnings; Exchange Calendar later renamed them (see the
  2026-10-10 amendment to ADR 0007).
- The monthly-refresh design (ADR 0003): a 60-day freshness gate (D9)
  and the rule that a removed MIC needs human confirmation (D10).
- `CONTRIBUTING.md` (D13).
- Verified at release: 66 root tests pass and five cross-language
  suites pass (`docs/v1.0.0-verification.md`).

## [0.1.0] - 2026-09-23

### Added

- The initial parser, `tools/fetch_swift_mic.py`, which turns SWIFT's
  published ISO 10383 file (the 2026-09-23 publication) into
  `iso10383.json`. The source format is recorded in
  `docs/source_format.md` and ADR 0001.
- The operating/segment type model (ADR 0002), the monthly-refresh
  design (ADR 0003) and the market category codes (ADR 0004).
- The initial `docs/PROVENANCE.md`, `docs/LAYERS.md` and
  `docs/action_types.md`.
- Wrapper packages for Python, JavaScript, Rust and Go, installed from
  the repository rather than from a package registry.

[Unreleased]: https://github.com/slimissa/iso10383/compare/v1.0.4...HEAD
[1.0.4]: https://github.com/slimissa/iso10383/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/slimissa/iso10383/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/slimissa/iso10383/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/slimissa/iso10383/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/slimissa/iso10383/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/slimissa/iso10383/releases/tag/v0.1.0
