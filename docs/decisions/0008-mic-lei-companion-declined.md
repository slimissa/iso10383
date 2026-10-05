# 0008 — MIC→LEI companion declined

**Status:** Accepted
**Date:** 2026-10-05
**Supersedes:** D11's "MIC→LEI (v1.1.0)" line
**Superseded by:** none

---

## Context

D11 (v1.0.0 locked decisions) listed "MIC→LEI mapping" as out of
scope for v1.0.0 and planned for v1.1.0. The plan was a companion
file `mic-lei.json` mapping each operating MIC to the LEI of its
legal operator, sourced from GLEIF's published MIC-to-LEI Mapping
Table.

Phase 0 of the v1.1.0 roadmap performed source reconnaissance against
GLEIF's 2026-09-18 publication. The findings are recorded in
`docs/mic_lei_source_format.md`. They show the companion is
unnecessary.

---

## Decision

The MIC→LEI companion does not ship. The `lei` field on each entry in
`iso10383.json` is the source of truth. No `mic-lei.json` file is
created.

---

## Rationale

Three numbers from the reconnaissance drive the decision.

**1. GLEIF's file is a strict subset of the existing field.** Every
one of the 1,024 MIC-LEI pairs in GLEIF's 2026-09-18 publication
appears in `iso10383.json`'s `lei` field, and every value agrees.

**2. SWIFT carries 120 pairs GLEIF does not.** The union of the two
sources is 1,144 entries — exactly SWIFT's populated count. GLEIF
adds nothing to the union.

**3. No disagreements exist to reconcile.** A companion file's value
would be in recording where the two sources differ. They do not
differ. There is nothing to reconcile.

A companion file as planned would ship 1,024 rows whose values already
exist in the registry, minus 120 rows, and a reconciliation section
whose findings are empty.

---

## Consequences

- **D11 is amended.** The MIC→LEI line changes from "planned for
  v1.1.0" to "declined; the field carries the data." See the
  amendment in `docs/decisions/v1.0.0-decisions.md`.
- **v1.1.0 does not ship.** No version bump, no CHANGELOG entry, no
  tag.
- **The `lei` field is the source of truth.** Consumers that want an
  operator's LEI read the entry. No lookup file is required.
- **The reconnaissance document is the artifact.**
  `docs/mic_lei_source_format.md` records the source format, the
  count reconciliation, and the finding. It is what a future
  maintainer reads when asking "why is there no companion?"
- **GLEIF's file remains a useful audit source.** If a future SWIFT
  publication and a future GLEIF publication ever disagree, the
  reconnaissance document names both and the reconciliation can be
  re-run. That possibility is what the document preserves.

---

## Alternatives considered

**Ship the companion as an enrichment file.** Rejected. The
enrichment would be a 1,024-row file whose every value is already in
`iso10383.json`. A consumer would have two sources of the same fact
with no signal about which to prefer.

**Ship a small audit file recording the coverage.** Rejected for
v1.1.0. The audit is a one-time finding, not a recurring artifact.
Recording it in `docs/mic_lei_source_format.md` preserves the finding
without adding a file that would need freshness checks, exports,
wrappers, and a release gate.

**Defer the companion but leave D11 as-is.** Rejected. D11's "planned
for v1.1.0" line would mislead a future maintainer into re-running
the reconnaissance. The finding needs a home.

**Defer the entire decision to a future release.** Rejected. The
reconnaissance answered the question. Recording the answer costs one
commit; deferring it costs the next maintainer a session.

---

## References

- [`docs/mic_lei_source_format.md`](../mic_lei_source_format.md) —
  the reconnaissance and the numbers
- [`docs/decisions/v1.0.0-decisions.md`](./v1.0.0-decisions.md) D11 —
  the plan this ADR declines
- [`docs/JOINS.md`](../JOINS.md) — the join graph, which now names
  GLEIF as a source but not as a companion
- GLEIF MIC-to-LEI Mapping Table, 2026-09-18 publication
- ISO 10383 `iso10383.json` v1.0.4
