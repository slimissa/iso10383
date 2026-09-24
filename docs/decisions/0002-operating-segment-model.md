# 0002 — Operating / segment model

**Status:** Accepted
**Date:** 2026-09-23
**Supersedes:** none
**Superseded by:** none

---

## Context

ISO 10383 defines two types of MIC:

- An **operating MIC** identifies an entity that operates an
  exchange, a trading platform, or a trade reporting facility. It
  is the top of a hierarchy.
- A **segment MIC** identifies a section of an entity that
  specialises in specific instruments or is regulated differently.
  It has a parent.

Every MIC has a parent MIC. The question is how the parent
relationship is modelled in the JSON, the schema, the SQL export,
and the four wrappers.

The naive model — one array of operating MICs, one array of segment
MICs, one array of expired MICs — is wrong, and this ADR explains
why.

---

## Facts from the source

1. **Operating MICs self-reference in the source file.** The `MIC`
   and `OPERATING MIC` columns hold the same value for every
   operating MIC row. 1,594 of 2,883 rows are operating MICs and
   self-reference.

2. **Segment MICs point to a parent that may itself be a segment.**
   Eight segments in the 2026-09-23 snapshot point to another
   segment. Example chain: `XEAS → XEQT → XBER`.

3. **A MIC's type is never inferred from its code.** Nothing about
   the four characters of a MIC determines whether it is operating
   or segment. The type is published in the `OPRT/SGMT` column.

4. **A MIC's type can change over time.** An operating MIC can
   expire. A new segment can be created under an existing operating
   MIC. A segment can become an operating MIC if its parent
   expires.

---

## Decision

**One array. Two type fields. Non-null parent.**

The registry has one top-level `mics` array. Each entry has:

- `mic_type` ∈ {`OPERATING`, `SEGMENT`}
- `status` ∈ {`ACTIVE`, `UPDATED`, `EXPIRED`}
- `operating_mic` — a non-null string matching `^[A-Z0-9]{4}$`

The rules:

| `mic_type` | `operating_mic` |
|------------|-----------------|
| `OPERATING` | equals `mic` (self-reference) |
| `SEGMENT` | equals the parent MIC (never equal to `mic`) |

The parent of a segment may itself be a segment. The parent chain
always terminates at an operating MIC.

Querying every segment under an operating MIC is one clause:

```sql
SELECT * FROM mics WHERE operating_mic = 'XJPX';
```

Querying every active operating MIC in the US is two clauses:

```sql
SELECT * FROM mics
WHERE country_code = 'US'
  AND status = 'ACTIVE'
  AND mic_type = 'OPERATING';
```

---

## Consequences

### For the schema

- `mic_type` and `status` are closed enums. An unknown value raises
  at parse time.
- `operating_mic` is a required, non-null string.
- The schema does not enforce that operating MICs self-reference.
  That is the validator's job. The schema is structural; the
  validator is semantic.

### For the validator

- Operating MICs must have `operating_mic == mic`.
- Segments must have `operating_mic != mic`.
- Every segment's chain must terminate at an operating MIC.
- Chains deeper than 8 levels are refused.
- Cycles are refused.
- Missing parents are recorded in `meta.broken_chains` and do not
  abort the parse.

### For the SQL export

The `mics` table declares a self-referencing foreign key:

```sql
CREATE TABLE mics (
  mic           VARCHAR(4) PRIMARY KEY,
  operating_mic VARCHAR(4) NOT NULL,
  ...
  CONSTRAINT fk_mics_operating
    FOREIGN KEY (operating_mic) REFERENCES mics(mic)
    DEFERRABLE INITIALLY DEFERRED
);
```

`DEFERRABLE INITIALLY DEFERRED` is required: rows are inserted in
`mic`-sorted order, and a segment whose parent sorts after it would
otherwise violate the FK mid-transaction. The deferral defers the
check to `COMMIT`.

The `NOT NULL` on `operating_mic` is the D3 decision made
mechanical.

