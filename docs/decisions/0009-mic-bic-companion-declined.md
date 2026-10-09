# 0009 — MIC→BIC companion declined

**Status:** Accepted
**Date:** 2026-10-09
**Supersedes:** D11's inclusion of "MIC→BIC" in the out-of-scope list
**Superseded by:** none

---

## Context

D11 (v1.0.0 locked decisions) listed "MIC→BIC" in its out-of-scope
list. The v1.2.0 roadmap proposed a companion file `mic-bic.json`
mapping each MIC to the BIC of its settlement or clearing
institution, "sourced from SWIFT's published mapping."

Phase 0 reconnaissance was performed on 2026-10-09 against three
first-party sources. The findings are recorded in
`docs/mic_bic_source_format.md`. They show the source does not exist.

---

## Decision

The MIC→BIC companion does not ship. No `mic-bic.json` is created.
The registry stays at v1.0.4.

---

## Rationale

Three findings drive the decision.

**1. No source file exists.** The ISO 20022 MIC page, the ISO 10383
Release 2.0 factsheet, and GLEIF's mapping page were all checked. No
MIC-to-BIC mapping file. The five formats the MIC page publishes
(xlsx, pdf, csv, xml+xsd, and an annexes PDF) carry no BIC data. The
factsheet defines 17 fields and BIC is not one of them. GLEIF
publishes BIC-to-LEI and MIC-to-LEI, not MIC-to-BIC.

**2. The registry has no `bic` field.** `iso10383.json` v1.0.4
carries 17 fields per entry. BIC is not among them. This distinguishes
the case from the MIC→LEI companion: that source existed and its data
was redundant with the `lei` field. Here, if a source existed, the
companion would add genuinely new data. It does not exist, so the
companion has nothing to add.

**3. Two indirect substitutes were considered and rejected.** A join
through GLEIF's BIC-to-LEI file inherits 450 null `lei` values and
conflates messaging-party BICs with settlement-route BICs. A prefix
join on the first four BIC characters fails because current MICs are
randomly allocated, not BIC-prefixed, per the Registration
Authority's FAQ.

The finding is "no source," not "redundant source." The MIC→LEI
precedent does not transfer.

---

## Consequences

- **D11 is amended.** A second amendment note is appended naming this
  finding, after the MIC→LEI amendment from 2026-10-05.
- **v1.2.0 does not ship.** No version bump, no CHANGELOG entry, no
  tag.
- **No `mic-bic.json`.** No schema, fetcher, validator, exports, or
  CLI additions are built.
- **The reconnaissance document is the artifact.**
  `docs/mic_bic_source_format.md` records the sources checked, the
  field-set finding, the two rejected substitutes, and the reopening
  condition.
- **The plan's premise is corrected.** The assertion that the
  companion would be "sourced from SWIFT's published mapping" is
  removed from `README.md` and `docs/PROVENANCE.md`. It has no
  citation.

---

## Alternatives considered

**Build the companion from GLEIF's BIC-to-LEI file.** Rejected. The
BIC in that file is the BIC of the LEI's legal entity as a messaging
party, not a settlement route. One LEI can pair with many BICs. The
join inherits 450 null `lei` values. The substitution rests on a
semantic conflation, not a data equivalence.

**Build the companion by matching the first four BIC characters.**
Rejected. ISO 10383:1992 defined the MIC as the BIC bank code. That
is no longer true. Current MICs are randomly allocated and no longer
share a prefix with any BIC.

**Borrow the MIC→LEI "strict subset" argument.** Rejected. The
registry has no `bic` field, so there is nothing to be a subset of.
The LEI precedent is a different finding about the same class of
companion. Both end in a decline, for different reasons.

**Defer the decision pending a SWIFT email.** Rejected. The
reconnaissance is complete without an email. A reply confirming "no
file exists" would strengthen the finding from "not found in three
sources" to "confirmed by the standards body." It would not change
the decision. If a reply arrives with a URL, the reopening condition
is met and Phase 0 restarts.

---

## Reopening condition

The decision reopens if a source file appears that satisfies all
three conditions named in `docs/mic_bic_source_format.md` § Reopening
condition: a named published file, redistributable terms, and a
counted reconnaissance. Neither of the two rejected substitutes
qualifies.

---

## References

- [`docs/mic_bic_source_format.md`](../mic_bic_source_format.md) —
  the reconnaissance and the sources checked
- [`docs/decisions/v1.0.0-decisions.md`](./v1.0.0-decisions.md) D11 —
  the plan this ADR declines
- [`docs/mic_lei_source_format.md`](../mic_lei_source_format.md) —
  the different-shaped decline for the MIC→LEI companion
- [`docs/decisions/0008-mic-lei-companion-declined.md`](./0008-mic-lei-companion-declined.md)
- ISO 20022 MIC page (`iso20022.org/market-identifier-codes`),
  September 2026 publication
- ISO 10383 Release 2.0 factsheet
- GLEIF mapping page (`gleif.org/en/lei-data/lei-mapping`)
