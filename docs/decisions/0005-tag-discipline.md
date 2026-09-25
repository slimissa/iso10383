# 0005 — Tag discipline

**Status:** Accepted
**Date:** 2026-09-25
**Supersedes:** none
**Superseded by:** none

---

## Context

A release is a tag on a commit. The tag has one job: to name the exact
state of the repository that passed every gate, so that a consumer who
checks out the tag gets the state that was verified.

The v1.0.0 release discovered three ways a tag can fail to do that job:

1. **The tag was created before CI finished.** The first `v1.0.0` tag
   was placed on the release commit (`680884d`) before the GitHub
   Actions run on that commit had reached a conclusion. CI failed.
   The tag had to be moved to the commit where CI actually passed.

2. **The verification document recorded the wrong SHA.** An annotated
   tag is itself a Git object with its own hash. That hash differs from
   the hash of the commit the tag points to. The v1.0.0 verification
   document recorded `737ac097…` — the tag object — where a consumer
   reading it would `git checkout 737ac097` and land on a detached
   tag object, not on a commit.

3. **The verification document was written before the tag was created.**
   The `release.sh` verification-doc step used `git rev-parse HEAD`,
   which is the commit that HEAD pointed at when the doc was written.
   On a clean release, that is the release commit — but the tag had
   not been created yet, and CI had not been verified. The doc
   asserted a state that was not yet known to be good.

The ADR fixes all three with one rule and one procedure.

---

## Decision

### 1. The tag names the commit CI verified green

A release tag is created **only after** the CI run on the pushed
commit reaches `completed success`. A tag on a red commit is not a
release; it is a wrong assertion about a commit.

The commit the tag points at is the commit that satisfied:
- Every local gate (`tools/validate.py`, `check_version_consistency.py`,
  `check_snapshot_freshness.py`, three `export_*.py --check`,
  `sync_wrappers.py --check`, `pytest tests/`, `check_cross_language.sh`).
- Every CI job in the `validate` workflow, on the pushed commit.

No exception for "the fix is obvious". If CI is red, the tag waits.

### 2. The verification document records both SHAs

An annotated tag `vX.Y.Z` has two relevant SHAs:

| SHA | Command | Meaning |
|-----|---------|---------|
| Tag object SHA | `git rev-parse vX.Y.Z` | The tag's own hash |
| Commit SHA | `git rev-parse vX.Y.Z^{commit}` | The commit the tag points to |

The verification document records both, on separate lines:

```
Commit:     <commit SHA>          # what a consumer checks out
Tag object: <tag object SHA>      # what identifies the tag
```

A consumer checking out a release uses the **commit SHA**. A consumer
verifying tag integrity uses the **tag object SHA** and its signature.
They are two different identifiers for two different purposes.

### 3. The verification document is written after the tag is created

`release.sh` writes the verification document as the last step, after
the tag exists. It reads both SHAs from the tag, not from `HEAD`:

```bash
echo "Commit:     $(git rev-parse "v$VERSION^{commit}")"
echo "Tag object: $(git rev-parse "v$VERSION")"
```

This guarantees the doc names the tagged commit, not a commit that
happens to be at HEAD when the doc is written.

### 4. Moving a tag is a documented procedure

Tags must move when the wrong commit was tagged. This happens for
three reasons:

- The tag was created before CI had finished.
- CI failed on the tagged commit and a fix commit followed.
- A release was cut against the wrong CHANGELOG section.

The procedure, in this exact order:

```bash
# 1. Delete the tag locally
git tag -d vX.Y.Z

# 2. Delete the tag on the remote
git push origin :refs/tags/vX.Y.Z

# 3. Recreate the tag on the correct commit
TAG_MSG=$(python3 - <<'PY'
import re
text = open("CHANGELOG.md", encoding="utf-8").read()
m = re.search(r"## \[X\.Y\.Z\][^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
print((m.group(1).strip() if m else "")[:4000])
PY
)
git tag -a vX.Y.Z -m "Release vX.Y.Z

$TAG_MSG"

# 4. Push the new tag
git push origin vX.Y.Z

# 5. Verify with the ^{commit} suffix, never without it
git rev-parse vX.Y.Z^{commit}
git log -1 --format='%h %s' vX.Y.Z^{commit}
```

Remote first, then local. Deleting the local tag first, then failing
partway through the remote delete, leaves the repository in an
inconsistent state that is harder to reason about than a redundant
retry.

### 5. The release script polls CI, and the poll is not advisory

`scripts/release.sh` polls `gh run list` for the pushed commit until
the run reaches a terminal state:

- `completed success` → continue to the tag step.
- `completed failure` → exit 1. The tag is not created.
- The loop exhausts without a terminal state → exit 1. The tag is not
  created.

A loop that prints the status and continues regardless is not a gate.
It is a decoration. The v1.0.0 script shipped with a jq escaping bug
that turned the polling output into a literal string; the loop ran 60
times and then fell through to the tag step with the CI state unknown.
That bug is fixed. The fix is covered by ADR 0006's companion rule:
a release script's guarantees are only as good as its enforcement.

