# 0012 — The agent's read surface

**Status:** Accepted
**Date:** 2026-10-09
**Supersedes:** none
**Superseded by:** none

---

## Problem

ADR 0010 sets one boundary for any future agent: it may propose, a
deterministic validator decides, and no non-deterministic code writes
Layers 0–4. It does not say what the agent may *read*. Without that,
"give the agent context" means whatever file happens to be nearby, at
whatever version, with no way to tell whether it is stale.

This ADR is the spec an agent would be built against. It builds no
agent and no code.

---

## Decision

1. The agent reads only the files in the table below, and only at the
   version and freshness stated there.
2. The agent **writes nothing** to the repository. Its output is a
   *proposal file*, a document with a schema a validator can check. A
   proposal is not a commit and not a patch.
3. The agent never reads the live internet to answer a question about
   the registry. Evidence it cites from outside the tree is recorded in
   the proposal with a retrieval date, and is checked by a human.
4. Staleness is detected by running the existing freshness checks, not
   by the agent's own judgement.

---

## Rationale

### Five things called "context"

| View | Artifact | What it shows | What it costs to keep fresh |
|------|----------|---------------|-----------------------------|
| Registry view | `iso10383.json` | The MICs themselves | Nothing extra. The monthly refresh regenerates it. |
| Materialised view of other registries | `tools/iso3166_snapshot.json`, `tools/exchange_calendar_snapshot.json` | Country codes and the MICs Exchange Calendar uses | A manual re-vendor. `review_by` dates force the review: 2026-12-28 and 2027-09-28. |
| Cross-registry view | `docs/JOINS.md` | Who joins on `mic`, at what granularity | Hand-edited prose. No check ties it to the code. |
| Human view | `python3 tools/iso10383_cli.py info` | Version, dates, source hash, counts | Free. It reads Layer 1 each time. |
| Decision view | `docs/decisions/`, `docs/mic_lei_source_format.md`, `docs/mic_bic_source_format.md` | Why things are as they are | Hand-edited prose. A stale one misleads silently. |

The `JOINS.md` and decision-view rows are the weakest. No CI gate
fails when they drift from the data, so a document can keep describing
a decision after it has been reversed.

### The read surface

| File | Layer | Version semantics | Freshness guarantee |
|------|-------|-------------------|---------------------|
| `iso10383.json` | 1 | `meta.version`, currently 1.0.4, equal to `VERSION` (`check_version_consistency.py`) | `check_registry_freshness.py` fails CI if `meta.source_snapshot` is over 60 days old. That date is the download date, not SWIFT's publication date (ADR 0003). |
| The nine exports | 2 | Derived from Layer 1, no version of their own | `export_*.py --check` runs on every push, so a stale export fails CI |
| `wrappers/*/…/iso10383.json` | 3 | Byte-identical to Layer 1 | `sync_wrappers.py --check` and `check_cross_language.sh` |
| The two snapshots | 4 | `source_version` in each `.meta.json` | `check_snapshot_freshness.py` fails CI past `review_by`. `check_*_current.py` compare to the live sibling. |
| `CHANGELOG.md` | none | Release headings | `check_version_consistency.py` checks the top heading against `VERSION` (D8) |
| `docs/decisions/*.md`, `docs/JOINS.md`, `docs/PROVENANCE.md` | none | None. Date in the header only. | None |
| `raw/MIC_*.csv` | 0 | Not committed | Not readable from a clone. Excluded. |

The agent does not read Layer 0. It is absent from a clone, and
`meta.source_hash` is the only evidence of what it held.

### What the agent may write

Nothing in the repository. A proposal file is the agent's whole
output. Its path and branch are chosen by the later change that
implements the agent. It must not live in a Layer 0–4 location, and
this ADR does not create a folder for it.

Why not a patch: Layer 1 is generated. `LAYERS.md` § The one rule says
"never hand-edit a committed artifact", and `--check` modes revert it.
A correction to a MIC value cannot be applied locally at all. The next
refresh would overwrite it from SWIFT's file. That narrows what a
legitimate proposal can ask for, and the next section says how.

### The proposal shape

This is a sketch. It names fields a validator could check. It is not a
committed schema, and no `schema.proposal.json` exists.

**Case 1 — a MIC correction.** The values below are illustrative.
`observed` is the real current value for `XNYS`; the claim is not a
finding. The legitimate actions are to report
the discrepancy to the registration authority (ADR 0003 records its
request deadline) or to propose an allowlist addition, which needs an
ADR amendment (D17).

