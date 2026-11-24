# 0013 — Sibling drift checks against release tags

**Status:** Accepted
**Date:** 2026-11-24
**Supersedes:** none
**Superseded by:** none

---

## Context

ISO 10383 vendors two sibling registries (README § 9, Layer 4):
`tools/iso3166_snapshot.json` from ISO 3166 and
`tools/exchange_calendar_snapshot.json` from Exchange Calendar. Each is
pinned to a tag in its `.meta.json`, and the generators fetch that tag,
never `main`. Two checks, `tools/check_iso3166_current.py` and
`tools/check_exchange_calendar_current.py`, compare the pinned snapshot
with the sibling. During v1.1.9 four problems showed up.

1. **The checks read the sibling's `main`, not a tag.** The ISO 3166
   check fetched `raw.githubusercontent.com/slimissa/iso3166/main/iso3166.json`;
   the Exchange Calendar check ran `git clone --depth 1` of the default
   branch. Unreleased work on a sibling's `main` could therefore turn
   this repository red, and both siblings have breaking schema changes
   on their roadmaps (ISO 3166 v2.0.0, Exchange Calendar 3.0.0). It
   happened on 2026-11-24: Exchange Calendar's `main` received
   `5010ff7 Revert "Release v2.34.0"` at 18:42 +0100, so `calendar.json`
   on `main` read 2.33.0 while the tag `v2.34.0` (`9d4bcb4`), the
   version v1.1.9 vendors, still existed. The release-gate form of the
   check, `--strict --fail-on-version-drift`, failed against `main`
   although nothing had been released upstream.

2. **A version-only sibling release blocks a release, and recovery was
   manual.** `scripts/release.sh` gates 7 and 8 (lines 249-250) pass
   `--fail-on-version-drift`. Exchange Calendar went from v2.28.0
   (2026-11-21 14:27 +0100) to v2.34.0 (2026-11-23 21:26 +0100), seven
   releases in three days, and ISO 3166 from v1.12.12 to v1.12.13 in
   eighty minutes on 2026-11-23. While v1.1.9 was being prepared, both
   siblings tagged again (v2.34.0, v1.12.13), so the snapshots
   re-vendored at v2.33.0 / v1.12.12 failed gates 7 and 8 before the
   release could run. Re-vendoring meant editing five fields in two
   places per sibling by hand, and it took a session.

3. **Content drift is found late.** `validate.yml` runs both checks only
   on push and pull request. Nothing scheduled runs them:
   `check-sources.yml` probes SWIFT only. A sibling that adds or removes
   a code or MIC leaves this repository's `main` silently stale until
   the next unrelated push, or the release. ADR 0007's amendment
   (2026-10-10) recorded the same failure once already: the drift was
   detected (`stale: 3 added, 3 removed`), but nothing acted on it, and
   "the drift was reported and ignored".

4. **An upstream format change reads as something else.** If a sibling
   changed its file layout at a tag, the checks either crashed or built
   an empty set and reported every local entry as "removed", that is,
   as a stale snapshot, instead of saying that the format had changed.

---

## Decision

### 1. Compare against the sibling's latest release tag, never `main`

"Latest" is the highest SemVer among the sibling's tags named exactly
`vX.Y.Z`, from `git ls-remote --tags`. Peeled entries (`^{}`) and any
tag that is not strict SemVer are ignored, and versions compare as
integer tuples (`v1.12.13` is above `v1.12.9`). One helper,
`tools/sibling_tags.py`, does this for both checks.

- ISO 3166: `iso3166.json` at
  `raw.githubusercontent.com/slimissa/iso3166/v<X.Y.Z>/iso3166.json`,
  the URL form `gen_iso3166_snapshot.py` uses.
- Exchange Calendar: `git clone --depth 1 --branch v<X.Y.Z>`, the form
  `gen_exchange_calendar_snapshot.py` uses.

