# The MIC join graph

ISO 10383's `mic` field is the join target for every other registry
in the QuantOS ecosystem. This document names the edges from the
leaf side: who references `mic`, where, and at what granularity.

Authored here because ISO 10383 is the target of the join. A
consumer registry that joins against `mic` cannot see the shape
from its own side.

---

## The join key

`mic` — a four-character uppercase alphanumeric string. Primary key
of `mics[]` in `iso10383.json`. Non-null, unique within the
registry, pattern `^[A-Z0-9]{4}$`. Example: `XNYS`.

The registry is at https://github.com/slimissa/iso10383.

---

## Registries that reference `mic`

| Registry | Field | Granularity | Notes |
|----------|-------|-------------|-------|
| Exchange Calendar | `exchanges/*.json` → `mic` (or `code`) | Either | One entry per exchange. 74 files today. |
| Asset Identifiers | each entry's `exchange` | Either | Primary listing venue. |
| Asset Identifiers | `listings[].exchange` | Either | Per-listing venue. |
| Corporate Actions (planned) | each action's `exchange` | Either | Per action. Not yet implemented. |

"Either" means the consumer does not state whether it means an
*operating* MIC, a *segment* MIC, or tolerates both. The registry
accepts any valid MIC on a join. The ambiguity is the consumer's.

---

## The granularity question

Every edge references "a MIC" without stating the level. This has
not been a problem in practice because most consumers reference the
operating MIC — the venue that operates, the venue that closes on
holidays, the venue whose legal entity has an LEI.

The distinction matters for three consumer patterns:

**1. "The venue that closed for a holiday."** Exchange Calendar's
model is per-exchange, and it uses the operating MIC. A segment MIC
that closes independently of its operating MIC (rare, but the model
allows it) is not visible from Exchange Calendar's current schema.

**2. "The specific segment where this instrument trades."** Asset
Identifiers' `listings[].exchange` should be a segment MIC in
principle — a share can trade on a segment of an exchange without
trading on the whole exchange. The current data does not always
distinguish. A future consumer that needs segment-level accuracy
would need the consumer's schema to say so.

**3. "The operator's legal entity."** Needs the operating MIC, or
the operating MIC reached by walking `operating_mic` up the parent
chain. See the next section.

A consumer that wants to be explicit can declare its granularity:

- **Operating only.** The field must match an entry whose
  `mic_type == "OPERATING"`.
- **Segment only.** The field must match an entry whose
  `mic_type == "SEGMENT"`.
- **Either.** No constraint. This is the current state on every
  edge.

ISO 10383 does not mandate one. The registry publishes both; the
consumer chooses.

---

## The self-reference pattern

Every operating MIC self-references: `operating_mic == mic`. Every
segment MIC points to a parent, which may itself be a segment. The
parent chain terminates at an operating MIC.

A consumer that joins on `mic` and then wants the operator walks
`operating_mic` until the value equals the entry's own `mic`:

```python
entry = by_mic[mic]
root = entry["operating_mic"]
while root != entry["mic"]:
    entry = by_mic[root]
    root = entry["operating_mic"]

There is no separate parent_mic field or root_mic field. The
chain is computed, not stored. This is deliberate: storing the root
would create a second value to keep in sync during a parent change.

See docs/action_types.md for the full type system.
What ISO 10383 does not answer

Three things a consumer may expect from a venue registry that this
one does not contain:

1. Trading currency. Not stored per MIC. Derived from
country_code → ISO 4217 currency. A MIC in the United States
trades in USD by the country's convention, not by any field on the
entry. If a venue trades in a non-local currency (rare but real —
e.g., a US-dollar-denominated segment on a foreign exchange), this
registry cannot express it.

2. Operating hours. Not in this registry. Exchange Calendar
owns per-exchange trading hours. Better sourced there — the hours
differ per session, per holiday, per early close, and the calendar
registry models all three.

3. Legal entity identity. Pending. A MIC→LEI companion is
planned for v1.1.0, sourced from GLEIF's published mapping. Until
then, the legal_entity_name field on each entry is the
published string from SWIFT, not a canonical identifier.
Reverse lookup

For each sibling registry, which record resolves to a mic:
Registry	Record	Field
Exchange Calendar	exchanges/<file>.json	Top-level mic (or code)
Asset Identifiers	identifiers.json → each entry	exchange, and listings[].exchange
Corporate Actions	actions.json → each action (planned)	exchange

A consumer that finds a MIC in one of these fields and wants the
full entry reads iso10383.json and looks up mics[] by mic.
Editing this document

A change to any edge — a new registry that references mic, or a
change to an existing reference's granularity — is a change to this
document in the same commit as the schema change on the consumer
side. The consumer's PR adds the row; the consumer's PR also opens
a PR here or files an issue.

This document is the leaf-side view of the join graph. Each
consumer's README links to it. If the pattern moves to a shared
location later, it moves with its history.
