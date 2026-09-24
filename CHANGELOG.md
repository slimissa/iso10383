# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-23

### Added

- Phase 0: repository skeleton, locked decisions document, source format ground truth.

## [Unreleased]

### Added

- Four wrappers: Python, JavaScript, Rust, Go. Each bundles a
  byte-identical copy of the registry and reads the shared contract
  fixture at `tests/cross_language_consistency.json`.
- `tools/check_cross_language.sh` runs all four test suites and
  verifies every wrapper agrees on the same expectations.
- `tools/sync_wrappers.py` extended to all four wrappers, with
  `--check` for CI.
- `docs/decisions/v1.0.0-decisions.md`: D15 (wrappers bundle the
  registry) and D16 (wrapper versions track registry versions).

### Changed

- `VERSION` bumped to 0.2.0 to reflect the four wrappers shipping.
- Root README lists wrapper packages and the consistent API surface.