The upstream version is the tag's version, cross-checked against the
file's `meta.version` (`iso3166.json`, or `calendar.json` for Exchange
Calendar). If they disagree, the check fails and names both. Each run
prints `upstream version: vX.Y.Z (latest release tag of <repo>)`.

### 2. Exit semantics are unchanged, plus one new failure

- A content difference (the alpha-2 set or the MIC set) fails under
  `--strict`.
- Version drift is a warning (`warning: version drift: snapshot
  source_version ...`) and fails only with `--fail-on-version-drift`.
- An unreachable sibling fails unless `--advisory` (RELEASE_PATTERN,
  operator-hygiene rule 7).
- **New:** a file at the tag that the check cannot read (a missing file
  or key, or a set that comes out empty) fails with `upstream format
  changed at vX.Y.Z: <what is missing>`. It is never reported as stale
  and never passes, even with `--advisory`: the sibling was reached, so
  rule 7's tolerance does not apply. A sibling with no release tag at
  all fails the same way (`no release tag matching ...`).

### 3. `tools/revendor.py`: re-vendoring is one command

```
python3 tools/revendor.py {iso3166|exchange_calendar|all} [--to X.Y.Z | --latest] [--date YYYY-MM-DD] [--check]
```

It resolves the target version (decision 1), sets `source_version`, runs
the existing generator's own fetch, build and render, recomputes
`upstream_sha256` from the tag as README § 9 states, and writes
`snapshot_sha256`, `vendored_from`, `vendored_at` (default today in
UTC) and `meta.review_by` (`vendored_at` + 1 cadence period, from
`tools/cadence.py`, the helper `tests/test_snapshot_meta.py` also
uses). `source`, `source_version` and `vendored_at` are written equal at
the top level and in `meta`. It writes nothing else; the CHANGELOG, the
release claims and the release stay human steps, and it prints that
reminder. `--check` writes nothing and exits 1 if a re-vendor would
change anything. `make revendor SIBLING=all` runs it; it is not part of
`make package` or `make test`.

### 4. `check-siblings.yml`: weekly detection

A scheduled workflow, every Monday at 06:30 UTC (after
`check-sources.yml` at 06:00) and on manual dispatch, runs both checks
with `--strict` and without `--fail-on-version-drift`. When one fails
it opens an issue titled `Sibling drift: <sibling>`, or comments on the
one already open, with the check's output and the run URL, following
`check-sources.yml`. Permissions are `contents: read` and
`issues: write`. It has no `push` or `pull_request` trigger:
`release.sh` polls the per-push workflows for the release SHA and is
written for exactly one (`validate.yml`; header lines 38-39, poll lines
320-324). A push trigger would first need ISO 4217's
`check_workflows_covered`, which is out of scope here.
`tests/test_check_siblings_workflow.py` pins the triggers, the
permissions and that single per-push workflow.

---

## Not decided here

**Version drift stays a release blocker.** `docs/RELEASE_PATTERN.md` §
"Version drift on push vs. on release" says a release gate requires
version drift to be zero, and that section is shared and
cross-reviewed (ISO 4217, Exchange Calendar, ISO 10383). This ADR does
not change it, and `release.sh` keeps `--fail-on-version-drift` in
gates 7 and 8. What this ADR changes is the cost of meeting the rule:
`revendor.py` makes recovery one command. A proposal to treat a
version-only lag as information rather than a blocker (qlf-sentinel's
S3) goes through a RELEASE_PATTERN review cycle, not through this ADR.

---

## Consequences

- Unreleased work on a sibling's `main`, including a reverted release,
  no longer reaches this repository's CI. The 2026-11-24 revert is the
  test case: `tests/test_sibling_tags.py` has a fake sibling whose
  `main` is behind its latest tag, and the check passes against the
  tag.
- A sibling release now shows up in CI (and in the weekly issue for a
  set change) only once it is tagged. A sibling that pushes data to
  `main` and never tags is invisible until it does; that is intended.
