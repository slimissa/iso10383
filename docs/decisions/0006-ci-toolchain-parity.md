# 0006 — CI toolchain parity

**Status:** Accepted
**Date:** 2026-09-25
**Supersedes:** none
**Superseded by:** none

---

## Context

A release is verified by two gates: the local gate a maintainer runs
on their machine, and the CI gate that runs on a fresh runner. The two
gates must agree on what "verified" means. When they disagree, a
release that passes locally fails in CI, and the tag that was supposed
to name a verified state names an unverified one.

The v1.0.0 release failed CI three times for the same reason: a job's
`pip install` line did not list every Python import the job's scripts
performed. In each case the local gate passed, because the maintainer's
virtual environment had every package from `requirements-dev.txt`
already installed. The CI runner did not.

### The three failures

| Job | Command that failed | Missing package |
|-----|---------------------|-----------------|
| `check-wrappers (python)` | `python3 -m pytest wrappers/python/tests -q` | `pytest` |
| `check-cross-language` | `pytest` inside `check_cross_language.sh` | `pytest` |
| (one step away) `check-cli` | `python3 -m pytest tests/test_cli.py -q` | would have failed the same way if the earlier fix had not also covered it |

The root cause in every case: `wrappers/python/pyproject.toml` declares
the wrapper's runtime dependencies. It does **not** declare `pytest`,
because `pytest` is a development dependency listed in
`requirements-dev.txt`. CI jobs that run tests against the wrapper
need `pytest`, but the wrapper's own install line does not bring it in.

Locally this is invisible. The maintainer ran
`pip install -r requirements-dev.txt` once, and every subsequent test
worked. CI runs each job in a fresh container with no prior state.

---

## Decision

### 1. Every `pip install` line lists the complete import set

Each CI job that runs Python code installs every Python package that
code imports. Inheritance from `requirements-dev.txt` is not a
mechanism CI relies on. If a script imports `pytest`, the job's
install line names `pytest`. If it imports `jsonschema`, the install
line names `jsonschema`. If it imports `pyarrow`, the install line
names `pyarrow`.

The rule applies to:

- Direct imports in scripts the job runs.
- Indirect imports: if a script invokes `pytest`, and `pytest`
  imports plugins from a package the wrapper does not declare, that
  package is in the install line.
- Conditional imports that fire only in the CI environment.

### 2. The `check-cross-language` script is the canary

`tools/check_cross_language.sh` runs every wrapper's test suite. It is
the widest Python surface any job exercises. Whatever it imports, every
job that invokes it must install. The v1.0.0 failure of that job — after
the matrix fix had already been applied — proved that the fix was
applied to one job and not to the sibling.

The rule: **when a fix to a dependency gap lands in one job, grep the
workflow for every other job that runs the same command, and fix them
all in one commit.**

### 3. `pip install -e wrappers/python` is not a substitute for `pytest`

The wrapper's `pyproject.toml` declares `[project.dependencies]` — the
runtime dependencies. `pytest` is not among them, and adding it would
be wrong: a consumer who installs the wrapper does not need `pytest`.

The correct fix is that CI jobs running tests against the wrapper
install `pytest` alongside the wrapper:

```yaml
- run: pip install -e wrappers/python pytest
```

Not:

```yaml
- run: pip install -e wrappers/python
```

which leaves the job unable to run the test suite it is about to invoke.

### 4. A CI fix commit reruns every job

When a dependency gap is fixed in one job, the fix commit triggers a
full workflow run. The commit message names the fix and the job. Do not
push a fix and watch only the fixed job: the other jobs are the ones
that were not checked. The v1.0.0 release discovered the second gap
only after the first was fixed and CI reran.

### 5. A composite action is the escape hatch, not the default

A shared composite action that installs the superset of dependencies
would prevent the drift entirely. So would a shared `setup` job. Neither
is adopted in v1.0.1, for two reasons:

- Composite actions add a layer of indirection that makes a CI failure
  harder to diagnose. A job that installs its own dependencies has one
  place to look.
- The superset approach installs `pyarrow` in jobs that do not need it,
  which costs CI minutes.

