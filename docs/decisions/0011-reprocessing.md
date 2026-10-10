# 0011 — Reprocessing and the `REMOVED > 0` guard

**Status:** Accepted
**Date:** 2026-10-09
**Supersedes:** none
**Superseded by:** none

---

## Problem

Three questions about the monthly refresh have no single answer in
the tree:

1. What does the refresh do, step by step, and which tool does each
   step?
2. What does "reprocess from raw" mean in this registry?
3. Is this registry a stream, a batch, or neither?

A fourth question surfaced while answering the first. D10 and ADR 0003
say a refresh with `REMOVED > 0` "fails" until a human confirms. This
ADR checks whether the workflow does that. It does not.

---

## Decision

1. The refresh is a **monthly batch**. It is the correct shape for a
   source that publishes monthly.
2. D10 stays as policy: a removed MIC needs human confirmation before
   merge. When this ADR was written the guard was **not enforced by
   `refresh.yml`**; that defect was fixed on 2026-10-10 (see the
   Amendment). The PR now opens as a draft on a removal.
3. Reprocessing from Layer 0 is **not a general capability** of this
   repository. Layer 0 is gitignored and only the current file is
   kept. Replaying history means checking out a tag, not re-parsing.
4. The registry is not a stream and does not become one without one of
   the triggers named below.

---

## Rationale

### The refresh, step by step

`.github/workflows/refresh.yml` runs at 00:00 UTC on the 15th of every
month, and on manual dispatch. It is the only `schedule:` entry under
`.github/`.

| # | Step | Tool | Layer touched |
|---|------|------|---------------|
| 1 | Download SWIFT's CSV to `raw/MIC_new.csv` | `tools/fetch_swift_mic.py` `download(force=True)` | 0 |
| 2 | Copy the old registry to `/tmp/iso10383.old.json` | `cp` | none |
| 3 | Parse Layer 0 into `iso10383.json` with `--version` set to `VERSION` and `--snapshot-date` set to today | `tools/fetch_swift_mic.py` | 1 |
| 4 | Diff old against new | `tools/refresh_diff.py` | none |
| 5 | Regenerate CSV, SQL, Parquet, and the four bundles | `export_csv.py`, `export_sql.py`, `export_parquet.py`, `sync_wrappers.py` | 2, 3 |
| 6 | Run the six-layer validator and the root tests | `tools/validate.py`, `pytest tests/` | none |
| 7 | Open a pull request | `peter-evans/create-pull-request@v6` | none |

Nothing merges on its own. The workflow opens a PR and a human merges.

### The guard, as designed

`tools/refresh_diff.py` compares two registries by `mic`. It prints
NEW, EXPIRED, CHANGED, and REMOVED counts to stdout. If any MIC in the
old file is absent from the new one it lists up to 20 of them on
stderr and exits 1. Otherwise it exits 0. The policy is D10 and
ADR 0003 § Decision 2: a removal is the change class most likely to
break a consumer, so a human reads it first.

### The guard, as wired

As of the Amendment (2026-10-10) below, the refresh workflow behaves
as follows when a refresh removes a MIC:

- The diff step sends both streams of `refresh_diff.py` to
  `/tmp/diff.txt`, captures the tool's own exit code, writes it to
  `GITHUB_OUTPUT`, prints the file to the log, and exits 0. The step
  never fails.
- The pull request always opens. When the code is `1` it opens as a
  **draft** whose body says `REMOVED > 0` and requires human
  confirmation. When the code is `0` it opens as a normal PR. A draft
  cannot be merged until a human marks it ready for review.
- The removed MICs are in the workflow log, not in the PR body.

The original finding (2026-10-09) was that the exit code was lost in a
pipeline and the guard never fired. That history, and the claims it
contradicted in ADR 0003, `docs/PROVENANCE.md`, the README, LAYERS and
CONTRIBUTING, is recorded in the amendments of this ADR and ADR 0003.

One wiring note remains open. ADR 0003 names
`check_snapshot_freshness.py` as the 60-day gate (Decision 1 and
References). The 60-day gate is `check_registry_freshness.py`.
`check_snapshot_freshness.py` checks the `review_by` dates of the two
Layer 4 snapshots.

### Guard rails compared

| Guard | Tool | Trips when | Result |
|-------|------|-----------|--------|
| Removal | `refresh_diff.py` | A MIC in old is absent in new | Exit 1. The workflow opens the PR as a draft. |
| Registry age | `check_registry_freshness.py` | `meta.source_snapshot` older than 60 days | Fails CI |
| Snapshot review | `check_snapshot_freshness.py` | Today is past a snapshot's `review_by` | Fails CI. Today: 2027-01-10 (Exchange Calendar), 2027-09-28 (ISO 3166). |
| Allowlist | `KNOWN_EXCHANGE_CALENDAR_GAPS` in `validate.py` | A MIC referenced by Exchange Calendar is absent and not in the frozenset (empty as of 2026-10-10) | An error from the validator (a warning under `--advisory`). The frozenset only suppresses; it is empty, so every absent MIC trips it. Edits need an ADR amendment (D17). |

The last three block in CI. The first does not stop the workflow; it
marks the PR as a draft.

### What "reprocess from raw" means here

