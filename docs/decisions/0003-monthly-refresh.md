# 0003 — Monthly refresh

**Status:** Accepted
**Date:** 2026-09-23
**Supersedes:** none
**Superseded by:** none

---

## Context

ISO 10383 is published by SWIFT on a **monthly** cadence. A registry
that tracks it must be updated monthly, or it will fall behind
reality and silently produce wrong answers for downstream consumers.

Three questions determine how the refresh works:

1. **What is the publication cadence?** When does SWIFT publish?
2. **How stale is too stale?** When should CI fail because the
   registry has not been updated?
3. **What happens when the source removes a MIC?** Is a removal
   merged silently, refused, or escalated?

Every answer has downstream consequences. This ADR fixes all three.

---

## Publication cadence

From the ISO 10383 FAQ:

- **Publication day:** the **second Monday** of each month, or the
  following business day if that Monday is a Belgian public holiday.
- **Effective day:** the fourth Monday of the month.
- **Request deadline:** a request received by the first Monday of
  the month is processed for that month's publication.

The registry's `meta.source_snapshot` is the download date, not the
publication date. The download may happen on any day on or after the
publication day.

---

## Decision 1 — Freshness gate at 60 days

CI fails if `meta.source_snapshot` is more than **60 days old**.
Enforced by `tools/check_snapshot_freshness.py`.

Sixty days is one full missed cycle. A snapshot that is 60 days old
means the refresh process did not run in September *or* October. That
is the correct threshold for two reasons:

- **Tighter (30 days)** would fail during a normal month in which
  the refresh ran on the 15th but the current date is the 16th of
  the next month and the file has not yet been updated. False
  positives are expensive: a red CI on a healthy repository trains
  maintainers to ignore the signal.
- **Looser (90 days)** allows three missed cycles. By the third
  missed publication, the registry is materially behind.

Sixty days is the smallest threshold that tolerates a normal
mid-month query without a false failure.

### How it is enforced

```bash
python3 tools/check_snapshot_freshness.py
```

Reads `iso10383.json`'s `meta.source_snapshot`, computes the age in
days, and exits 1 if the age exceeds the threshold. The threshold is
overridable with `--max-days` for testing.

CI runs the check on every push. A stale snapshot fails the
`validate-json` job.

---

## Decision 2 — REMOVED > 0 is a hard failure

A refresh that removes a MIC from the registry requires human
confirmation before merging. The refresh workflow opens the pull
request as a draft with the removal count in the body (see the
Amendment of 2026-10-10 at the end of this ADR).

Enforced by `tools/refresh_diff.py`, which compares the old registry
to a newly generated one and exits 1 if any MIC present in the old
version is absent from the new one.

### Why

A removed MIC is the change class most likely to break downstream
consumers:

- A venue that stops appearing in the source may have been
  **withdrawn** (a real closure) or **temporarily delisted** (an
  administrative issue at SWIFT).
- A downstream consumer that pins a MIC in a risk config or an
  order-routing table will fail at the next registry load.
- A MIC removal is a **signal** that a venue no longer exists or has
  been restructured. That signal deserves a human reading the diff,
  not a bot merging it.

The alternative — auto-merge on removal — is how a consumer
discovers a MIC vanished by having their order routed to a MIC that
no longer exists. The failure mode is asymmetric: the cost of a
delayed removal is one more day of stale data; the cost of an
unreviewed removal is a broken order.

### How it is enforced

`.github/workflows/refresh.yml` runs the diff step with `set +e` to
capture the exit code, then writes it to `GITHUB_OUTPUT`. The PR is
opened regardless, as a draft when the code is `1`. The signal is the exit code — `1` means removed
MICs exist. A reviewer must check the diff and confirm before
merging.

The workflow does not auto-close the PR on `REMOVED > 0`. An open
PR with the diff is more useful than a rejected one with no record.

### The four diff shapes

A monthly refresh produces one of four shapes:

| Shape | Meaning | Action |
|-------|---------|--------|
| NEW only | New MICs added | Merge after review |
| NEW + EXPIRED | Some existing MICs expired; new ones added | Merge after review |
| CHANGED only | Names, categories, or countries updated | Merge after review |
| Any + REMOVED | At least one MIC removed from the source | Human confirmation required |

The first three are routine. The fourth is an event.

---

## Decision 3 — The refresh runs on the 15th

`.github/workflows/refresh.yml` runs on the **15th of every month at
00:00 UTC**, and on manual dispatch.

The 15th is the first day on which the second-Monday publication is
certainly available. Publications on the second Monday fall between
the 8th and the 14th of the month. Waiting one day avoids racing the
publication itself.

The workflow:

1. Downloads the current SWIFT file to `raw/MIC_new.csv`.
2. Copies the current `iso10383.json` to `/tmp/iso10383.old.json`.
3. Runs `tools/fetch_swift_mic.py` with `--snapshot-date` set to the
   current UTC date.
4. Diffs old vs. new with `tools/refresh_diff.py`.
5. Regenerates all nine Layer 2 artifacts.
6. Regenerates all four Layer 3 bundles.
7. Runs the six-layer validator and the root test suite.
8. Opens a pull request.

The PR body carries the diff summary. If step 4 exits 1 (removed
MICs exist), the PR is still opened, and the body names the removed
MICs so the reviewer sees them without opening the workflow log.

---

## Consequences

### For the schema

None. The schema does not encode the refresh cadence.

### For the validator