If a third CI-only failure of the same class occurs in the next two
releases, the composite action is adopted. Until then, the rule is
"list every dependency in the job that uses it."

---

## Consequences

### For `.github/workflows/validate.yml`

Every job that runs Python code has an install line that names every
package the code imports. The three affected jobs:

```yaml
validate-json:
  - run: pip install jsonschema pyarrow pytest

check-cli:
  - run: pip install jsonschema pyarrow pytest

check-wrappers:  # the python matrix entry
  - run: pip install -e wrappers/python pytest

check-cross-language:
  - run: pip install -e wrappers/python pytest
```

`check-exports` installs only `pyarrow`, because that job runs only the
exporters and `sync_wrappers.py`, and those import only `pyarrow` and
the standard library.

### For `requirements-dev.txt`

Unchanged. It remains the list of everything a maintainer needs locally.
It is not consumed by CI. A maintainer reading the file to decide what a
CI job needs is reading the wrong file — that is what the ADR is
correcting.

### For `CONTRIBUTING.md`

A short section names the rule and points at this ADR. When a job's
dependencies change, the `pip install` line changes in the same commit
as the script.

### For a consumer reading the CI configuration

Each job is self-contained. A reader does not need to know what
`requirements-dev.txt` contains to know what a job installs. The
job's install line is the answer.

---

## Alternatives considered

**Have CI install `requirements-dev.txt` in every job.** Rejected.
`requirements-dev.txt` includes `pytest`, `pyarrow`, `jsonschema`, and
`requests`. `requests` is not needed by any workflow job. `pyarrow` is
needed by two jobs and not the others. Installing the superset costs
CI minutes and hides which packages each job actually needs.

**Have CI install `requirements-dev.txt` in a setup job whose artifact
every other job downloads.** Rejected for v1.0.1. See Rule 5.

**Add `pytest` to `wrappers/python/pyproject.toml`'s
`[project.dependencies]`.** Rejected. A consumer who installs the
wrapper does not need `pytest`. Declaring it as a runtime dependency
would ship it to every downstream user. The wrapper's
`[project.optional-dependencies].dev` group is where pytest belongs,
and CI jobs that run tests install that group:

```yaml
- run: pip install -e 'wrappers/python[dev]' pytest
```

This is a valid alternative that v1.0.1 does not adopt, because the
simpler form (`pip install -e wrappers/python pytest`) is sufficient
and easier to read. A future refactor may adopt the `[dev]` group.

**Do not run the CI-polled gate for release.** Rejected. See ADR 0005
Rule 5.

**Make the CI workflow tolerant of missing dependencies by skipping
tests whose packages are not installed.** Rejected. A test that skips
because a dependency is missing is a test that is not running. The
whole point of the gate is that the tests run.

**Treat CI as advisory and only the local gate as authoritative.**
Rejected. The local environment is one environment. A registry whose
contract is "any consumer in any language on any platform" cannot
verify that contract on one machine.

---

## Open questions

**What if a job needs a package only on Linux?** The install line
lists it. The workflow runs on `ubuntu-latest`. If a future workflow
adds a macOS or Windows runner, the install line becomes
platform-conditional in that job, not in a shared location.

**What if a Python package's install name differs from its import
name?** `pyarrow` installs and imports as `pyarrow`. `PyYAML` installs
as `PyYAML` and imports as `yaml`. The install line names the **install
name**, not the import name. The workflow's install lines use install
names.

**What if a job needs a minimum version?** Version constraints go in
the install line: `pip install "pyarrow>=14"`. The workflow pins
`ubuntu-latest`, so the default Python is 3.12 and the default
resolutions are recent. If a minimum matters, the constraint belongs
in the line.

**What if `requirements-dev.txt` and a job's install line drift?**
They are allowed to drift: the file is for maintainers, the line is
for CI. They are unified only if a future ADR adopts the composite
action.

---

## References

- ADR [0005](./0005-tag-discipline.md) — tag discipline and the CI poll
- `.github/workflows/validate.yml` — the workflow this ADR governs
- `requirements-dev.txt` — local-only dependency list
- `wrappers/python/pyproject.toml` — the wrapper's runtime dependencies
- v1.0.0 fix commits: `cbc0896`, `753cbbb`