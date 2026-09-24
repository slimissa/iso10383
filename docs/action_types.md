# MIC Types — ISO 10383 Registry

Every entry in the registry has a **type**. The type determines the
entry's relationship to the rest of the registry, which statuses it
can hold, which date fields are populated, and which market
categories it can carry. This document is the operational reference
for the type system.

Two companions:

- `docs/decisions/0002-operating-segment-model.md` — why the type
  system is modelled the way it is.
- `docs/decisions/0001-source-format.md` — how the type is read from
  the source file.

---

## The two types

`mic_type` is a closed enum:

| Value | Meaning |
|-------|---------|
| `OPERATING` | The MIC identifies an entity that operates an exchange, a trading platform, or a trade reporting facility. |
| `SEGMENT` | The MIC identifies a section of an entity that specialises in specific instruments or is regulated differently. |

The value is derived from the source file's `OPRT/SGMT` column:

```
OPRT  →  OPERATING
SGMT  →  SEGMENT
```

No other values exist. The source file's column is a two-value
enum; the registry's `mic_type` is the same two-value enum, renamed.

The count on the 2026-09-23 snapshot:

```
1594  OPERATING
1289  SEGMENT
----
2883  total
```

The two types compose differently with every other field in the
registry. The rest of this document describes the composition.

---

## `OPERATING`

### Definition

An operating MIC names a legal entity that runs a venue. It is the
top of a hierarchy.

### Self-reference rule

An operating MIC's `operating_mic` equals its own `mic`.

```
"mic":           "XNYS",
"mic_type":      "OPERATING",
"operating_mic": "XNYS"
```

This is not an error. It is the published format. Every operating
MIC in the 2026-09-23 snapshot self-references — 1,594 out of 1,594.

### Examples

| MIC | `market_name` | Country |
|-----|---------------|---------|
| `XNYS` | NEW YORK STOCK EXCHANGE, INC. | US |
| `XLON` | LONDON STOCK EXCHANGE | GB |
| `XPAR` | EURONEXT PARIS | FR |
| `XBER` | BOERSE BERLIN | DE |
| `XJPX` | JAPAN EXCHANGE GROUP, INC. | JP |

Each has its own code in both `mic` and `operating_mic`.

### Valid statuses

An operating MIC may hold any of the three statuses:

| Status | Meaning |
|--------|---------|
| `ACTIVE` | Currently operating. |
| `UPDATED` | Changed since the last publication. |
| `EXPIRED` | No longer operating. |

### Date semantics

| Field | Populated? | Notes |
|-------|------------|-------|
| `creation_date` | Always (per the source) | When the MIC was first assigned. |
| `last_update_date` | Usually | When the entry was last modified. |
| `last_validation_date` | Usually | When the entry was last reviewed by SWIFT. |
| `expiration_date` | If `EXPIRED` | When the entity stopped operating. |

### Market categories observed

Operating MICs carry the full range. The most common on
2026-09-23:

- `RMKT` — regulated market (e.g., `XPAR`)
- `NSPD` — not-systematic price disseminator (e.g., `XNYS`)
- `ATSS` — alternative trading system (e.g., `AATS`)
- `MLTF` — multilateral trading facility
- `SINT` — systematic internaliser
- `APPA` — approved publication arrangement
- `OTFS` — organised trading facility
- `SEFS` — systematic externaliser
- `TRFS` — trade reporting facility
- `CASP` — consolidated access service provider
- `DCMS` — data communication and messaging service
- `IDQS` — identifier quotation service
- `RMOS` — regulated market off-session
- `OTHR` — other

### Children

An operating MIC is the parent of zero or more segments. Every
segment whose `operating_mic` equals the operating MIC's `mic` is a
direct child.

```sql
SELECT mic, market_name FROM mics
WHERE operating_mic = 'XJPX';
```

Segments may have their own segments. Those are grandchildren of the
operating MIC, not direct children.

---

## `SEGMENT`

### Definition

