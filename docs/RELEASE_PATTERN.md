# Release pattern

**Status:** Adopted — reviewed by ISO 3166 and Exchange Calendar.

The `release.sh` script exists in four registries. Each was written
independently. They share eight invariants and diverge on one step.
This document captures both.

- ISO 4217 (`scripts/release.sh`, two axes, eleven version sites)
- ISO 3166 (`scripts/release.sh`, one axis, eight version sites)
- Exchange Calendar (`scripts/release.sh`, three sites, two workflows)
- ISO 10383 (`scripts/release.sh`, nine version sites, one polled workflow)

---

## The essential eight

Every `release.sh` refuses on the same eight conditions, in this
order. The order matters: cheap checks first.

### 1. Refuse on unclean state

The working tree is clean, the current branch is `main`, and `HEAD`
matches `origin/main`. All three, or the release does not start.

The `HEAD` comparison must be against a freshly-fetched
`origin/main`. Without the fetch, a stale remote-tracking ref lets
the check pass locally while the remote has moved ahead.

Why: a release built from an uncommitted state is a release whose
contents can't be reproduced. A release from a non-`main` branch is a
release nobody else has. A release from a stale `main` is a release
that will conflict with the next push.

### 2. Refuse on version collision or missing CHANGELOG

`VERSION` differs from the target, and `CHANGELOG.md` has a
`## [<target>]` section. Both.

Why: the version collision check is a no-op guard against re-running
a release that already completed. The CHANGELOG check ensures the
release has a description before it has a tag.

### 3. Bump all version sites, then verify

Every site that carries the version is bumped. After the bumps, all
sites are re-read and compared. Any mismatch stops the release.

Why: a partial bump is worse than no bump. It ships a registry whose
own metadata disagrees with itself.

The site list is repo-specific. See `axes.json` for the ISO 4217
and ISO 3166 shapes.

### 4. Post-rebuild verify

Two shapes. Pick the one that matches your generator count.

**Single generator.** One artifact from one generator
(Exchange Calendar: `calendar.json` from `tools/build.py`).
`build → re-read → compare`. Three lines, immediate, points at
the build script if it fails.

**Multiple generators.** Nine artifacts from four generators
(ISO 4217, ISO 3166). `regenerate all → gate → consistency
check`. The gate centralizes the comparison. The failure message
names the stale artifact.

Rule: state which shape your repo uses, and why.

### 5. Gate before commit

Every check that CI runs also runs locally, before the release
commit is created. Any non-zero exit stops the release before
anything is committed or pushed.

Why: a release that fails CI is a release that needs a revert
commit. A release that fails the gate locally is a release that
was never created.

**The gate must include every check that runs in CI's fast
workflow.** A check that runs in CI but not in the gate is a check
that a release can bypass: the release commit lands on `main` with a
red CI before the tag is created. The v1.7.5 incident in ISO 4217 is
the reference case. Pytest was not in the gate; a stale test passed
locally and failed in CI. Fixed by adding `pytest tests/` to the
gate.

**The same rule covers the commands that produce what the release
commits.** A command that fails and isn't checked leaves stale
output. The ISO 3166 v1.6.9 snapshot generator ran without its
required `--source` argument; the shell continued; the release
carried the stale snapshot. Applies to artifact generators,
exporters, sync scripts, and any command whose output the release
commit includes.

