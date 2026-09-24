# 0004 — Market category codes

**Status:** Accepted
**Date:** 2026-09-23
**Supersedes:** none
**Superseded by:** none

---

## Context

Every MIC carries a `MARKET CATEGORY CODE`. The values are four-letter
codes from the ISO 10383 Release 2.0 factsheet. The codes are not the
familiar abbreviations: the code for "Regulated Market" is `RMKT`,
not `EXCH`; the code for "Systematic Internaliser" is `SINT`, not
`SI`.

The registry must decide:

1. **How many codes to include in the enum.**
2. **Whether the enum is closed or open.**
3. **Whether to store the code, the human-readable label, or both.**

The 2026-09-23 snapshot uses 14 of the factsheet's 16 codes. The
other two — `ARMS` and `CTPS` — are defined but currently unassigned.

---

## The 16 codes

From the Release 2.0 factsheet:

| Code | Meaning |
|------|---------|
| `ATSS` | Alternative Trading System |
| `APPA` | Approved Publication Arrangement |
| `ARMS` | Arrangement for Reporting |
| `CTPS` | Consolidated Tape Provider |
| `CASP` | Consolidated Access Service Provider |
| `DCMS` | Data Communication and Messaging Service |
| `IDQS` | Identifier Quotation Service |
| `MLTF` | Multilateral Trading Facility |
| `NSPD` | Not-Systematic Price Disseminator |
| `OTFS` | Organised Trading Facility |
| `OTHR` | Other |
| `RMOS` | Regulated Market Off-Session |
| `RMKT` | Regulated Market |
| `SEFS` | Systematic Externaliser |
| `SINT` | Systematic Internaliser |
| `TRFS` | Trade Reporting Facility |

### Observed in the 2026-09-23 snapshot

```
1307  NSPD     381  MLTF     351  SINT     303  RMKT
 143  ATSS     129  OTHR     128  OTFS      30  SEFS
  30  CASP      27  RMOS      26  APPA      22  DCMS
   5  TRFS       1  IDQS
```

Absent: `ARMS`, `CTPS`.

---

## Decision 1 — The enum is the union of all 16 codes

The schema's `market_category` enum includes all 16 codes from the
factsheet, not just the 14 currently assigned.

### Why

A closed enum means an unknown value raises at parse time. If the
enum were the current 14 and SWIFT assigned `ARMS` next month, the
next refresh would raise a `ValueError` on the row using `ARMS`. The
fetcher would refuse to produce a registry. A human would have to
notice the failure, open an ADR, update the enum, and re-run the
refresh.

Including all 16 means a future assignment of `ARMS` or `CTPS` does
not fail the schema. The refresh runs; the new code appears in the
data; the enum did not need to change.

The alternative — "the enum is exactly what the file contains" —
sounds tighter but in practice it means the enum must change on the
same schedule as the data. That coupling is unnecessary.

### Why not extend beyond the factsheet

The 16 codes are the full vocabulary of the Release 2.0 standard. If
a 17th code appears in a future publication, it is a spec change
that warrants a code change — the same way a new `OPRT/SGMT` value
or a new `STATUS` value does.

Being generous with the 16 defined codes is different from being
open to any string. The former is future-proofing; the latter is
abdication.

---

## Decision 2 — Closed enum, unknown value raises

The enum is closed. A value not in the 16-code set raises at parse
time in `tools/fetch_swift_mic.py`.

### Why

An open string field would silently absorb a typo, an unknown code,
or a new spec value. Downstream consumers would have to handle
"market categories they have never seen." The registry's value
depends on the field's vocabulary being known and enforced.

A closed enum at parse time means the failure is at the boundary —
the fetcher names the row and the offending value — not in a
consumer's application three months later.

### Where the failure surfaces

`build_entry()` in `tools/fetch_swift_mic.py`:

```python
if category_raw is not None and category_raw not in MARKET_CATEGORY_SET:
    raise ValueError(
        f"row {row_num} (MIC {mic}): unknown MARKET CATEGORY CODE "
        f"{category_raw!r}"
    )
```

The parser stops. The registry is not written. The human reads the
error, checks the factsheet, and updates the enum in a commit that
names the new code.