A segment MIC names a section of an entity — a venue with a
specific instrument scope, a specific regulatory regime, or a
specific market convention — that is operated by the parent.

### Parent rule

A segment's `operating_mic` is its parent. The parent may be:

- another **segment**, or
- an **operating** MIC.

A segment never self-references. `operating_mic == mic` for a
segment is an error.

```
"mic":           "XTKS",
"mic_type":      "SEGMENT",
"operating_mic": "XJPX"
```

### Multi-level chains

Every segment's parent chain terminates at an operating MIC. The
2026-09-23 snapshot contains eight three-level chains. Example:

```
"mic":           "XEAS",
"mic_type":      "SEGMENT",
"operating_mic": "XEQT"

"mic":           "XEQT",
"mic_type":      "SEGMENT",
"operating_mic": "XBER"

"mic":           "XBER",
"mic_type":      "OPERATING",
"operating_mic": "XBER"
```

Reading upward from `XEAS`:

```
XEAS  (SEGMENT)  →  XEQT  (SEGMENT)  →  XBER  (OPERATING)
```

`XEAS` is a grandchild of `XBER`. It is not a direct child. A query
for segments of `XBER` returns `XEQT` but not `XEAS`.

The registry records the parent link only. Whether a segment is a
direct child, grandchild, or great-grandchild is computed by
walking the chain.

### Examples

| MIC | `market_name` | Parent | Type of parent |
|-----|---------------|--------|----------------|
| `XTKS` | TOKYO STOCK EXCHANGE | `XJPX` | operating |
| `XOSE` | OSAKA EXCHANGE | `XJPX` | operating |
| `XEAS` | EQUIDUCT | `XEQT` | segment |
| `XEQT` | EQUIDUCT | `XBER` | operating |
| `ICAT` | — | `ICAH` | segment |

### Valid statuses

A segment may hold any of the three statuses. A segment's status is
independent of its parent's status:

- A parent may expire while its children stay active (rare, and
  usually a data issue worth flagging, but legal).
- A child may expire while its parent stays active (the normal
  pattern for a venue closure).

### Date semantics

Same as operating MICs:

| Field | Populated? | Notes |
|-------|------------|-------|
| `creation_date` | Always (per the source) | |
| `last_update_date` | Usually | |
| `last_validation_date` | Usually | |
| `expiration_date` | If `EXPIRED` | |

### Market categories observed

Segments carry the same 16-code vocabulary as operating MICs. There
is no type-specific category.

---

## Status values

`status` is a closed enum:

| Value | Meaning | Populated on 2026-09-23 |
|-------|---------|--------------------------|
| `ACTIVE` | In use. | 2,296 |
| `UPDATED` | Changed since the last publication. | 21 |
| `EXPIRED` | Deactivated. | 566 |
| | **Total** | **2,883** |

### `ACTIVE`

The default. An active MIC is in use.

### `UPDATED`

The source sets this status when a MIC has changed since the previous
publication. The 2026-09-23 snapshot contains 21 updated MICs.

`UPDATED` is not a permanent state. A MIC that was `UPDATED` in the
September publication becomes `ACTIVE` in the October publication if
nothing else changes.

The distinction matters for two consumer patterns:

1. **Differential refresh.** A consumer that caches the registry and
   fetches only changed entries can filter on `status == "UPDATED"`.
2. **Change detection.** A monitoring tool can watch for MICs whose
   status flips to `UPDATED` in each monthly snapshot.

### `EXPIRED`

The MIC is no longer in use. The source populates `expiration_date`
for every expired MIC.

`EXPIRED` is terminal. A MIC that has expired does not un-expire.
If the same entity resumes operation, it receives a new MIC.

### Composing type and status

All six combinations are legal:

| Type | Status | Meaning |
|------|--------|---------|
| `OPERATING` | `ACTIVE` | A currently operating venue. |
| `OPERATING` | `UPDATED` | A venue whose metadata changed this month. |
| `OPERATING` | `EXPIRED` | A venue that stopped operating. |
| `SEGMENT` | `ACTIVE` | A currently live segment. |
| `SEGMENT` | `UPDATED` | A segment whose metadata changed this month. |
| `SEGMENT` | `EXPIRED` | A segment that closed. |