**Gate block shape.** The gate block must be a per-check capture
(each check's exit read individually) or a subshell with `set -e`.
Never a bare brace group on the left of `||`.

A brace group's exit status is the last command's status. With `||`
on the right, `set -e` is disabled inside the group: every check
runs, and only the last gates. ISO 3166 v1.6.6 shipped a release
where the claims check failed but the gate reported pass, because
`pytest` ran last and succeeded.

Two valid shapes:

    # Per-check capture
    GATE_FAILED=0
    run_check() {
        if output=$("$@" 2>&1); then
            echo "ok: $1"
        else
            echo "FAIL: $1"; GATE_FAILED=1
        fi
    }
    run_check validate.py python3 tools/validate.py
    ...
    [ "$GATE_FAILED" -eq 0 ] || fail "gate failed"

    # Subshell with set -e
    (
        set -e
        python3 tools/check_version_consistency.py
        python3 tools/check_release_claims.py "$VERSION"
        ...
    ) > "$GATE_LOG" 2>&1 \
        || { tail -20 "$GATE_LOG"; fail "gate failed"; }

ISO 10383 uses the first shape: a `gate()` function that captures
each command's exit code, appends `"<rc>|<command>"` to `GATE_LOG`,
and exits on failure. Both shapes work. The brace group does not.

### 6. Poll every workflow

After the release commit is pushed, poll every workflow that runs
on push to the release branch. Wait for all of them to complete.
`in_progress`, `queued`, and `pending` are not green. Only
`completed success` is.

Schedule-driven workflows (`monitor`, `fetch`, `refresh`) are
deliberately excluded. The exclusion list is enumerated by hand
and must be checked against the workflows directory before every
release; a new per-push workflow added silently to the repo would
otherwise be missed.

In a repo with multiple per-push workflows, `gh run list` returns
multiple runs per SHA. Querying only the first (`head -1`) silently
misses the others. Query all runs for the SHA and assert every one
is `completed success`.

Reference implementation:

- ISO 4217, `scripts/release.sh` at commit `1f38fb4` — the
  `poll_ci` function reads every run for the SHA and asserts
  each reads `completed success`.
- ISO 3166, `scripts/release.sh` — same shape, adopted from
  ISO 4217's fix.
- The workflow-coverage check is `check_workflows_covered`,
  present in both scripts. It enumerates `.github/workflows/`,
  excludes schedule-driven files by name prefix, and fails if
  any remaining workflow isn't in the declared poll list.

Why: a tag that lands on a green commit whose second workflow is
still running is a tag that hides a failure. v1.3.0 in ISO 3166 is
the historical example.

**Reference implementation.** ISO 10383 `scripts/release.sh`
polls `gh run list --json databaseId,headSha,status,conclusion,
workflowName` for the release SHA, and asserts every run is both
`completed` and `success` before tagging. The failure message names
which workflow failed and its run ID.

The workflow-coverage check (`check_workflows_covered`) enumerates
`.github/workflows/*.yml`, filters schedule-driven workflows by name
prefix, and fails if any remaining workflow is not in the declared
poll list. It catches a new per-push workflow added without being
added to the declared list. ISO 10383 has one per-push workflow
today (`validate.yml`), so the check is trivially satisfied and not
yet implemented. The trigger is a second per-push workflow. The same
trigger applies on ISO 3166's side.

### 7. Tag only on green

The tag is created only after all polled workflows report
`completed success`. No manual override, no force. The tag message
is written to a file first, read back, then passed to `git tag -F`.

Why: this is the rule that the release process exists to enforce.
`CONTRIBUTING.md` says "don't tag on red"; the script says "you
cannot tag on red."

### 8. Immutable tags

**This is policy, not mechanism.** The script refuses to re-run on
an already-tagged version (invariant 7). Nothing in the code
prevents a manual `git tag -f`. The rule holds because operators
follow it, not because the tooling enforces it.

Once a tag is pushed, the code it points at is what shipped,
whether or not the CHANGELOG reflects it accurately.

Reconciliation of a tag that shipped with a known issue is a future
CHANGELOG entry acknowledging the divergence, not a force-push, not
a moved tag, not a rewritten release.

The tag is a claim about what shipped. The CHANGELOG is a claim
about what was known when. When they disagree, the CHANGELOG is
corrected and the tag is left alone.

---

## The `[Unreleased]` rule

`CHANGELOG.md` may carry an `[Unreleased]` section at the top at
release time. Nothing in the release path reads the first line of the
file, and nothing requires the target version's heading to be the
first heading. Presence, not position. Three consumers, each in
ISO 10383:

- `release.sh` refuses unless a line beginning `## [<version>]` exists
  anywhere in the file.
- The tag message is the body of the `## [<version>]` section, from
  that heading to the next `## [` heading, wherever it sits.
- `tools/check_version_consistency.py` skips the `[Unreleased]`
  heading when finding the top released version.

One position still counts: among dated version headings, the first
must equal `VERSION` before the release script bumps it. An
`[Unreleased]` section above it changes nothing.

ISO 10383 diverges from ISO 4217's copy in one respect: it does not
use staged headings. ISO 4217 names a fourth consumer that finds a
staged heading `## [<version>] — Unreleased` anywhere in the file and
rewrites it to the release date. ISO 10383 does not stage, so it does
not rewrite. The rule permits an `[Unreleased]` section; it does not
require one, and it does not require the rewrite.

---

## Two shapes of step 4

### Single generator

build
re-read the version from the artifact
compare to VERSION
text


Three lines. Immediate. The failure message names the file.

Exchange Calendar uses this shape: `tools/build.py` writes
`calendar.json`, then the script re-reads `meta.version` and
compares.

### Multiple generators

regenerate every artifact
run the gate (which includes a version-consistency check)
the check compares every artifact's version to VERSION

The gate centralizes the comparison. The failure message names
which artifact is stale, but the failure point is the gate, not
the rebuild step.

ISO 4217 and ISO 3166 use this shape: nine artifacts regenerate,
then `check_version_consistency.py` compares all of them.

### How to pick

If the repo has one generator, use the single-generator shape. It
catches the failure at the point of the failure.

If the repo has multiple generators, use the multi-generator
shape. An explicit re-read of each artifact is N blocks of
duplicated code; a centralized check is one.

State your choice in the release script's header comment.

---

## The wrapper-copy test question

When a wrapper bundles a copy of the registry file (Python wheel
ships `iso3166.json`, Go module vendors it, Rust crate includes
it), the release script must verify the bundled copy matches the
root. But whether that check is *primary* or *defense-in-depth*
depends on one thing:

**Do the wrapper tests read from the bundled copy or from the root
file?**

- If tests read the bundled copy, pytest is the primary guard. The
  release-step check is redundant but cheap; keep it as
  defense-in-depth.
- If tests read the root file, the release-step check is the sole
  local guard. CI's wrapper-sync check is the backstop.

Before adding the check, `grep` the test suite for the path it
loads. Case in Exchange Calendar: tests load the repo-root file,
so the release-step check is primary. Case in ISO 3166: tests load
the bundled copy, so the check is defense-in-depth.

The rule: verify which path the tests exercise before deciding the
check's role.

---

## Registry freshness vs. snapshot freshness

Two questions that look similar and aren't:

- **Registry freshness** — is my own source of truth current?
  Answered by comparing the registry's `meta.updated` against a
  threshold (typically 180 days).

- **Snapshot freshness** — are my vendored copies of other repos'
  sources current? Answered by checking each snapshot's
  `meta.review_by` against the current date.

Both share an exit-code contract (0 fresh, 1 stale, 2 fatal).
Their state designs differ: registry freshness is one date against
one threshold; snapshot freshness has three states (ISO date,
`closed`, `null`) because vendored sources can be static.

**Naming.** A tool named `check_snapshot_freshness.py` answers the
second question. If it is used to answer the first, the naming
collides with the purpose and a maintainer will look for the
registry's freshness check and not find it. The two questions
want two names.

**Reference implementation.** ISO 4217 has both as of v1.6.3:

- `tools/check_registry_freshness.py` — reads
  `iso4217.json → meta.updated`, 180-day threshold.
- `tools/check_snapshot_freshness.py` — adopted from ISO 3166
  v1.6.1. Globs `tools/*_snapshot.json`; reads `meta.review_by`
  from a sibling `<stem>.meta.json` when present, from the
  snapshot's own `meta` block when not.

Both run in CI, both run in the release gate. Neither supersedes
the other.

**When to add the registry check.** Any repo whose source of
truth is updated on a human cadence needs it. A repo whose source
of truth is updated by an automated pipeline that runs on every
push does not — the pipeline is the freshness guarantee. ISO
3166 is in the second category today; ISO 4217 is in the first.

### The monthly-cadence shape

ISO 10383 refreshes on a calendar: SWIFT publishes the MIC file
on the second Monday of each month. The registry's freshness check
uses a threshold of two missed publication cycles — 60 days — and
keys on `meta.source_snapshot`, the date the JSON's contents
reflect.

Neither ISO 4217 nor ISO 3166 refreshes on a calendar. Their
sources change on irregular amendment cycles, and their freshness
checks use 180-day thresholds keyed on `meta.updated`, the file's
last-modified date. The field name and the threshold are
repo-specific; only the pattern is shared.

**`meta.updated` vs `meta.source_snapshot`.** A registry whose
source of truth is a file the maintainers edit (ISO 4217's
`iso4217.json`, ISO 3166's `iso3166.json`) should key freshness on
`meta.updated`: the file's own last-modified date. A registry whose
source of truth is a publication it consumes (ISO 10383's
`iso10383.json`, derived from SWIFT's monthly file) should key on
`meta.source_snapshot`: the date the publication reflects. The two
can differ — a file can be edited (a bug fix, a formatting change)
without its upstream snapshot changing, and vice versa.

The pattern is: pick the field that answers "is the data stale?"
not "was the file touched?" For a maintained file, those coincide.
For a consumed publication, they do not.

*Contributed by ISO 10383. Ported to other registries' copies as
they adopt the monthly-refresh shape.*

## Tagged releases are immutable

Three rules, all consequences of the same principle.

**1. Never move a pushed tag.** A moved tag breaks anyone who has
already fetched. If v2.3.0 pointed at a commit whose polling fix
hadn't landed, the tag stays where it is. The fix is in the next
release.

**2. Never force-push over a tag.** Deleting and re-creating is the
same problem with an extra step. If the tag is wrong, the next
release corrects the record.

**3. The CHANGELOG acknowledges divergence.** When a tag shipped
with an issue that was discovered later, the next CHANGELOG's
`[Unreleased]` or the next release's section names the divergence
and points at the fix's commit. This is the reconciliation. It is
not a rewrite.

### The partial-release state

The script can produce one state it cannot resolve: the release
commit is pushed, `VERSION` is bumped, and the poll times out
before the tag is created. Re-running the script fails at
precondition (invariant 2: `VERSION` already at target).

Recovery is a manual `git tag -a vX.Y.Z -F /tmp/tag-message.txt`
on the pushed SHA, then `git push origin vX.Y.Z`. The tag message
is the same one the script would have written. Nothing else needs
to change.

This is the one state where a human must finish the release the
script started. Document it in the release script's header comment.

The state can also occur **after** the tag: the release is pushed,
CI passes, the tag lands, and a post-tag step (verification report,
artifact upload, notification) fails. The tag stays; the failing
step is completed manually; a follow-up commit closes the release.

ISO 3166 v1.6.2 is the reference example: the release ran through
step 6, step 7 failed on an undefined variable in the report
template, the tag stayed at the release commit, and the report was
written manually and committed forward. No force-push, no tag
move.

---

## The one exception: release-pipeline failure

If a tag was created on a commit that was red at the moment of
creation — because the release pipeline itself was broken, not
because the release content was wrong — moving the tag is a
recovery procedure, not a violation of rule 8.

The condition is narrow. The pipeline must have failed. The
release itself must be correct. The procedure must be documented
in the registry's own ADR with a Scope section limiting it to
this case.

ISO 10383's ADR 0005 is the reference implementation. Its scope
statement: the procedure applies only when the release pipeline
itself failed after the tag was pushed — a CI-polling defect, a
script that missed a workflow, a gate that ran the wrong
command. It does not apply to post-shipment discoveries (rule
8's CHANGELOG reconciliation) or to cosmetic corrections.

---

## Version-pinned byte outputs

Any build tool that produces a byte-comparable artifact must be
pinned to an exact version, not a range. A different version can
write different bytes for the same logical content.

Three registries hit this in sequence. ISO 3166 v1.6.8:
`pyarrow>=15.0` let CI install a different pyarrow from the one that
wrote the committed `iso3166.parquet`; CI's regeneration differed
byte for byte. Fixed with `pyarrow==25.0.1`. ISO 4217 v1.8.1: the
committed Parquet footers named pyarrow 25.0.1 while
`requirements-ci.txt` allowed `>=26,<27`; regenerating under 26.0.0
rewrote two bytes in each of the five files, the writer version in
the footer. ISO 4217's exporters' `--check` modes compared content,
not bytes, so they passed throughout; the verdict there was a sha256
comparison of regenerated against committed files. A `--check` that
compares bytes would have failed.

ISO 10383 closed the class at `268cbd8`. `constraints.txt` pins
`pyarrow==25.0.1`; `requirements-dev.txt` applies it with
`-c constraints.txt`; every CI job that installs pyarrow uses
`-c constraints.txt`; and `tools/export_parquet.py --check` compares
bytes, not schema metadata. A manifest claim prevents a bare
`pip install pyarrow` from reappearing in any workflow.

CSV and JSON are usually stable across versions. Anything binary or
with a structured footer (Parquet, Arrow, Avro, HDF5) is not. Pin
those.

**Corollary: pin the settings, not only the version.** Any tool that
produces a byte-comparable artifact must have all settings that
affect those bytes pinned in the tool itself. Serialization order,
encoding, and locale are settings, not incidental choices. If a
setting can differ between two runs of the same tool version,
`--check` will fail on a machine that made the other choice.

ISO 10383's instance: `tools/export_parquet.py` sorts the footer
metadata dict before writing (`dict(sorted(footer.items()))`), so
order is a property of the code, not Python's dict literal order.
The sort is asserted by a test that reads the file's footer keys
(`tests/test_export_parquet.py::test_metadata_keys_are_sorted`).

**Corollary: pin the render, not only the settings.** Any generator
whose output is a committed artifact must not read the clock, the
OS, or an unpinned dependency. A value from `date.today()`,
`os.getpid()`, or an unpinned library version can pass `--check`
only on the day (or machine) that generated the committed file. Pin
the render, or omit the varying field.

ISO 10383's instance: `tools/gen_iso3166_snapshot.py` and
`tools/gen_exchange_calendar_snapshot.py` read `source_version` from
their `.meta.json` sibling, clone or fetch the pinned tag, verify
that the source declares the same version, and write the snapshot.
Neither carries a `generated` field. Ten absence claims in
`tools/release_claims.json` (as of `268cbd8`) assert that
`date.today()`, `datetime.now()`, `time.time()`, `random.`, and
`uuid.uuid4()` are absent from both generators. One more
(`14fd705`) asserts that `scripts/release.sh` does not contain the
`&& info ` string, which is the shell short-circuit that swallows a
command's failure under `set -e`.

---

## Operator hygiene

Eight rules that emerged from specific failure modes across the
three implementations.

### 1. No heredocs for multi-line scripts

Inline Python or shell with quotes, braces, or shell
metacharacters will corrupt. Write the script to `/tmp/`, run it
standalone, check its exit code. Then proceed.

The failure mode: a heredoc silently absorbs the next shell
command into the file body. Happened in every release before the
rule.

### 2. `git diff` before every `git add`

If `git diff` is empty after an edit, the edit didn't land. The
commit will do nothing. The message describing the change will be
a lie.

The failure mode: a patch script that aborted at an anchor
mismatch, but the shell continued to the next command. The commit
message described a change that wasn't made.

### 3. Read every CI status before the next step

`in_progress`, `queued`, and `pending` are not green. Only
`completed success` is. Do not proceed past a CI check on any
other value.

The failure mode: a tag created while the second workflow was
still running. The tag landed on a commit that failed.

### 4. Any construct that requires the shell to parse structure goes into a file

The class is not "multi-line constructs." It is "any construct
that requires the shell to parse structure." A single-line
`bash -c "..."` with nested quoting fails the same way a pasted
multi-line loop does.

Heredocs, loops with function calls, `bash -c "..."`, Python via
stdin — all of them go into a file. Inline `python3 -c "..."`
for a one-liner is fine. The line is: does it need shell quoting
across more than one level?

Run the file. Check the exit code. Then proceed.

The failure mode: a `for` loop pasted into an interactive shell
that referenced functions defined inside a script. Twice.

### 5. The exit code of a pipeline is the last command's exit

`python3 tool.py | tail -3; echo $?` prints `tail`'s exit code,
not `tool.py`'s. `tail` always succeeds. The failure is invisible.

Redirect to a file, capture the exit code, then read the file:

python3 tool.py > /tmp/out 2>&1
echo "exit: $?"
tail -3 /tmp/out

The failure mode: a validator ran with a broken import, exited 1,
and the piped `tail -3` printed `0`. The release proceeded with
the validator broken.

Most checks that run in the gate also run in CI, so the gate is a
faster, local copy of the same signal. Some checks are gate-only by
design: their inputs are version-scoped in a way CI cannot
reproduce. `check_release_claims.py` is the reference case: the
manifest has claims about a version that does not exist until the
release commit lands. Gate-only checks are permitted; the tool's
docstring names the reason.

### 6. Every artifact that quotes an implementation detail is coupled to that implementation

When a script's expression changes, every test that asserts on it
and every doc line or claim that quotes it change in the same
commit. The failure mode is silent: the script works, the doc lies.

The ISO 10383 case: `\(.conclusion)` became
`\(.conclusion // \"pending\")` in a jq expression. The
release-claims manifest still asserted the old shape, and a test
still checked for it. Neither failed until the claim was verified
against the tree.

Applies to:

- CHANGELOG entries that quote command output
- Verification docs that paste captured results
- README sections that show example invocations
- Release-claims manifests that assert on script internals

The rule: if an artifact reproduces text from a running program,
that artifact is a copy, not a reference. Copies drift.

### 6b. The commit is not the working tree

`git diff --cached --stat` before every commit. The message is a
claim about what the commit contains, not about what's on disk. If
the diff doesn't match the message, the message is wrong.

Three instances:

- ISO 4217 `82668a0`: the commit's title was "Run stores-200 demo
  test in CI"; the diff carried only a trailing-whitespace change.
- ISO 4217 `3687bc2`: the commit's message described the orphan
  check landing; the diff only carried the call site. The function
  body followed two commits later.
- ISO 3166 v1.6.4: the CHANGELOG section named the ISO 10383
  reviewer entry and the orphan-preflight convention. Neither
  landed; a one-character anchor mismatch dropped both edits.

Both patches reported success. Neither diff matched its message.
The verification is `git diff --cached --stat` before every commit,
read against the intended change.

A `--stat` confirms which files changed, not what changed. When the
change is a specific line in a file — a step added, a claim updated,
a version bumped — read `git diff --cached` in full, not just the
stat. The stat catches a missing edit; the full diff catches the
wrong edit. The ISO 4217 v1.7.11 attempt is the reference case: the
patch that installed `duckdb` substituted a line inside a step
rather than replacing the step, producing an orphan `name:` in the
YAML. The stat named the workflow file; the diff would have named
the orphan.

### 6c. Manifest claims describe state, not intent

A claim in `release_claims.json` that asserts `file contains X` must
be verified against the file before the manifest is committed. If X
isn't there, the fix hasn't landed, not the claim.

Two failure classes:

- A claim describing a change that was intended but did not land.
- A claim whose string was edited to match the file, when the file
  was wrong.

Both turn the manifest into a check that always passes. The manifest
is a contract; a claim that describes intent instead of state is a
contract with nothing to enforce.

The `--audit` mode in `check_release_claims.py` runs every claim
against the current tree. Verify new claims before committing them.

### 6d. A check is only meaningful against the artifact it was designed for

The ISO 4217 v1.7.11 release had three checks return a clean result
against the wrong file, and the release was cut three times before
the placeholder in its verification doc was caught.

Three concrete instances, all in one session:

- `grep -c TODO` on the verification doc returned 0, because the
  doc contained a placeholder (`<the real line>`) that is not the
  string `TODO`.
- `grep -c "986 passed|test_stores_200"` on the same doc returned
  2, because the doc's own placeholder text contains both strings.
- `grep -c pytest` on a captured CI log returned 0, because the log
  was from the `Version and Hygiene` workflow, which does not run
  pytest. The `Validate Registry` workflow does.

A zero from a check pointed at the wrong file looks identical to a
zero from a check that correctly found nothing. The failure mode is
silent and it is the operator's responsibility to notice.

**The rule:**

- Record which artifact each check reads, in the check's own output.
  When a check produces a summary line, print the path or the run
  ID it was run against. `OK: 1 verification doc(s) clean` is
  weaker than `OK: 1 verification doc(s) clean under /repo/docs`.
  The second cannot be true if the check was pointed at the wrong
  place.
- When a check returns zero unexpectedly, first confirm the
  artifact is the one intended. Re-read the path or the command
  that produced it. A correct check against a wrong artifact is
  indistinguishable from a wrong check against the right artifact
  until you look.
- Never write a check whose passing state is supplied by the
  artifact's own template. A check on a doc that asks "does this
  contain X?" is a check that cannot fail if the doc's placeholder
  text contains X. Substituting a specific known-bad string for a
  general pattern is not a fix; it moves the failure to the next
  string.
- **A diagnostic check must parse with the same parser the consumer
  uses.** `grep` on structured data is not a check: it is a search
  over bytes that may not mean what the consumer reads. A value
  containing escaped characters — a JSON string whose value is a
  Python literal with a backslash, a Python literal with a newline
  escape — is stored in the file with one extra layer of escaping
  compared to the value the consumer reads. Grep for the file's
  bytes and you match the escaped form; grep for the consumer's
  value and you match nothing. Use `json.loads` + string
  comparison, or the equivalent parser, when the artifact is
  structured data.

This rule was added after ISO 4217 v1.7.11, and extended after
ISO 10383's v1.0.4 port when a `grep -F` on `release_claims.json`
returned two false negatives for two claims that were present in
the file. The check that closes the first class is
`tools/check_verification_doc.py`; the second class is closed by
using `json.loads` in place of `grep` for any diagnostic on a JSON
file. Sourced from ISO 4217 v1.7.11 and ISO 10383 v1.0.4.

### 7. A check that cannot run must fail, not pass

A built-in check that cannot execute — a missing toolchain, an
absent dependency, a network failure, a skipped test — is not a
pass. It is an unverified state, and the check must say so and exit
non-zero.

Four consequences:

- A missing prerequisite is a failure, reported by name. The
  prerequisite is checked before anything is changed, and also
  under `--dry-run`.
- An exception must be explicit and visible: a flag on the command
  line that appears in the output. Not a silent default, not an
  environment variable, not a `skipped` line that still exits 0.
- "Nothing ran" is never success, even when every part of the check
  was excused.
- A check that wraps other checks reports how many ran, not only
  how many passed.

Sourced from ISO 4217 v1.7.12 (`poll_ci` returned success when it
could not poll), v1.7.13 (`check_cross_language.sh` reported a
skipped suite as OK), v1.7.14 (skipped tests counted as passes in
the gate), and v1.7.15 (`check_amendments.py` exited 0 when it
could not read the SIX page, so the weekly monitor reported success
while detecting nothing). ISO 10383 closed its instance at `54d7f25`
(`check_cross_language.sh --strict` in the release gate) and
`62b2364` (`--strict` in `validate.yml`).

### 8. Every tool proves its own reachability

A tool with no `--check` or smoke invocation in CI may have
unreachable code paths. A generator did: its preservation block
crashed on every invocation and only appeared to work because the
snapshot's `review_by` was set manually.

Every tool that produces a committed artifact runs in CI, even on
unchanged inputs: a `--check` or smoke invocation in the fast
workflow and, under invariant 5, the same command in the release
gate. The check does not have to verify output; it has to make the
tool's code path execute. A `--check` that rebuilds with the same
function the write path calls, and compares, satisfies both: it
runs every branch and fails on an unreachable one.

Reference case: ISO 3166 `tools/gen_iso4217_snapshot.py` at
`07e103f`, the commit before `b9c0807`. Given a valid `--source` it
raised `NameError` (`output_path` was undefined), in write mode and
`--check` mode alike, and exited 1, the code `--check` uses for
"snapshot stale". The defects arrived in `da186b2`; `b9c0807` fixed
three: the undefined variable, a value assigned to a dict that was
discarded before the return value was built, and a stray import.

ISO 4217 had the same gap in v1.8.1: `tools/enrich_field.py
--check` ran in neither CI nor the gate, and the vendored ISO 3166
snapshot had no tool at all, so it was edited by hand and drifted
from every tag. v1.8.2 adds the four `enrich_field.py --check`
steps and `tools/vendor_iso3166.py --check`.

ISO 10383's two generator `--check`s (`gen_iso3166_snapshot.py`,
`gen_exchange_calendar_snapshot.py`) run in the `check-snapshots` CI
job and in the release gate, as of `8cf3357`.

Applies to: every tool with an output path in the repo, every
generator, every exporter. Sourced from ISO 3166 v1.6.9
(`94350d6`, `b9c0807`).

---

## The vendored-snapshot `review_by` shape

When registry A vendors a byte-for-byte snapshot of registry B, and
the snapshot-freshness check (see ISO 3166's `check_snapshot_
freshness.py`) needs a `review_by` field, the byte-for-byte property
collides with the metadata requirement. Adding `review_by` to the
vendored file breaks the property the snapshot exists for.

Three shapes:

**1. Separate metadata file.** `tools/<source>_snapshot.meta.json`
next to the snapshot, carrying `review_by` and `refresh_cadence`.
The check reads both files. The snapshot stays byte-for-byte.
Recommended: the cadence is a property of the vendoring, not of
the vendored.

**2. In-memory wrapper.** The snapshot is vendored into a wrapper
object at check time, with `review_by` injected. Byte-for-byte
preserved on disk; the wrapper exists only in memory.

**3. Documented exception.** Byte-for-byte applies to the source's
*data*, not its metadata block. Add `review_by` directly and note
in the ADR that the metadata block is not covered.

The recommendation is shape 1. If a registry ever ships a second
consumer of the same source, the metadata file travels
independently.

---

## Snapshot drift

When registry A vendors a snapshot of registry B, nothing on A's
side detects that B has released a newer version. Two legitimate
shapes:

**1. Freshness check per vendoring registry.** Each repo that
vendors a snapshot checks that the vendored version matches the
sibling's current release. Cheap when both repos have a
discoverable version; hard when they do not.

**2. Refresh-on-demand.** The vendoring repo refreshes when it
needs a specific upstream change. No automatic drift detection.

Shape 1 is right for registries that *depend on upstream
stability* (a foreign-key join against the source, for example).
Shape 2 is right for registries that just *consume the data* at
build time.

Both are legitimate. The choice depends on the relationship, not
on a rule. State which shape your repo uses and why.

---

## The mojibake self-trigger rule

Any pattern-based check will find its own explanation. The mojibake
scanner matches corrupted bytes; a docstring that shows the
corruption by example contains those bytes. `check_version_
consistency.py` would trip on a doc that embedded a mismatch
example. A future freshness check would trip on an expired date
shown as an example.

Two escapes, both valid:

1. Describe the corruption in prose. "The circumflexed o becomes
   four bytes when a file is decoded as Latin-1 and re-encoded as
   UTF-8" rather than embedding the corrupted string.
2. Mark the file with the check's skip marker. Reserved for test
   fixtures that deliberately contain the pattern.

A third example: `check_version_consistency.py` would trip on a
doc that embedded a mismatch string — a `VERSION == meta.version`
example shown as `1.5.3 == 1.5.2`. The doc must describe the
mismatch without printing it.

The general rule: state what the pattern matches, not the pattern
itself.

**Assertions on docstring content must normalize whitespace before
substring checks.** A line break is a formatting choice, not a
semantic one; a test that fails on a wrapped line will fail on the
next maintainer's reformat. The docstring assertions in
`tests/test_check_mojibake.py` normalize with `" ".join(doc.split())`
before the substring check, precisely because the docstring's line
wrapping is not part of its meaning.

**A diagnostic check must parse with the same parser the consumer
uses.** See operator-hygiene rule 6d for the full treatment; the
short form here is that grep on structured data is a search over
bytes that may not mean what the consumer reads. Use `json.loads` +
string comparison for any diagnostic on a JSON file.

### Implementation note

`tools/check_mojibake.py` scans the first 200 bytes of every file
for the literal string `# mojibake-scan: skip`. If present, the
file is not scanned. This is the second escape, implemented.

The first escape — prose description — is a documentation
discipline, not a mechanical rule. It applies to any pattern-
based check, not just mojibake.

---

## What this document does not cover

- Specific `release.sh` implementations. See the three repos.
- The eight version sites that ISO 4217 tracks, or the eleven that
  ISO 3166 tracks. See `axes.json` in each repo.
- The versioning policy (semver, what counts as major / minor /
  patch). See `CONTRIBUTING.md` in each repo.
- The snapshot-vendoring pattern for cross-registry checks. See
  the ISO 3166 README's "Consumed by" section and the Exchange
  Calendar ↔ ISO 3166 exchange.

---

## Review history

- 2026-09-27 — reviewed by ISO 10383 during their v1.0.2 preparation.
  Two corrections applied: the implementations list named ISO 10383
  as "planned" when it shipped at v1.0.0; the tag-immutability
  section gained an exception for tags created on a red commit
  by a pipeline defect. The exception cites ISO 10383's ADR 0005
  as the reference implementation.
- 2026-09-27 — reconciled against ISO 4217 v1.7.0. Adopted the
  additions ISO 3166 had not yet absorbed: the fifth
  operator-hygiene rule, the mojibake implementation note, and
  the registry-vs-snapshot subsection. Text-level differences
  reconciled in the same commit.

- 2026-09-27 — reviewed by ISO 4217. Two implementation divergences
  found in 4217's own `release.sh` (`head -1` on the poll list;
  missing `HEAD == origin/main` check). Doc unchanged; 4217's script
  fixes the divergences. Vendored-snapshot `review_by` shape
  discussed; recommendation adopted.
- 2026-09-27 — reviewed by Exchange Calendar. Invariant 8 clarified
  as policy, not mechanism. Partial-release recovery state added to
  the tag-immutability section. Operator hygiene rule sharpened
  from "multi-line construct" to "construct that requires shell
  parsing." Workflow poll list confirmed hardcoded; note added to
  invariant 6.

- 2026-09-28 — adopted into ISO 10383. No substantive changes to
  the pattern. ISO 10383 added to the reviewed-by list. The
  registry's own ADR 0005 gains a Scope section citing the
  tag-immutability exception documented above.

- 2026-10-01 — adopted Exchange Calendar's § Sources unreachable from
  CI. Two variants named: network-vantage blocking and
  client-fingerprint blocking. XKRX regression recorded as an expected
  event, not a failure. Contributed by Exchange Calendar.

Reviewed-by:
- `slimissa/iso4217`
- `slimissa/exchange-calendar`
- `slimissa/iso10383`

The document is stable. Future changes require a new review cycle.