Layer 0 is `raw/MIC_YYYYMMDD.csv`. `LAYERS.md` says it is gitignored
and that "only the current snapshot is kept locally". In CI it exists
only for the length of one run.

- **Layer 1 from Layer 0.** One command, deterministic, byte-identical
  for identical input. `meta.source_hash` lets anyone holding the CSV
  confirm which file produced a given `iso10383.json`.
- **Layers 2 and 3 from Layer 1.** One command each, with `--check`.
  They are cheap and have no independent information.
- **Old versions.** The repository cannot re-parse the SWIFT file that
  produced v1.0.2, because that file is not kept. What it can do is
  `git checkout v1.0.2`. The committed Layer 1 in a tag is the archive.

So "immutable RAW, cheap CURATED" is half true here. Curated is cheap.
Raw is not stored. That is a deliberate choice recorded in
`LAYERS.md` (size and SWIFT's licence terms), and this ADR does not
change it. A registry that never needs to replay old inputs does not
have a reprocessing problem, but it also cannot reproduce Layer 1 for
a past month without SWIFT's own archive.

### Is it a stream

No. SWIFT publishes on the second Monday of the month. The pipeline
runs on the 15th. A monthly batch is the correct shape.

It would become a stream if one of these held:

1. SWIFT offered a push or change-feed interface for the MIC file.
2. A consumer needed freshness under a day, and said so.
3. A source changed continuously, not on a monthly cycle.

None holds in this tree. ADR 0003 already rejected weekly and
publication-day refreshes for the same reason.

---

## Alternatives considered

**Model the refresh as a Kafka `readStream`.** Rejected. There is one
file a month. A broker would add operations cost and no information.

**Event-driven refresh on SWIFT publication.** Rejected. SWIFT offers
no event to subscribe to that this tree knows of, and polling a
monthly file more often only finds nothing. ADR 0003 rejected weekly
polling.

**Keep every raw CSV in git, so any month can be replayed.** Rejected
by `LAYERS.md` on size (~7 MB a year) and licence grounds. Not
reopened here.

**Materialise a view of the source.** Rejected. Layer 1 already is
that view, and `source_hash` ties it to the file.

**Leave the guard as a reviewer convention.** Rejected as a long-term
state. The workflow now marks the PR as a draft on a removal.

---

## Consequences

- **The wiring defect is fixed** (Amendment, 2026-10-10). The removed
  MICs are still in the workflow log only, not in the PR body.
- **ADR 0003 and the docs that described the guard** were corrected
  on 2026-10-10. The wrong tool name in ADR 0003 (Decision 1 and
  References) is not yet corrected.
- **ADR 0010** defines the layer vocabulary used here.
- **ADR 0012** defines what an agent may read of the registry. The
  refresh described here is the deterministic path it must not write
  into.
- **Any proposal to change cadence, add a second source, or build a
  stream pipeline** answers against the three triggers above.

---

## References

- [`.github/workflows/refresh.yml`](../../.github/workflows/refresh.yml)
- [`tools/refresh_diff.py`](../../tools/refresh_diff.py)
- [`tools/fetch_swift_mic.py`](../../tools/fetch_swift_mic.py)
- [`tools/check_registry_freshness.py`](../../tools/check_registry_freshness.py)
- [`tools/check_snapshot_freshness.py`](../../tools/check_snapshot_freshness.py)
- [`docs/LAYERS.md`](../LAYERS.md)
- [`docs/PROVENANCE.md`](../PROVENANCE.md)
- [`docs/decisions/0003-monthly-refresh.md`](./0003-monthly-refresh.md)
- [`docs/decisions/0007-cross-registry-allowlist.md`](./0007-cross-registry-allowlist.md)
- [`docs/decisions/0010-platform-charter.md`](./0010-platform-charter.md)
- [`docs/decisions/0012-agent-read-surface.md`](./0012-agent-read-surface.md)
- [`docs/decisions/v1.0.0-decisions.md`](./v1.0.0-decisions.md) — D10, D17

---

## Amendment (2026-10-10)

Corrections against the original text.

**The diff mechanism changed.** The pipeline described in the original
§ The guard, as wired no longer exists. `refresh.yml` now redirects both
streams of `refresh_diff.py` to `/tmp/diff.txt`, captures the tool's
own exit code with `code=$?`, and prints the file to the log. The pipe
had returned the exit code of the last command in it, not the tool's.
See ADR 0003 § Amendment.

**The guard's behavior is now explicit.** The refresh workflow marks
the PR as a draft when `code == 1` (removals present) and says so in
the body. Previously the PR opened with a bare `0` or `1`. See
`refresh.yml`.

**`--version` is passed to the fetcher.** `fetch_swift_mic.py`
defaults `--version` to `0.1.0`; the workflow did not override it, so a
refresh would have written `meta.version` `0.1.0`. The workflow now
passes `--version "$(cat VERSION)"`.

**The branch and title are computed in a prior step.** The `branch:`
and `title:` inputs contained `$(date ...)`, which action inputs do not
expand. `git check-ref-format` rejects the literal branch name. A step
now writes `month` and `date` to `GITHUB_OUTPUT`, and the inputs use
those.

Not changed: the `meta.updated` / `meta.source_snapshot` ownership
question (the fetcher sets them equal, `release.sh` writes
`meta.updated` afterwards). That is a separate finding.
