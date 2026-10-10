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
   merge. The guard is **not enforced by `refresh.yml` as written**,
   and this ADR records that as a defect, not as design.
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
| 3 | Parse Layer 0 into `iso10383.json` with `--snapshot-date` set to today | `tools/fetch_swift_mic.py` | 1 |
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

I reproduced the workflow's diff step on `/tmp` copies, removing
`XNYS` from a copy of `iso10383.json`:

- `refresh_diff.py` alone exits **1**, prints `REMOVED:  1` on stdout,
  and prints the removed MIC and the FAIL line on stderr.
- The workflow runs it as
  `python3 tools/refresh_diff.py OLD NEW | tee /tmp/diff.txt` with
  `set +e`, then `echo "code=$?"`. GitHub Actions runs an unlabeled
  `run:` step as `bash -e {0}`, which has no `pipefail`. Run the same
  way, the step printed **`code=0`**.
- `/tmp/diff.txt` held the four count lines and **not** the removed
  MIC. `tee` only saw stdout.

[Confirmed] on a local shell with the same flags. [Likely] on the
GitHub runner, which I could not run.

Consequences of that wiring:

| Claim | Where made | What the tree shows |
|-------|-----------|--------------------|
| The step's exit code is the signal | ADR 0003 § Decision 2 | `code` is `tee`'s status, always 0 |
| The PR body names the removed MICs | ADR 0003 § Decision 3 | The body holds the `code` value and a pointer to the log. It names no MIC. |
| `REMOVED > 0` "fails the job's diff step" | `docs/PROVENANCE.md` § Refresh cadence | The step is run under `set +e` and never fails |
| `refresh.yml` "refuses to open a pull request" on removal | ADR 0003 § Addendum | The PR always opens. The same ADR's Decision 2 and Alternatives say it does. |
| The PR body points to `/tmp/diff.txt` "in the workflow log" | `refresh.yml` | The file is never printed to the log |

The only working part of D10 today is the reviewer checklist line in
the PR body: "If `REMOVED > 0`, confirm the removal is intentional."
That line depends on the reviewer opening `refresh_diff.py` output
themselves.

Two further wiring notes, both [Likely]. The `branch:` and `title:`
inputs contain `$(date ...)`. Action inputs are not passed through a
shell, so the literal text is probably used. Separately, ADR 0003 names
`check_snapshot_freshness.py` as the 60-day gate (Decision 1 and
References). The 60-day gate is `check_registry_freshness.py`.
`check_snapshot_freshness.py` checks the `review_by` dates of the two
Layer 4 snapshots.

### Guard rails compared

| Guard | Tool | Trips when | Result |
|-------|------|-----------|--------|
| Removal | `refresh_diff.py` | A MIC in old is absent in new | Exit 1, but see above |
| Registry age | `check_registry_freshness.py` | `meta.source_snapshot` older than 60 days | Fails CI |
| Snapshot review | `check_snapshot_freshness.py` | Today is past a snapshot's `review_by` | Fails CI. Today: 2026-12-28 (Exchange Calendar), 2027-09-28 (ISO 3166). |
| Allowlist | `KNOWN_EXCHANGE_CALENDAR_GAPS` in `validate.py` | A MIC referenced by Exchange Calendar is absent and not in the frozenset of `XBEK`, `XNBO`, `XQSE` | Fails the validator. Edits need an ADR amendment (D17). |

The last three block in CI. The first only advises, and by the wiring
above it does not even advise reliably.

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
state. The policy says "fails". The workflow does not.

---

## Consequences

- **The wiring defect needs a separate code change.** This ADR writes
  none. The change, in outline: give the diff step `shell: bash` (which
  enables `pipefail`) or read `PIPESTATUS[0]`; send stderr into
  `diff.txt`; put the removed MICs in the PR body; and either fail the
  PR or label it when the code is 1. That change should cite D10 and
  this ADR.
- **ADR 0003 and `docs/PROVENANCE.md` need amendment notes** for the
  contradictions in the table above, and ADR 0003 for the wrong tool
  name. This ADR does not edit them.
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