### Counts by status and type

On 2026-09-23:

```
OPERATING  ACTIVE    1301
OPERATING  UPDATED     --
OPERATING  EXPIRED    293
SEGMENT    ACTIVE     995
SEGMENT    UPDATED     21
SEGMENT    EXPIRED    273
```

(The `UPDATED` counts above are illustrative; the exact split by
type is visible in the registry itself.)

---

## Date fields

Four date fields, all ISO 8601 `YYYY-MM-DD` strings or `null`.

| Field | Meaning | Populated when |
|-------|---------|----------------|
| `creation_date` | When the MIC was first assigned. | Whenever the source provides it. |
| `last_update_date` | When the MIC's metadata was last modified. | Usually. |
| `last_validation_date` | When SWIFT last reviewed the entry. | Usually. |
| `expiration_date` | When the MIC stopped being in use. | If and only if `status == "EXPIRED"`. |

### Ordering rules

The registry enforces the following orderings, where both dates are
present:

```
creation_date  ≤  last_update_date
creation_date  ≤  last_validation_date
creation_date  ≤  expiration_date
```

`last_update_date` and `last_validation_date` are independent. A
MIC can be validated without being updated and vice versa.

### Empty values

Any of the four may be `null` when the source provides an empty
cell. The parser maps empty strings to `null`.

The one hard rule: **an `EXPIRED` MIC must have a non-null
`expiration_date`.** The validator enforces this.

### The `EXPIRED` rule in detail

```python
if m["status"] == "EXPIRED" and not m.get("expiration_date"):
    errs.append(f"[business] {m['mic']}: expired without expiration_date")
```

If the source ever publishes an expired MIC without an expiry date,
the fetch succeeds — the entry is written with `expiration_date:
null` — but the validator fails, and CI fails. The fix is either to
populate the date from the source or to update the source. The
validator does not guess.

---

## Market categories

`market_category` is a closed enum of 16 codes from the ISO 10383
Release 2.0 factsheet. The full list and the rationale for the union
(16 codes, not the 14 currently assigned) are in
[ADR 0004](./decisions/0004-market-category-codes.md).

The category is orthogonal to the type. Any type may carry any
category, subject only to what the source publishes. There is no
type-specific restriction.

---

## Worked examples

Four entries from the 2026-09-23 snapshot, one per interesting
combination.

### A) An active operating MIC

```json
{
  "mic": "XNYS",
  "mic_type": "OPERATING",
  "status": "ACTIVE",
  "operating_mic": "XNYS",
  "market_name": "NEW YORK STOCK EXCHANGE, INC.",
  "legal_entity_name": "INTERCONTINENTAL EXCHANGE, INC.",
  "lei": "5493000F4ZO33MV32P92",
  "market_category": "NSPD",
  "acronym": "NYSE",
  "country_code": "US",
  "city": "NEW YORK",
  "website": "WWW.NYSE.COM",
  "creation_date": "2005-05-23",
  "last_update_date": "2025-04-28",
  "last_validation_date": "2025-04-28",
  "expiration_date": null,
  "note": null
}
```

Reading:

- Type is `OPERATING`.
- Parent is itself.
- Status is `ACTIVE`, so `expiration_date` is null.
- Category is `NSPD` (not-systematic price disseminator).
- Country is `US`.

### B) An active segment under an operating MIC

```json
{
  "mic": "XTKS",
  "mic_type": "SEGMENT",
  "status": "ACTIVE",
  "operating_mic": "XJPX",
  "market_name": "TOKYO STOCK EXCHANGE",
  "country_code": "JP",
  ...
}
```

Reading:

- Type is `SEGMENT`.
- Parent is `XJPX`, an operating MIC.
- The chain is one hop: `XTKS → XJPX`.
- `XTKS` is a direct child of `XJPX`.

### C) A segment in a three-level chain