The freshness gate is a separate tool, not a validator layer. The
validator checks data integrity; the freshness gate checks metadata
age. Combining them would make it impossible to run the validator
against a synthetic fixture older than 60 days.

### For the release script

`scripts/release.sh` runs `check_snapshot_freshness.py` as part of
its gate. A release cannot be cut against a stale snapshot.

### For the tests

The tests do not exercise the freshness gate directly. The gate has
its own test at the CI level: the `validate-json` job invokes it and
fails the job if it exits 1. Running the check locally is the
maintainer's responsibility.

### For consumers

`meta.source_snapshot` is the version consumers should pin against
if they need reproducibility. A consumer reading a snapshot from
2026-09-23 knows they are reading the registry as it was on that
day.

`meta.updated` is the date the JSON was generated. On the
2026-09-23 snapshot, both are the same date. They diverge when a
registry is regenerated from a cached raw file on a later day.

---

## Alternatives considered

**Per-entry `last_verified` dates, as ISO 3166 uses.** Rejected. MIC
data changes as a block — SWIFT publishes a new file — not as a
field-by-field curation. A per-entry timestamp would say nothing
useful, and the freshness gate would have to compute a minimum
across 2,883 entries. A single `meta.source_snapshot` is the
correct granularity.

**A 30-day freshness threshold.** Rejected. False positives during
normal months. See "Decision 1."

**A 90-day freshness threshold.** Rejected. Tolerates three missed
cycles. See "Decision 1."

**Auto-merge removals.** Rejected. See "Decision 2."

**Refuse the refresh on `REMOVED > 0` without opening a PR.**
Rejected. An open PR with a diff is more useful to a reviewer than
a rejected run with no artifact. The exit code is the signal; the
PR is the record.

**Refresh on the publication day itself.** Rejected. Racing the
publication risks parsing a partially uploaded file. The 15th is
safe.

**Refresh weekly.** Rejected. The source changes monthly. Weekly
refreshes would find nothing on three out of four runs and would
clutter the git history.

**Refresh on manual dispatch only.** Rejected. A registry that
depends on a human remembering to run a command will go stale.
The schedule is the point.

---

## Addendum — the `REMOVED > 0` guard

`refresh.yml` opens the pull request as a draft when the monthly diff
removes any MIC. A removal requires human confirmation before merge.

Rationale: removals are the change class most likely to break
downstream consumers. A consumer that pins a MIC in a risk config or
an order-routing table will fail at the next registry load. The
guard makes that a deliberate decision, not a silent one.

The guard is implemented in `tools/refresh_diff.py`, which exits 1
when any MIC present in the previous snapshot is absent from the new
one. The workflow runs the diff with `set +e` so the exit code is
captured and included in the PR body. The PR is opened regardless of
the exit code; the code is the signal.

Reference for sibling registries: when ISO 3166 or ISO 4217 adds a
scheduled refresh for its foreign snapshots, cite this section. The
guard shape is:

1. Compute the diff between old and new.
2. Count removals.
3. If removals > 0: exit non-zero, but open the PR anyway as a draft
   with the count in the body. The removed identifiers are in the
   workflow log.
4. A human reads the PR and confirms before merge.

---

## Open questions

**What if SWIFT changes the publication cadence?** A future ADR
amends the schedule and the freshness threshold. The evidence for
the change would be a persistent failure of the current schedule.

**What if SWIFT's server blocks GitHub's IP range?** The download
step fails loudly. The fix is a manual refresh from a different
network, or a proxy. Not a v1.0.0 concern.

**What if the source file's column set changes?** The fetcher
raises on unknown columns. A new column is a schema change and
requires a code change, not a silent absorb. This is intentional.

---

## References

- ADR [0001](./0001-source-format.md) — source format
- `docs/PROVENANCE.md` § Refresh cadence
- `docs/LAYERS.md` § Layer 1
- `tools/check_snapshot_freshness.py`
- `tools/refresh_diff.py`
- `.github/workflows/refresh.yml`
- ISO 10383 FAQ (publication cadence)

---

## Amendment (2026-10-10) — the `REMOVED > 0` guard did not fire

The `REMOVED > 0` guard was found **non-functional** on
2026-10-09 during the séance 3–4 coursework review (ADR
0011). The workflow piped `refresh_diff.py` through `tee`
and read `$?`, which is `tee`'s exit code, not the tool's.
On a synthetic removal of `XNYS`, `refresh_diff.py` exited 1
but the workflow's step printed `code=0`. The guard had
never fired.

The defect is fixed in the same commit. The workflow now
redirects both streams to the same file, captures the exit
code directly, and records it in `GITHUB_OUTPUT`.

The lesson is operator-hygiene rule 5 from
`RELEASE_PATTERN.md`: **the exit code of a pipeline is the
last command's exit.** A guard that does not fire is worse
than no guard, because this ADR claimed it did. The
reconnaissance that found it is ADR 0011.

---

## Amendment (2026-10-10) — the guard's mechanism is a draft PR

Decision 2 says a removal "fails the refresh pull request". It does
not, and the workflow never did: the diff step exits 0 and the PR
opens regardless (see the amendment above and ADR 0011). The
heading's "hard failure" is policy, not mechanism.

The mechanism, made explicit on 2026-10-10: when `refresh_diff.py`
exits 1, the PR opens as a **draft** whose body says `REMOVED > 0` and
requires human confirmation. A draft cannot be merged until a human
marks it ready for review, so the diff is visible and the merge is
blocked. The removed MICs are in the workflow log, not in the PR body.
The policy (D10) is unchanged; the claim is what changed.