- A tag deleted upstream changes what "latest" means. If the tag this
  repository vendors is deleted, the latest tag is older than the
  snapshot and the checks report version drift; `revendor.py --to`
  re-pins explicitly.
- Two behaviours changed with the format rule. The ISO 3166 check used
  to print `note: upstream declares no meta.version; version not
  compared` and go on; the Exchange Calendar check used to fall back to
  the sibling's `VERSION` file when `calendar.json` had no version. Both
  now fail as a format change, because the tag cannot be cross-checked
  without the file's version.
- There are now three scheduled workflows (`refresh.yml`,
  `check-sources.yml`, `check-siblings.yml`) and one per-push workflow.
  ADR 0010's amendment (2026-11-08) counts two scheduled workflows "since
  v1.1.0"; that sentence is historical and is not rewritten.
- `release.sh`'s poll selects every run whose head SHA is the release
  commit, whatever triggered it. A scheduled run of `check-sources.yml`
  or `check-siblings.yml` that starts on the release commit during the
  poll window is counted too. That was already true of
  `check-sources.yml`; this ADR does not change the poll.
- The weekly check needs the network and GitHub's issue API, as
  `check-sources.yml` does. A run that cannot reach a sibling fails and
  opens an issue (no `--advisory`), because a check that could not run
  is not a pass.

---

## Alternatives considered

**Keep reading `main`, and tolerate drift on push.** Rejected. It is
the current behaviour and the cause of problem 1: a sibling's
unreleased or reverted work decides whether this repository is green.

**Read the tag that the snapshot pins, not the latest one.** Rejected.
That is what `gen_*_snapshot.py --check` already does (gates 16 and 17):
it proves the snapshot reproduces from its own tag. The drift checks
exist to say whether the sibling has moved since; comparing with the
pinned tag would always say no.

**Treat a version-only lag as information, not a release blocker.**
Not decided here; see "Not decided here".

**Add a push trigger to the weekly workflow.** Rejected for now. The
release poll is written for one per-push workflow, and
`check_workflows_covered` is not ported.

**Re-vendor automatically in the scheduled workflow and open a pull
request.** Rejected for now. A re-vendor needs a CHANGELOG entry and
release claims that a human writes, and the weekly workflow has
`contents: read` only. The issue names the one command to run.

---

## Reopening triggers

Any of:

1. A sibling ships its planned breaking change (ISO 3166 v2.0.0,
   Exchange Calendar 3.0.0). The checks will fail with `upstream format
   changed at ...`; the readers in both checks, and the generators,
   need updating together.
2. A RELEASE_PATTERN review cycle changes § "Version drift on push vs.
   on release". Decision 2 and `release.sh` gates 7 and 8 follow it.
3. A second per-push workflow is added, or `check_workflows_covered` is
   ported. Then `check-siblings.yml` may take a push trigger.
4. A sibling adopts tags that are not `vX.Y.Z` (pre-release tags, a
   different prefix) for real releases. `tools/sibling_tags.py` ignores
   them today.

---

## References

- `tools/sibling_tags.py`, `tools/check_iso3166_current.py`,
  `tools/check_exchange_calendar_current.py`, `tools/revendor.py`,
  `tools/cadence.py`
- `.github/workflows/check-siblings.yml`,
  `.github/workflows/check-sources.yml`
- `tests/test_sibling_tags.py`, `tests/test_revendor.py`,
  `tests/test_check_siblings_workflow.py`, `tests/test_checks.py`
- `scripts/release.sh` (gates 7 and 8; poll scope)
- `docs/RELEASE_PATTERN.md` § "Version drift on push vs. on release"
- [ADR 0007](./0007-cross-registry-allowlist.md), Amendment (2026-10-10)
- [ADR 0010](./0010-platform-charter.md), Amendment (2026-11-08)
- README § 9 (vendored snapshots, the two hashes) and § 14 (CI)