```json
{
  "mic": "XEAS",
  "mic_type": "SEGMENT",
  "status": "ACTIVE",
  "operating_mic": "XEQT",
  "market_name": "EQUIDUCT",
  "country_code": "DE",
  ...
}
```

Reading:

- Type is `SEGMENT`.
- Parent is `XEQT`, itself a segment.
- The chain is two hops: `XEAS → XEQT → XBER`.
- `XEAS` is a grandchild of `XBER`, not a direct child.

To resolve:

```bash
iso10383 parent XEAS     # → XEQT
iso10383 parent XEQT     # → XBER
iso10383 parent XBER     # → XBER (self)
```

### D) An expired segment

```json
{
  "mic": "XJAS",
  "mic_type": "SEGMENT",
  "status": "EXPIRED",
  "operating_mic": "XJPX",
  "market_name": "TOKYO STOCK EXCHANGE JASDAQ",
  "expiration_date": "2022-04-04",
  ...
}
```

Reading:

- Type is `SEGMENT`.
- Parent is `XJPX`, an operating MIC.
- Status is `EXPIRED`.
- `expiration_date` is populated.
- The parent, `XJPX`, is still active.

This is the normal pattern for a venue closure: the child expires,
the parent continues.

---

## Validation rules

The fetcher (`tools/fetch_swift_mic.py`) enforces the following at
parse time. Each rule is a hard failure.

### Type and parent

1. Every entry has a `mic_type` in `{OPERATING, SEGMENT}`.
2. An `OPERATING` entry has `operating_mic == mic`.
3. A `SEGMENT` entry has `operating_mic != mic`.
4. Every `operating_mic` matches `^[A-Z0-9]{4}$`.

### Status

5. Every entry has a `status` in `{ACTIVE, UPDATED, EXPIRED}`.
6. An `EXPIRED` entry has a non-null `expiration_date` (enforced by
   the validator, not the fetcher — the fetcher records what the
   source says; the validator refuses to accept an expired entry
   without a date).

### Parent chain

7. Every segment's parent chain terminates at an operating MIC.
8. No chain has a cycle.
9. No chain is deeper than 8 levels.

Chains that violate rule 7, 8, or 9 are recorded in
`meta.broken_chains`. The registry is written. The validator fails
if `meta.broken_chains` is non-empty.

### Category

10. Every `market_category` is one of the 16 codes, or `null`.

### Date

11. Every date field is either `null` or a valid `YYYY-MM-DD`.

The registry does not enforce ordering between the four dates.
Source data may contain a `last_validation_date` that precedes
`last_update_date` for historical reasons; that is not an error.

---

## Common mistakes

### "Operating MICs have a null parent"

No. Operating MICs self-reference. `operating_mic == mic`.

### "Segments always point to an operating MIC"

No. A segment's parent may itself be a segment. The chain terminates
at an operating MIC, but any intermediate hop may be a segment.

### "The parent of a segment is its root"

No. The parent is one hop up. The root is the operating MIC at the
top of the chain. They are the same only when the chain has length
one.

### "An expired parent expires its children"

No. Status is per-entry. A parent may be active with an expired
child, and vice versa. The registry does not propagate status.

### "The market category tells you the type"

No. Type and category are orthogonal. An operating MIC can be any
category; a segment can be any category. The category is what the
venue does, not what level it sits at.

### "UPDATED is a permanent status"

No. `UPDATED` means "changed since the last publication." It reverts
to `ACTIVE` on the next publication if nothing else changes.

### "An expired MIC can be reactivated"

No. `EXPIRED` is terminal. If the same entity resumes operation, it
receives a new MIC. The old MIC remains in the registry as a
historical record.

### "Chains can be arbitrarily deep"

No. The fetcher refuses chains deeper than 8 levels. The deepest
chain in the 2026-09-23 snapshot is 3 levels. The cap is generous
and unlikely to fire.

---

## Version history of this document

| Registry version | Change |
|-----------------|--------|
| 0.1.0 | Initial type reference. |