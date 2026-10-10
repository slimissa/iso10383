# 0010 — Platform charter

**Status:** Accepted
**Date:** 2026-10-09
**Supersedes:** `docs/decisions/D18-platform-charter.md` (an undated draft; removed in the commit that adds this file)
**Superseded by:** none

---

## Problem

The registry has a README, a locked-decisions register (D1–D17), and
nine ADRs. None of them says on one page what the registry is *for*,
who consumes it, which layers it has, and what it deliberately does
not do. A maintainer asked "should we add feature X?" has no single
document to answer against.

A Big Data course asks for a *cahier des charges* and a layer model
for a pipeline. This registry already is such a pipeline. This ADR
writes the charter down and fixes the vocabulary the later ADRs use.

---

## Decision

ISO 10383 is a **canonical, versioned, machine-readable registry of
ISO 10383 Market Identifier Codes**. It is derived from SWIFT's
monthly publication, consumed as reference data by other systems, and
maintained under the release discipline in `docs/RELEASE_PATTERN.md`.

### Consumers

| Consumer | Use | Basis |
|----------|-----|-------|
| Exchange Calendar | Every MIC it references must exist here, or be allowlisted (the allowlist is empty as of 2026-10-10) | README § consumers; `tools/exchange_calendar_snapshot.json` holds its 74 MICs; D17, ADR 0007 |
| Asset Identifiers | `exchange` and `listings[].exchange` join on `mic` | `docs/JOINS.md` |
| Corporate Actions (planned) | Each action's `exchange` joins on `mic` | `docs/JOINS.md`, marked "Not yet implemented" |
| Tempus | `@market_context` type-level validation | README only |
| LAS_Shell | Market status detection and prompt display | README only |
| The ecosystem | `docs/JOINS.md` is the join reference for every registry that references a MIC | `docs/JOINS.md` |

The last two rows rest on the README alone. Those repositories are not
in this tree, so this ADR does not verify them. Nothing in this tree
shows that any consumer pays, requires wrapper publication, or needs
updates more often than SWIFT publishes. The README's "What's next"
lists wrapper publication with the trigger "a consumer tries to
install one", which implies none has.

### The layers

`docs/LAYERS.md` defines five layers. They are the authority for
vocabulary in this repository.

| Layer | Name | Artifact | Committed |
|-------|------|----------|-----------|
| 0 | Raw | `raw/MIC_YYYYMMDD.csv`, SWIFT's file byte-for-byte | No (`.gitignore` excludes `raw/`) |
| 1 | Curated | `iso10383.json` | Yes |
| 2 | Derived | Nine exports at the repo root: SQL ×4, CSV ×4, Parquet | Yes |
| 3 | Bundled | Four byte-identical copies of Layer 1 under `wrappers/` | Yes |
| 4 | Cross-referenced | `tools/iso3166_snapshot.json`, `tools/exchange_calendar_snapshot.json` | Yes |

The course's three-layer model maps onto these as follows. The
mapping is approximate and this ADR says where it is not.

| Course term | Registry layer | Where the mapping is imperfect |
|-------------|----------------|--------------------------------|
| RAW | Layer 0 | In this registry RAW is **not** `iso10383.json`. It is the gitignored SWIFT CSV, and only the current file is kept locally. |
| CURATED | Layers 1, 2, 3 | Layers 2 and 3 are projections of Layer 1 and add no information. |
| AGGREGATED | Layer 4, loosely | Layer 4 holds *joins*, not aggregates. It is validation input and contributes no fields to Layer 1 (`docs/LAYERS.md` § Layer 4). MICs do not aggregate the way currencies do, so this registry's aggregated layer is thin by nature. |

**The layer rule.** A layer may only assume what the layer below it
guarantees. Concretely:

- Layer 1 is a deterministic function of Layer 0 plus the fetcher's
  code (`tools/fetch_swift_mic.py`). Its `meta.source_hash` is the
  digest of the Layer 0 file it came from.
- Layers 2 and 3 are regenerated from Layer 1. Each generator has a
  `--check` mode that CI runs on every push.
- Layer 4 snapshots are produced from sibling registries by
  `tools/gen_*_snapshot.py`. They never feed Layer 1.

Layer 4 is read by more than the validator. `tools/validate.py` uses
both snapshots. `tools/check_snapshot_freshness.py` reads their
`review_by` dates. `tools/check_iso3166_current.py` and
`tools/check_exchange_calendar_current.py` compare them to the live
siblings. None of these writes to Layers 0–3.

### Out of scope

| Feature | Where it was decided |
|---------|----------------------|
| MIC→LEI companion | ADR 0008. GLEIF's mapping is a strict subset of the existing `lei` field. |
| MIC→BIC companion | ADR 0009. No published source file was found. |
| Operating hours | D11. `docs/JOINS.md` shows Exchange Calendar models per-exchange closures. |
| Regulatory status per venue | D11 |
| Trading currency per MIC | D11 |
| MIC→ISIN | D11 |