```json
{
  "proposal_type": "mic_correction",
  "registry_version": "1.0.4",
  "source_snapshot": "2026-09-23",
  "mic": "XNYS",
  "field": "website",
  "observed": "WWW.NYSE.COM",
  "claimed": "an illustrative value, not a real finding",
  "evidence": [
    {"url": "https://example.org/page", "retrieved_at": "2026-10-09"}
  ],
  "recommended_action": "report_to_ra"
}
```

A deterministic validator can check, with no model:

- `registry_version` equals `meta.version` and `source_snapshot`
  equals `meta.source_snapshot`. A mismatch means the proposal is
  stale.
- `mic` matches `^[A-Z0-9]{4}$` and exists in `mics[]`.
- `field` is one of the keys an entry carries.
- `observed` equals the entry's current value. This is the staleness
  check at proposal level.
- `recommended_action` is from a closed list and `evidence` is
  non-empty.

**Case 2 — a source unblocking.** A proposal that says how a currently
unreachable source could be fetched. Its fields (source id, method,
cost bound, retry budget) depend on a list of blocked sources that
**is not in this tree**. This ADR does not invent them. The séance 7–8
ADR fixes the shape once that list is available.

### The freshness problem

An agent reading `iso10383.json` 1.0.4 is reading the current version
only if `VERSION` still says 1.0.4. An agent reading a snapshot may be
reading one past its `review_by` date. The detection is not new. The
agent's run starts by executing `check_registry_freshness.py` and
`check_snapshot_freshness.py` and recording their exit codes. If
either fails, the agent stops and says so. It does not try to repair
the data.

One gap: nothing checks that `JOINS.md` and the decision documents
match the data (see the first table). The agent treats those as
orientation, and trusts only the JSON for any value it cites.

---

## Alternatives considered

**Give the agent write access to a branch.** Rejected. A branch write
is a commit, and a commit by a non-deterministic author is the thing
ADR 0010 forbids. It also bypasses the one place Layer 1 is allowed to
change, `fetch_swift_mic.py`.

**Let the agent open pull requests directly.** Rejected. The refresh
already opens PRs, but its content is a deterministic function of
SWIFT's file. A PR authored by an agent has no such function, and a
reviewer could not tell which part was regenerated and which was
generated.

**Let the agent query the live ISO 20022 page.** Rejected. The
registry parses the CSV, not the page. A live read is unrepeatable,
carries no version, and brings network failure and page-layout drift
into every answer. Evidence from the web is allowed, but only as
dated citations a human checks.

**Give the agent the whole repository.** Rejected. Most of it is
generated, and the exports and bundles repeat Layer 1 up to thirteen
times. Reading them adds cost and no information.

---

## Consequences

- **A proposal schema and its validator are separate, later work.**
  This ADR sketches them and writes neither.
- **The `JOINS.md` and decision-view gap stays open.** If an agent is
  ever built, a check that those documents agree with the data is the
  first thing it needs.
- **The séance 7–8 triage ADR (BLOCKED.md) is not written.** The file
  it is about is not in this tree. It will cite this ADR for the read
  surface and fill in the Case 2 shape. This ADR does not link to it,
  because it does not exist.
- **ADR 0010** states the boundary this ADR specifies. **ADR 0011**
  describes the deterministic refresh the agent must never write into.

---

## References

- [`docs/LAYERS.md`](../LAYERS.md)
- [`docs/JOINS.md`](../JOINS.md)
- [`tools/iso10383_cli.py`](../../tools/iso10383_cli.py)
- [`tools/iso3166_snapshot.json`](../../tools/iso3166_snapshot.json)
- [`tools/exchange_calendar_snapshot.json`](../../tools/exchange_calendar_snapshot.json)
- [`tools/check_registry_freshness.py`](../../tools/check_registry_freshness.py)
- [`tools/check_snapshot_freshness.py`](../../tools/check_snapshot_freshness.py)
- [`CHANGELOG.md`](../../CHANGELOG.md)
- [`docs/mic_lei_source_format.md`](../mic_lei_source_format.md)
- [`docs/mic_bic_source_format.md`](../mic_bic_source_format.md)
- [`docs/decisions/0008-mic-lei-companion-declined.md`](./0008-mic-lei-companion-declined.md)
- [`docs/decisions/0009-mic-bic-companion-declined.md`](./0009-mic-bic-companion-declined.md)
- [`docs/decisions/0010-platform-charter.md`](./0010-platform-charter.md)
- [`docs/decisions/0011-reprocessing.md`](./0011-reprocessing.md)
- [`docs/decisions/v1.0.0-decisions.md`](./v1.0.0-decisions.md)
