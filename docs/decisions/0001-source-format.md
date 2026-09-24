# 0001 — Source format

**Status:** Accepted
**Date:** 2026-09-23
**Supersedes:** none
**Superseded by:** none

---

## Context

The registry parses exactly one file: the SWIFT-published ISO 10383 MIC
CSV. The parser cannot be written against a shape that was assumed;
it must be written against the shape SWIFT actually publishes. Every
downstream decision — schema, validator, SQL export, wrapper API —
depends on this document being correct.

This ADR records the format as observed on 2026-09-23. When the
observed shape changes, this document changes and a new ADR is
opened.

---

## Observed file format

| Property | Value |
|----------|-------|
| URL | `https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv` |
| Encoding | UTF-8, no BOM |
| Line endings | LF |
| Size | 589,482 bytes |
| Data rows | 2,883 |
| Columns | 17 |
| Delimiter | `,` |
| Quote character | `"` |
| Quoting | Every field is quoted |
| Escaping | Doubled quotes (`""`) inside quoted fields |

**Fields containing commas exist** in `MARKET NAME-INSTITUTION
DESCRIPTION`, `LEGAL ENTITY NAME`, and `COMMENTS`. `cut -d,` and
`awk -F,` corrupt output on these rows. The parser uses Python's
`csv` module. This is a hard requirement, not a preference.

### Verbatim column headers

```
 1  MIC
 2  OPERATING MIC
 3  OPRT/SGMT
 4  MARKET NAME-INSTITUTION DESCRIPTION
 5  LEGAL ENTITY NAME
 6  LEI
 7  MARKET CATEGORY CODE
 8  ACRONYM
 9  ISO COUNTRY CODE (ISO 3166)
10  CITY
11  WEBSITE
12  STATUS
13  CREATION DATE
14  LAST UPDATE DATE
15  LAST VALIDATION DATE
16  EXPIRY DATE
17  COMMENTS
```

All header names are uppercase. Every header name is used verbatim by
the parser; the mapping to JSON field names is documented in
`docs/PROVENANCE.md`.

### Value sets observed

**`OPRT/SGMT`** — two values.

```
1594  OPRT
1289  SGMT
```

**`STATUS`** — three values.

```
2296  ACTIVE
 566  EXPIRED
  21  UPDATED
```

**`MARKET CATEGORY CODE`** — 14 of the 16 codes defined by the
Release 2.0 factsheet.

```
1307  NSPD     381  MLTF     351  SINT     303  RMKT
 143  ATSS     129  OTHR     128  OTFS      30  SEFS
  30  CASP      27  RMOS      26  APPA      22  DCMS
   5  TRFS       1  IDQS
```

`ARMS` and `CTPS` are absent from the current snapshot. They are
defined in the factsheet and included in the registry's enum. See
ADR [0004](./0004-market-category-codes.md).

### Date format

All dates in the source are `YYYYMMDD`, not ISO 8601. Example:
`20210927` for 27 September 2021.

The parser converts to `YYYY-MM-DD`. Empty dates become `null`.

### Snapshot date

The file does not embed a publication date. The snapshot date is the
download date and is passed explicitly to the fetcher via
`--snapshot-date`. The monthly refresh workflow passes the current
UTC date.

---

## The self-reference case

**Rows where `MIC == OPERATING MIC`:** 1,594.

This is exactly the count of rows with `OPRT/SGMT == OPRT`. Every
operating MIC has its own code in both the `MIC` and `OPERATING MIC`
columns. Every segment MIC has a different code in the `OPERATING
MIC` column.

This is not a copy-paste artifact. It is the published format.

### But: chains are not two-level

Eight segments point to a parent that is itself a segment. Example:

```
"XEAS","XEQT","SGMT"      # XEAS's parent is XEQT
"XEQT","XBER","SGMT"      # XEQT's parent is XBER
"XBER","XBER","OPRT"      # XBER is an operating MIC
```

The hierarchy is:

```
XEAS  (SEGMENT, parent XEQT)
 └── XEQT  (SEGMENT, parent XBER)
      └── XBER  (OPERATING)
```

The schema must model parent chains of arbitrary depth, not a
two-level tree. See ADR [0002](./0002-operating-segment-model.md).

---

## Consequences

### For the fetcher

1. **Use `csv.DictReader`.** Never `split(",")`.
2. **Convert `YYYYMMDD` → `YYYY-MM-DD`** on output.
3. **Empty string → `null`** for optional fields.
4. **`mic_type` is derived**, not stored: `OPRT` → `OPERATING`,
   `SGMT` → `SEGMENT`.
5. **`operating_mic` is never null.** For `OPRT` rows, set it to
   the row's own `mic`. For `SGMT` rows, set it to the source
   `OPERATING MIC` value.
6. **Resolve the full parent chain** from every segment upward. A
   chain that does not terminate at an operating MIC is recorded in
   `meta.broken_chains`.

### For the schema

1. `mic_type` ∈ {`OPERATING`, `SEGMENT`}, closed.
2. `status` ∈ {`ACTIVE`, `UPDATED`, `EXPIRED`}, closed.
3. `market_category` ∈ the 16-code enum, closed.
4. `operating_mic` matches `^[A-Z0-9]{4}$`, non-null.
5. Dates are ISO 8601 `YYYY-MM-DD` strings.

### For the validator

1. Operating MICs must self-reference.
2. Segments must not self-reference.
3. Every parent chain must terminate at an operating MIC.
4. Chains deeper than 8 levels are refused.

---

## What this ADR does not decide

- Whether the registry bundles or fetches the JSON. See
  [D15](../v1.0.0-decisions.md).
- Which market category codes belong in the enum. See
  [0004](./0004-market-category-codes.md).
- How often the registry refreshes. See
  [0003](./0003-monthly-refresh.md).

---

## Alternatives considered

**Assume a fixed shape and hardcode the column indexes.** Rejected.
Column order is not contractual; the header names are. `DictReader`
keys on names and fails loudly if a name is missing.

**Parse with a regex.** Rejected. Quoted commas and escaped quotes
make a regex parser unreliable. Python's `csv` is a state machine
that handles every case correctly.

**Treat the self-reference case as a bug and reject the file.**
Rejected. It is the published format. A parser that refuses the
canonical file would never work.

**Assume the hierarchy is two levels.** Rejected. Eight three-level
chains exist in the current snapshot. A schema that cannot model
them cannot represent the source.

---

## References

- `docs/source_format.md` — the raw reconnaissance output
- `docs/PROVENANCE.md` § File format consumed
- ADR [0002](./0002-operating-segment-model.md) — hierarchy model
- ADR [0003](./0003-monthly-refresh.md) — refresh cadence
- ADR [0004](./0004-market-category-codes.md) — category enum
- ISO 10383 FAQ, Release 2.0 factsheet