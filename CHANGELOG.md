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

[Unreleased]: https://github.com/slimissa/iso10383/compare/v1.0.4...HEAD
[1.0.4]: https://github.com/slimissa/iso10383/releases/tag/v1.0.4
[1.0.3]: https://github.com/slimissa/iso10383/releases/tag/v1.0.3
[1.0.2]: https://github.com/slimissa/iso10383/releases/tag/v1.0.2
[1.0.1]: https://github.com/slimissa/iso10383/releases/tag/v1.0.1
[1.0.0]: https://github.com/slimissa/iso10383/releases/tag/v1.0.0
[0.1.0]: https://github.com/slimissa/iso10383/releases/tag/v0.1.0
