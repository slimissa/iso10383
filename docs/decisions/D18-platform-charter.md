# D18 — Platform charter

**Status:** Accepted
**Date:** 2026-10-XX
**Supersedes:** none
**Superseded by:** none
**Continues:** the D-series in `v1.0.0-decisions.md` (D1–D17)

---

## Problem

ISO 10383 has a README, and a decisions register, and eleven ADRs.
None of them states, on one page, what the registry is *for*, who
consumes it, and what it deliberately does not do. The README is a
sales pitch; the register records specific choices; the ADRs record
specific declines. A reader who asks "should we add feature X?"
has no single document to answer against.

The Big Data course this registry has been mapped to asks for a
*cahier des charges*. So does the registry. This is that document.

---

## Decision

ISO 10383 is a **canonical, versioned, machine-readable registry of
ISO 10383 Market Identifier Codes**, derived from SWIFT's monthly
publication, consumed as reference data by other systems, and
maintained under a documented release discipline.

### Consumers

| Consumer | Uses |
|----------|------|
| Exchange Calendar (`slimissa/exchange-calendar`) | Every exchange's MIC is validated against this registry |
| Tempus (`slimissa/Tempus`) | Planned `@market_context` compile-time validation |
| LAS_Shell (`slimissa/Las_shell`) | Planned market status detection and prompt display |
| The ecosystem itself | The MIC join graph at `docs/JOINS.md` is the reference for every registry that references a MIC |

No consumer pays. No consumer requires a wrapper to be published to
PyPI, npm, or crates.io. No consumer requires the registry to be
updated more frequently than SWIFT publishes.

### The three layers

| Layer | Artifact | Rule |
|-------|----------|------|
| RAW | `iso10383.json` | Never modified by tooling. Only human commits. |
| CURATED | The nine exports (SQL ×4, CSV ×4, Parquet) and the four wrapper bundles | Regenerated from RAW. Never hand-edited. Each generator has `--check`. |
| AGGREGATED | The two cross-registry snapshots (`tools/iso3166_snapshot.json`, `tools/exchange_calendar_snapshot.json`) | Joins, not aggregates. Read by the validator. |

The aggregated layer of ISO 10383 is thinner than ISO 4217's — it
has no per-region or per-anchor Parquet files. That is honest: MICs
do not aggregate the way currencies do. What ISO 10383 aggregates is
*other registries' keys*, and the two snapshots are that
aggregation.

**A layer may only assume what the layer below it guarantees.** The
CURATED exporters do not read the two cross-registry snapshots. The
snapshots are read only by the validator, at the boundary between
CURATED and the outside world.

### Out of scope

Named, with the ADR that declined each:

| Feature | Where it was decided |
|---------|----------------------|
| MIC→LEI companion | ADR 0008 — GLEIF's mapping is a strict subset of the existing `lei` field |
| MIC→BIC companion | ADR 0009 — no SWIFT-published source exists |
| Operating hours | Exchange Calendar owns this per exchange |
| Regulatory status per venue | Out of scope (D11) |
| Trading currency per MIC | Derived from `country_code` → ISO 4217, not stored |
| MIC→ISIN relationships | Many-to-many; belongs to an asset-identifiers context |

### The one non-deterministic component already in the pipeline

`tools/check_amendments.py` runs weekly. It fetches a source that
may or may not have changed, may or may not be reachable, and may
or may not have a shape the parser recognizes. It flags; it does
not write. Its output is a GitHub issue, not a commit.

This is the pipeline's existing *slow, expensive, non-deterministic*
stage. It is deliberately bounded: it cannot modify RAW, it cannot
modify CURATED, and its only output is a notification. The design
question the course asks — *"que devient un pipeline déterministe
quand on y branche un composant lent, coûteux et non déterministe?"*
— has already been answered for this one component: it goes before
the deterministic validator, not after.

### The cognitive layer

The course's séances 5–8 propose a *cognitive layer* — an agent that
reads context and decides something. For this registry, the
plausible place is the BLOCKED.md triage: which of the 29 blocked
sources could be automated next, at what cost, with what
traceability.

**Not decided in this charter.** What is decided is the boundary:

- An agent may *propose* a change.
- A deterministic validator *decides* whether the change enters the
  pipeline.
- RAW is never written by non-deterministic code.

The read surface the agent is allowed to consult — which files, at
what version, with what freshness guarantee — is the séance 5–6
deliverable, not this charter.

---

## Alternatives considered

**Let the README serve as charter.** Rejected. The README is
written for a prospective consumer. The charter is written for a
future maintainer deciding what to add. Different audiences,
different documents.

**Put the charter in a `docs/coursework/` folder.** Rejected. The
moment coursework lives in its own folder, it becomes a parallel
universe with separate commits and separate drift. Every séance
output goes in `docs/decisions/` with a D-number, next to the code
it describes.

**Write the charter at the ecosystem level, not per registry.**
Deferred. It may move if a fifth registry adopts the same shape.
For now it lives in the registry whose operations most resemble a
pipeline, because that is the registry the course is studying.

**Do nothing.** Rejected. The question "should we add feature X?"
will be asked again, and without a charter it is answered by
whoever is loudest in the moment.

---

## Consequences

- **Every future scope question references D18.** A proposal to add
  operating hours answers against the "Out of scope" table. A
  proposal to build a companion answers against the two declined
  ADRs. The document is the arbiter.
- **The séance 5–6 read surface spec references D18.** The agent's
  allowed inputs are bounded by what D18 names as the layers.
- **The séance 7–8 BLOCKED.md triage proposal references D18.** The
  cognitive layer's boundary — propose, don't decide — is decided
  here; the triage proposal fills in the mechanism.
- **The pattern may move.** If a fifth registry adopts the same
  shape, the charter is promoted to the ecosystem and each registry
  links to it. Today it is local, because there is no forcing
  function to move it.

---

## References

- The Big Data course syllabus, Séance 1
- [`README.md`](../../README.md) — the consumer-facing summary
- [`docs/LAYERS.md`](../LAYERS.md) — the layer model
- [`docs/JOINS.md`](../JOINS.md) — the cross-registry join graph
- [`docs/PROVENANCE.md`](../PROVENANCE.md) — per-field sourcing
- [`docs/decisions/0008-mic-lei-companion-declined.md`](./0008-mic-lei-companion-declined.md)
- [`docs/decisions/0009-mic-bic-companion-declined.md`](./0009-mic-bic-companion-declined.md)
- [`docs/decisions/v1.0.0-decisions.md`](./v1.0.0-decisions.md) — D1–D17
- [`BLOCKED.md`](../../BLOCKED.md)