---

## The v1.0.0 incident, in full

Recorded here so the next maintainer does not repeat it.

### What happened

1. `scripts/release.sh 1.0.0` ran, passed every gate, committed
   `680884d`, pushed, and reached the CI-polling step.
2. The polling step's jq expression was `"\\(.status) \\(.conclusion)"`.
   jq read `\\(` as an escaped backslash followed by literal text. The
   loop printed `\(.status) \(.conclusion)` sixty times and then fell
   through.
3. The script continued to the tag step and created `v1.0.0` on
   `680884d` without waiting for CI.
4. CI failed on `680884d`. The `check-wrappers (python)` matrix job
   could not run `pytest` — it was not installed.
5. The tag was moved manually after two follow-up commits
   (`cbc0896`, `753cbbb`) made CI green. It now points at `753cbbb`.

### What the ADR would have prevented

- **The 60-line fall-through.** Rule 5 requires the poll loop to exit
  on unknown status, not fall through.
- **The wrong verification-doc SHA.** Rule 2 separates the commit SHA
  from the tag object SHA.
- **The tag on a red commit.** Rule 1 forbids it.

### What it does not prevent

A downstream consumer that checked out `737ac097` between the v1.0.0
tag creation and the ADR being written has a detached tag object. That
is a one-off. Future releases are protected by Rule 2.

---

## Consequences

### For `scripts/release.sh`

Three changes:

1. The CI-polling loop exits 1 on any status other than
   `completed success`, including loop exhaustion.
2. The verification-doc writer reads `git rev-parse "v$VERSION^{commit}"`
   and `git rev-parse "v$VERSION"`, not `git rev-parse HEAD`.
3. The verification doc template gains a `Tag object:` line.

### For `docs/vX.Y.Z-verification.md`

Every future verification document has the two-SHA shape. The v1.0.0
document is retroactively corrected (see the correction block at the
end of that file).

### For the wrapper packages

None. The wrapper versions track the registry version (D16), which is
the version string, not a commit SHA. The commit SHA appears only in
the verification document.

### For consumers

A consumer that pins a release by commit SHA reads the verification
document and uses the `Commit:` line. A consumer that pins by tag name
uses the tag. Both resolve to the same commit, provided the tag was
created per Rule 1.

---

## Alternatives considered

**Tag before CI, and move the tag if CI fails.** Rejected. This is
what v1.0.0 did. It produces a tag that lies about which commit was
verified. Moving a tag is expensive: a force-push to a tag ref, a
rebuild of any downstream cache keyed on the tag, and a public
correction. Waiting for CI is free by comparison.

**Do not create a verification document.** Rejected. The document
records which commit was verified and when. Without it, a consumer has
to infer the verified commit from the tag, the CI status, and the
commit log — three sources that can disagree.

**Record only the tag object SHA.** Rejected. `git checkout <tag>`
with an annotated tag checks out the commit, not the tag object. The
commit SHA is what a consumer needs.

**Record only the commit SHA.** Rejected. The tag object SHA is what
identifies the tag in a `git ls-remote` listing and what a signed tag
signature covers. It belongs in the document for a different reader.

**Trust the local gate and skip the CI gate.** Rejected. The v1.0.0
release passed every local gate and failed CI three times. The local
environment had `pytest` installed; the CI runner did not. A release
gate that only tests one environment is not a gate. See ADR 0006.

**Automate the tag move.** Rejected. A tag move is an exceptional
event. Automating it invites silent moves, which is worse than manual
moves that a human reads. The procedure above is manual and documented.

---

## Open questions

**What if CI is flaky?** A flaky CI run is not `completed success`. The
release waits. If the flake is persistent, it is a bug in the CI
workflow, and it is fixed before the release, not worked around.

**What if a release is aborted after the tag step but before the
verification doc?** The tag exists; the doc does not. Rerun the doc
step manually and commit. Do not delete and recreate the tag — the tag
was correct, the doc is just missing.

**What if a security fix must ship without waiting for a full CI run?**
The release ships with the full CI run. A security fix that cannot
wait for CI is a security incident, not a release, and is handled
under a different procedure that does not create a normal release tag.

---

## v1.0.1 addendum

The tag-discipline procedure worked as designed for v1.0.1. The
release script's CI-polling loop reported the actual run status,
refused to tag on a red commit, and created `v1.0.1` on the commit
whose run reached `completed success`. The verification doc records
both the commit SHA and the annotated tag object SHA.

The v1.0.0 incident remains the only tag move in the registry's
history.

---

## References

- ADR [0001](./0001-source-format.md) — the source format
- ADR [0006](./0006-ci-toolchain-parity.md) — CI environment parity
- `scripts/release.sh` — the release pipeline
- `docs/v1.0.0-verification.md` — the corrected v1.0.0 verification
- `docs/decisions/v1.0.0-decisions.md` D12 — release.sh ported before
  v1.0.0