---

## Decision 3 — Store the code, not the label

The JSON carries the four-letter code (`RMKT`) in the
`market_category` field. It does not carry the human-readable label
("Regulated Market").

### Why

Consumers join on the code. The code is the join key. Storing the
label instead would break every join against a consumer that used
the published code.

The label is human metadata. Where a label is useful — the SQL
export's `market_categories` lookup table — it is written by the
export tool, not stored in the registry. If ISO renames a code's
label, the label changes in one place (`tools/export_sql.py`) and
every SQL export follows.

The registry itself has no opinion about what a code means in
English. That is what the factsheet is for.

---

## Consequences

### For the schema

`market_category` is a closed enum of 16 codes plus `null`:

```json
"market_category": {
  "type": ["string", "null"],
  "enum": [
    "ATSS", "APPA", "ARMS", "CTPS", "CASP", "DCMS",
    "IDQS", "MLTF", "NSPD", "OTFS", "OTHR", "RMOS",
    "RMKT", "SEFS", "SINT", "TRFS", null
  ]
}
```

`null` is included because some entries in the source file have an
empty `MARKET CATEGORY CODE` cell.

### For the fetcher

`MARKET_CATEGORY_SET` is a Python `set` with all 16 codes. The
fetcher raises on any value not in the set.

### For the SQL export

Two tables:

- `mics.market_category` — the code, constrained by a `CHECK`
  against the same 16-code list.
- `market_categories` — a lookup table with `code` and `label`
  columns. The labels are the one hand-authored value in the entire
  export pipeline.

### For the validator

The validator does not re-check category values. The fetcher
enforces the enum; the schema enforces the enum; a third check
would be redundant. The validator does check that the labels in the
SQL export match the codes in the JSON, via the exporter's
`--check` mode.

### For the CLI

`iso10383 list --category RMKT` filters by code. There is no
`--category "Regulated Market"` shorthand. Codes are the interface.

### For the wrappers

Every wrapper exposes the code as a string. `xnys.market_category`
returns `"NSPD"`, not `"Not-Systematic Price Disseminator"`.

---

## Alternatives considered

**Enum is exactly what the current snapshot contains (14 codes).**
Rejected. Requires an enum change on every refresh that assigns a
new code. See "Decision 1."

**Open string field.** Rejected. Silent drift. See "Decision 2."

**Store both the code and the label in the JSON.** Rejected. The
label is derivable from the code plus the factsheet. Storing both
invites drift when one is updated and the other is not.

**Use human-readable labels as the primary field.** Rejected.
Consumers join on the published code. See "Decision 3."

**Include `ARMS` and `CTPS` in the enum but flag them as "unassigned"
in the schema.** Rejected. The schema has no place for a per-enum-
value annotation. The factsheet is the source of truth for what each
code means; the schema's job is to accept the 16 codes and reject
everything else.

**Normalize to a smaller set (e.g., "exchange", "MTF", "other").**
Rejected. The registry faithfully represents what the source says.
Normalizing at the registry layer would lose information that
consumers can no longer recover.

---

## Open questions

**What if a 17th code appears in a future publication?** The
fetcher raises; the human reads the factsheet; a new ADR amends this
one and the schema is updated. This is the correct behavior. A new
spec code is a code change, not a data change.

**What if SWIFT deprecates a code?** The code stays in the enum
until it is removed from the factsheet. A deprecated code that
appears in an old MIC's `market_category` field would still parse.
Removing a code from the enum is a breaking schema change and
requires a major version bump.

**What about the labels?** The SQL export labels are the one place
this ADR takes a position on English text. The labels are copied
from the Release 2.0 factsheet. If the factsheet updates a label,
the label in `tools/export_sql.py` should follow. The change is
cosmetic — the SQL export is derived, and `--check` will regenerate
it.

---

## References

- ADR [0001](./0001-source-format.md) — source format, value sets
- `docs/source_format.md` — the reconnaissance output
- `docs/PROVENANCE.md` § Value sets observed
- ISO 10383 Release 2.0 factsheet § 2.4(1)
- The 2026-09-23 source snapshot (14 of 16 codes present)