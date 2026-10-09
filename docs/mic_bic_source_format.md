# SWIFT MIC-to-BIC Source Format — Ground Truth

Reconnaissance for the v1.2.0 MIC→BIC companion, performed on
2026-10-09. Concluded that no source file exists: SWIFT does not
publish a MIC-to-BIC mapping file. The companion is declined for
lack of a source, not because the data duplicates an existing field.
See § Decision below.

This reconnaissance differs in kind from the MIC→LEI case recorded in
`docs/mic_lei_source_format.md`. There, the source existed and its
data was redundant. Here, the source does not exist at all. Both are
legitimate findings, and both end in a decline.

---

## The premise being tested

The v1.2.0 plan, as recorded in `README.md` and `docs/PROVENANCE.md`,
was a companion file `mic-bic.json` mapping each MIC to the BIC of
its settlement or clearing institution. The plan asserted, without
citation, that the data was "sourced from SWIFT's published mapping."

Reconnaissance exists to test that assertion. It did not hold.

---

## Sources checked

Three first-party sources were checked on 2026-10-09. None carries a
MIC-to-BIC mapping file.

| Source | What it lists | MIC-to-BIC? |
|--------|---------------|-------------|
| ISO 20022 MIC page (`iso20022.org/market-identifier-codes`) | xlsx, pdf, csv, xml+xsd, and an annexes PDF — September 2026 publication | No |
| ISO 10383 Release 2.0 factsheet | 17 fields; LEI is one, BIC is not | No |
| GLEIF mapping page (`gleif.org/en/lei-data/lei-mapping`) | BIC-to-LEI and MIC-to-LEI files | No |

The ISO 20022 MIC page publishes the MIC file in five formats. None
is a BIC file, and no annex or companion document on that page
carries BIC data.

The Release 2.0 factsheet defines the 17 fields the MIC file
carries. BIC is not among them. LEI is, which is why a MIC-to-LEI
Mapping Table exists at GLEIF — the LEI field is part of the MIC
standard, so an external mapping is meaningful. BIC is not part of
the standard, so no analogous mapping exists.

---

## The nine questions

| # | Question | Answer |
|---|----------|--------|
| 1 | Source URL and format | **None found.** Three sources checked; no MIC-to-BIC file. |
| 2 | Column headers | Not applicable — no file. |
| 3 | Row count | Not applicable — no file. |
| 4 | Delimiter, quoting, encoding | Not applicable — no file. |
| 5 | BIC format | Not applicable — no file. The format is defined by ISO 9362 but this reconnaissance does not validate it against a source. |
| 6 | MIC format | Not applicable — no file. |
| 7 | Duplicates | Not applicable — no file. |
| 8 | Cross-check against `iso10383.json` | The registry has no `bic` field. See § What the registry carries. |
| 9 | License | Not applicable — no file, so no license to read. |

Every question that requires a file is answered "not applicable."
Nothing is estimated. The reconnaissance does not invent counts for a
file that does not exist.

---

## What the registry carries

`iso10383.json` v1.0.4 carries 17 fields per entry:

mic
mic_type
status
operating_mic
market_name
legal_entity_name
lei
market_category
acronym
country_code
city
website
creation_date
last_update_date
last_validation_date
expiration_date
note

None is a BIC. Unlike the MIC→LEI case — where the `lei` field on
every entry made a companion redundant — there is no field to
duplicate. If a MIC-to-BIC source existed, the companion would add
genuinely new data.

It does not exist. That is what blocks the companion.

---

## Two substitutes considered and rejected

Two indirect paths would produce a MIC-to-BIC mapping without a
direct source. Both are rejected.

### 1. Join GLEIF's BIC-to-LEI file on `lei`

The path is `MIC → LEI → BIC`. GLEIF publishes a BIC-to-LEI file.
The registry carries an LEI per operating MIC. Joining them would
produce a per-MIC BIC.

Rejected for three reasons:

- **Semantics.** The BIC in GLEIF's file is the BIC of the LEI's
  legal entity as a *messaging party*. That is not necessarily the
  BIC a settlement instruction should be routed to. One LEI can be
  paired with many BICs (different branches, different settlement
  accounts, different messaging endpoints). The join would pick one
  arbitrarily or return a set whose meaning is unclear.
- **Coverage.** 450 operating MICs have a null `lei` in the
  registry. The join would inherit that gap.
- **Untested.** The GLEIF BIC-to-LEI file was not downloaded during
  this reconnaissance. The rejection rests on the semantics above,
  not on a measured count. If a future maintainer reopens this, the
  file must be fetched and the semantics verified against it.

### 2. Match on the first four BIC characters

ISO 10383:1992 (withdrawn) defined the MIC as the BIC bank code:
four characters, matching the first four characters of a BIC.

The current standard does not. The ISO 10383 Registration Authority's
FAQ states that current MICs are randomly allocated and no longer
carry the BIC prefix. A join on the first four characters would
produce false matches.

Rejected.

---

## Finding

No SWIFT-published MIC-to-BIC mapping file exists. The registry has
no `bic` field. Two indirect paths were considered and rejected. The
companion as planned cannot be built without inventing a source.

The plan's assertion — "sourced from SWIFT's published mapping" —
appears in `README.md` and `docs/PROVENANCE.md` without citation. It
is recorded here as a plan that was never backed by a source file.

---

## Decision

**Declined. The companion file does not ship.**

The v1.2.0 release that D11 planned does not happen. No `mic-bic.json`
is created. No schema, fetcher, validator, exports, or CLI additions
are built. The registry stays at v1.0.4.

See [ADR 0009](./decisions/0009-mic-bic-companion-declined.md) for
the full decision record and the reopening condition.

---

## Reopening condition

The decision reopens if **and only if** a source file appears that
satisfies all three:

1. **A named, published file.** A URL. Not a plan, not a proposal,
   not a rumor. A file someone can download today.
2. **Redistributable terms.** A license that permits redistribution,
   with the required notice quoted verbatim in this document.
3. **A counted reconnaissance.** The nine questions above answered
   with real numbers from the file, following the shape of
   `docs/mic_lei_source_format.md`.

If those three hold, this document is updated and ADR 0009 is
amended. Until then, the decision stands.

An indirect path (either of the two substitutes above) does not
qualify. Neither is a published MIC-to-BIC source.