### For the wrappers

Every wrapper exposes:

- `by_mic(mic)` — returns the entry
- `segments(mic)` — returns the **direct** children of a MIC
- `operating_mic(mic)` — returns the parent MIC

`segments(mic)` returns direct children only. A grandchild is not
listed. To walk the full subtree, call `segments()` recursively or
walk upward from each candidate.

The Python and JavaScript wrappers return fresh copies on every
lookup. The Rust and Go wrappers return borrowed references. Both
are correct; the language's ownership model determines which is
idiomatic.

### For the CLI

`iso10383 segments XJPX` returns the direct children.

`iso10383 parent XTKS` returns the parent. For an operating MIC, the
parent is itself.

There is no `iso10383 root XTKS` or `iso10383 subtree XJPX` in
v1.0.0. Both are trivial to build on top of `parent` and `segments`.
If demand arises, they are additive.

---

## Why one array, not three

The naive split is `operating_mics`, `segment_mics`, `expired_mics`.
Every argument against it:

1. **Expired is a status, not a type.** An expired MIC was once
   either operating or segment. Splitting by status means every
   expiry is a move between arrays.

2. **Two orthogonal dimensions are simpler than three arrays.** The
   two facts about a MIC are its type and its status. Storing them
   as two fields on one entry is one filter clause per dimension.
   Storing them as three arrays means every query unions across
   arrays and re-checks the dimensions anyway.

3. **The FK is one table.** A self-referencing `operating_mic`
   foreign key is a single clause. A cross-array parent reference
   requires either two FKs or a synthetic join table.

4. **The wrappers need one map.** One `HashMap<mic, Entry>` answers
   every lookup. Two arrays require two maps and a composite query
   for "give me everything with this MIC."

5. **The order of operations is wrong.** A refresh that expires a
   MIC would have to remove it from `operating_mics` and insert it
   into `expired_mics` as a single atomic step. The correctness
   burden is on the refresh tool rather than the schema.

The three-array design is not wrong because it is unusual. It is
wrong because it makes every downstream consumer's job harder for
no compensating benefit.

---

## Alternatives considered

**`operating_mic` is null for operating MICs.** Rejected. The
source file self-references. Null would mean the parser has to
special-case the operating rows, every consumer has to test
`operating_mic is None`, and the self-referencing nature of
operating MICs would be lost. The published format is the format.

**Two arrays: `operating_mics` and `segment_mics`, with expired as
a status field on each.** Rejected. See "Why one array, not three."

**A separate `parent_mic` field for the direct parent and a
`root_mic` field for the operating MIC.** Rejected. `root_mic` is
derivable from `parent_mic` by walking the chain. Storing both
invites drift: a refresh that changes a parent would have to
recompute roots for every descendant. The chain is computable; the
storage is not necessary.

**Model the hierarchy as a graph with explicit edges.** Rejected.
The graph is a forest, and every node has exactly one parent. A
self-referencing parent field is the forest, encoded compactly. An
edge table would be a projection of the same information with no
new capability.

**Refuse files with multi-level chains.** Rejected. The chains are
in the source. A parser that refuses them is not usable.

**Flatten multi-level chains to two levels.** Rejected. The
intermediate segment (e.g., `XEQT` in `XEAS → XEQT → XBER`) is a
real venue with its own MIC. Flattening would erase it.

---

## Open questions

None. The self-reference pattern and the multi-level chains are
both observed facts. The model is deterministic.

If a future refresh produces a chain deeper than 8 levels, the
fetcher refuses and names the chain. The decision to extend the cap
is a data question, not a modelling question, and can be answered
when it arises.

---

## References

- ADR [0001](./0001-source-format.md) — source format
- `docs/source_format.md` — the reconnaissance output
- `docs/PROVENANCE.md` § The hierarchy model
- `docs/LAYERS.md` § Layer 1
- ISO 10383 FAQ (self-reference example)
- The 2026-09-23 source snapshot (1,594 self-references, 8
  three-level chains)