D11 gives one reason for all six: each is a separate companion file
with its own source and cadence, and bundling dilutes the primary
contract. The extra reasons above (subset, no source) come from the
two reconnaissance documents. This ADR does not add reasons D11 does
not give for the last four.

### Non-determinism today

The course's guiding question is what becomes of a deterministic
pipeline when a slow, costly, non-deterministic component is attached
to it.

**This registry has no such component today.** The nearest things are
network steps, and none is cognitive:

| Step | Where | Non-deterministic because |
|------|-------|---------------------------|
| SWIFT download | `refresh.yml`, monthly on the 15th | The remote file changes |
| Sibling comparison | `check_iso3166_current.py`, `check_exchange_calendar_current.py`, `check_iso4217_current.py`, run in the `validate-json` job on every push | The live sibling registries change |

Both read the outside world and neither interprets it. The SWIFT
download feeds a deterministic parse. The sibling checks only compare.

An earlier draft of this charter described a weekly job,
`tools/check_amendments.py`, as the pipeline's existing non-
deterministic stage. **No such file or schedule exists in this tree.**
The only `schedule:` entry under `.github/` is the monthly refresh.
`docs/RELEASE_PATTERN.md` mentions "amendment cycles" in prose and
nothing else does. If the tool exists in a local clone, it is not on
`main`.

### The cognitive layer

A cognitive layer is an agent that reads context and proposes
something. For this registry the boundary is:

1. An agent may **propose**. A proposal is a document, not a commit.
2. A deterministic validator **decides** whether anything enters the
   pipeline.
3. No non-deterministic code writes Layers 0–4. Layer 1 is written
   only by `tools/fetch_swift_mic.py`, whose output is
   byte-identical for identical input.

What an agent may read, at what version, with what freshness
guarantee, is decided in ADR 0012. This charter does not decide it.

---

## Rationale

**Why five layers and not three.** The repository already has five,
documented in `LAYERS.md`, and every tool's docstring uses that
numbering. Renaming them to fit a course would create a second
vocabulary that drifts. The mapping table keeps both readable.

**Why say there is no non-deterministic component.** The honest answer
to the course's question is that the registry avoided the problem by
having no such stage. The first one, if built, is a design decision
(ADR 0012), not a retrofit of something that already runs.

**Why correct the draft.** The draft charter's claims about
`check_amendments.py` and `BLOCKED.md` cannot be checked against the
tree. A charter cited as the arbiter of scope cannot rest on files
that are absent.

---

## Alternatives considered

**Let the README serve as charter.** Rejected. The README speaks to a
prospective consumer. The charter speaks to a maintainer deciding what
to add.

**Put coursework in a `docs/coursework/` folder.** Rejected. It would
become a parallel record with separate drift. Séance outputs live in
`docs/decisions/` as numbered ADRs, next to the code they describe.

**Write the charter at ecosystem level.** Deferred. If a fifth
registry adopts the same shape, the charter can be promoted and each
registry can link to it.

**Keep the three-layer course names as the registry's own.**
Rejected. RAW would have to mean `iso10383.json`, which the fetcher
writes and `LAYERS.md` calls Layer 1.

---

## Consequences

- **Scope questions answer against this ADR.** A proposal for operating
  hours, a companion file, or regulatory status cites the out-of-scope
  table.
- **`D18-platform-charter.md` is deleted** in the same commit. Nothing
  else links to it.
- **ADR 0011** describes the monthly refresh against the layer model
  here and records that the `REMOVED > 0` guard does not fire as
  wired.
- **ADR 0012** specifies the agent's read surface within the layer
  boundary stated here.
- **A BLOCKED.md triage ADR (the séance 7–8 deliverable) is not yet
  written.** `BLOCKED.md` is not in this tree. See ADR 0012 §
  Consequences.

---

## References

- [`README.md`](../../README.md)
- [`docs/LAYERS.md`](../LAYERS.md)
- [`docs/JOINS.md`](../JOINS.md)
- [`docs/PROVENANCE.md`](../PROVENANCE.md)
- [`docs/RELEASE_PATTERN.md`](../RELEASE_PATTERN.md)
- [`docs/decisions/0007-cross-registry-allowlist.md`](./0007-cross-registry-allowlist.md)
- [`docs/decisions/0008-mic-lei-companion-declined.md`](./0008-mic-lei-companion-declined.md)
- [`docs/decisions/0009-mic-bic-companion-declined.md`](./0009-mic-bic-companion-declined.md)
- [`docs/decisions/0011-reprocessing.md`](./0011-reprocessing.md)
- [`docs/decisions/0012-agent-read-surface.md`](./0012-agent-read-surface.md)
- [`docs/decisions/v1.0.0-decisions.md`](./v1.0.0-decisions.md) — D1–D17
