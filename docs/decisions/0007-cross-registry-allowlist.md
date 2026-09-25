# 0007 — Cross-registry allowlist

**Status:** Accepted
**Date:** 2026-09-25
**Supersedes:** none
**Superseded by:** none

---

## Context

ISO 10383 cross-references two sibling registries via committed
snapshots:

- `tools/iso3166_snapshot.json` — 252 ISO 3166-1 alpha-2 country codes.
  Every `country_code` in `iso10383.json` must exist in this set, with
  one exception: `ZZ`, ISO 10383's placeholder for "no fixed country",
  which is not an ISO 3166 code.
- `tools/exchange_calendar_snapshot.json` — 74 MICs referenced by the
  Exchange Calendar registry. Every MIC in this set must exist in
  `iso10383.json`.

D6 said cross-registry validation is **advisory in v1.0.0, blocking in
v1.0.1**. The v1.0.0 validator prints cross-registry mismatches to
stderr and exits 0. That is the advisory behavior.

The v1.0.1 promotion to blocking was expected to be a one-line change.
It is not, because three MICs referenced by Exchange Calendar do not
appear in the SWIFT-published file:

| MIC | Venue | Status |
|-----|-------|--------|
| `XBEK` | Beirut Stock Exchange | Referenced by Exchange Calendar |
| `XNBO` | Nairobi Securities Exchange | Referenced by Exchange Calendar |
| `XQSE` | Qatar Exchange | Referenced by Exchange Calendar |

The investigation:

- The three are not in the 2026-09-23 SWIFT file. Verified by grep on
  the raw CSV.
- They are not in the ISO 10383 registry at any prior version this
  project has access to.
- They *are* in Exchange Calendar's `exchanges/` directory. That
  directory was written before ISO 10383 was published, using MICs
  that the SWIFT file either never assigned or has since removed.

Resolving the gap requires one of:

1. Editing `slimissa/exchange-calendar` to remove the three MICs (or
   replace them with the correct MICs, if the venues have since
   received different assignments).
2. SWIFT assigning the three MICs in a future publication and the
   next monthly refresh picking them up.
3. An exception in the validator.

Option 1 is out of scope for ISO 10383 v1.0.1: this repository does
not touch sibling repositories. Option 2 has no schedule. Option 3 is
the only one available to v1.0.1.

---

## Decision

### 1. The validator distinguishes expected gaps from unexpected ones

Cross-registry validation is promoted to blocking in v1.0.1, but with
an explicit allowlist. Any MIC referenced by Exchange Calendar that is
absent from `iso10383.json` is classified:

- **Expected gap** — in the allowlist. Reported as a warning. Does not
  fail the validator.
- **Unexpected gap** — not in the allowlist. Reported as an error.
  Fails the validator.

The distinction is the whole point. A cross-registry check that treats
every gap as fatal cannot be promoted to blocking until every gap is
resolved. A check that treats every gap as advisory is not blocking.
The allowlist is the mechanism that lets a blocking check tolerate a
known, documented gap without hiding the gap.

### 2. The allowlist is a `frozenset` in `tools/validate.py`

```python
# MICs referenced by a sibling registry that are known to be absent
# from SWIFT's published file. Adding to this set requires an ADR
# amendment. See docs/decisions/0007-cross-registry-allowlist.md.
KNOWN_EXCHANGE_CALENDAR_GAPS = frozenset({
    "XBEK",  # Beirut Stock Exchange
    "XNBO",  # Nairobi Securities Exchange
    "XQSE",  # Qatar Exchange
})
```

A `frozenset` because it is iterated, never mutated at runtime, and the
type makes that clear. A `dict` would invite storing reasons inline,
which invites the list to grow without the accompanying ADR.

### 3. Adding a MIC to the allowlist requires an ADR amendment

The rule is not "the allowlist can grow whenever a gap appears." It is
"every entry in the allowlist is named in this ADR, with its venue and
its reason." Adding a fourth MIC requires:

1. An investigation that names the venue and the discrepancy.
2. A commit that adds the MIC to the allowlist **and** adds a row to
   the table in this ADR.
3. A note in `docs/PROVENANCE.md` § Known cross-registry gap.

A commit that adds to the allowlist without touching this ADR is
refused. The exception is the record of a decision; the ADR is where
the decision lives.

### 4. Removing a MIC from the allowlist is the preferred direction

The allowlist should shrink, not grow. A MIC leaves the allowlist when:

- Exchange Calendar removes it (option 1 above), or
- SWIFT assigns it (option 2 above).

Either is a good outcome. The first is a one-line change in a sibling
repository; the second is a monthly refresh that resolves it
automatically. Neither requires an amendment to *this* ADR, but both
require a commit that removes the MIC and updates the table.

### 5. The `ZZ` country code is not in the allowlist

`ZZ` is ISO 10383's placeholder for "no fixed country." It appears in
the source file three times, on MICs whose operator has no fixed
national location. It is not a malformed country code; it is the
source's way of saying "none."

`ZZ` is handled separately from the Exchange Calendar allowlist,
because it is a *value the source uses*, not *a gap between two
registries*. The validator's ISO 3166 check excludes `ZZ` explicitly:

```python
if country == "ZZ":
    continue  # ISO 10383's placeholder for "no fixed country"
```

This is not a policy decision that warrants an ADR amendment. It is a
fact about the source file, recorded in `docs/source_format.md`.

---

## Consequences

### For `tools/validate.py`

Two changes:

1. The `KNOWN_EXCHANGE_CALENDAR_GAPS` frozenset is defined at module
   level, with the comment above.
2. The cross-reference layer splits the missing MICs into two lists:
   expected (in the allowlist) and unexpected (everything else). The
   expected list produces warnings; the unexpected list produces
   errors.

### For the default behavior

`tools/validate.py` runs cross-registry checks as **blocking by
default** in v1.0.1. The v1.0.0 default was advisory. The change is:

```bash
python3 tools/validate.py                  # exit 0 in v1.0.0
                                           # exit 0 in v1.0.1 if every gap is allowlisted
                                           # exit 1 in v1.0.1 if any gap is unexpected
```

An `--advisory` flag restores the v1.0.0 behavior for consumers who
need it:

```bash
python3 tools/validate.py --advisory        # exit 0 regardless of gaps
```

### For the CI workflow

The `validate-json` job runs `tools/validate.py` with default behavior
(blocking). A run that produces an unexpected gap fails. A run that
produces only allowlisted gaps passes with a warning.

### For `docs/PROVENANCE.md`

The `### Known cross-registry gap` section names the three MICs, points
at this ADR, and states that the allowlist is the mechanism. It does
not enumerate the allowlist separately; the ADR is the source of
truth.

### For `CONTRIBUTING.md`

A paragraph names the allowlist, states the rule for adding to it, and
points at this ADR. The paragraph is short: the ADR carries the detail.

### For a consumer reading `iso10383.json`

Nothing changes. The three MICs are not in the registry. The allowlist
does not add them; it records that their absence is known and
tolerated. A consumer that checks every MIC it uses against the
registry will still fail for `XBEK`, `XNBO`, or `XQSE`.

That is the correct behavior. The registry is honest about the gap.

---

## Alternatives considered

**Keep cross-registry advisory indefinitely.** Rejected by D6. The
point of committing a sibling snapshot is that the check runs. A check
that never fails is not a check.

**Resolve the gaps by editing Exchange Calendar.** Rejected. This
repository does not touch sibling repositories. Whether `XBEK`,
`XNBO`, and `XQSE` are correct MICs for their venues is a question for
the Exchange Calendar maintainers, who may have their own reasons for
keeping them.

**Remove the three MICs from Exchange Calendar unconditionally.**
Rejected for the same reason. Not this repository's decision.

**Add the three MICs to `iso10383.json` from a non-SWIFT source.**
Rejected absolutely. The registry's value is that every entry traces
to SWIFT's file. Adding a MIC from a press release or a Wikipedia
article breaks that chain and would make the registry unauditable.
ADR 0001 forbids it.

**Promote cross-registry to blocking only for ISO 3166, not for
Exchange Calendar.** Rejected. The bidirectional check is the more
valuable one: MIC is the join key, and the join key is where drift
appears. Keeping the ISO 3166 check blocking and the MIC check advisory
inverts the priorities.

**Have the allowlist live in a JSON file rather than in the code.**
Rejected. A JSON allowlist is a data file that CI reads and that a
contributor can edit without touching the ADR. A Python `frozenset` is
a code change, and code changes are reviewed. The friction is
intentional.

**Make the allowlist a warning with no ADR required to grow.**
Rejected. An allowlist that grows silently is a blacklist. The ADR
amendment is what distinguishes "known gap" from "convenient
exclusion."

---

## Open questions

**What if SWIFT assigns one of the three MICs next month?** The
monthly refresh picks it up. The MIC leaves the allowlist in the same
PR: the fetch adds it to `iso10383.json`, and a follow-up commit
removes it from `KNOWN_EXCHANGE_CALENDAR_GAPS` and from the table in
this ADR. The two changes ship in one release.

**What if Exchange Calendar adds a fourth MIC not in SWIFT's file?**
The validator fails on the next run. The failure names the MIC. The
maintainer investigates: is it a real MIC SWIFT has not published, or
a typo in Exchange Calendar? If real and not in SWIFT's file, an ADR
amendment adds it to the allowlist. If a typo, Exchange Calendar is
notified. The default is failure, not tolerance.

**What if the allowlist ever grows past five or six entries?** The
allowlist is a symptom of drift between two registries. If it grows
past six, the correct response is not more allowlist entries. It is a
review of the relationship between the two registries: is Exchange
Calendar's MIC set actually a subset of ISO 10383's? If not, the
cross-registry check is comparing incompatible things, and the check
itself needs to change.

**What if the ISO 3166 snapshot gains a similar gap?** The mechanism
generalizes. A `KNOWN_ISO3166_GAPS` frozenset would be added the same
way. No ISO 3166 gap exists today; the mechanism is documented here
for the case where one appears.

---

## References

- ADR [0001](./0001-source-format.md) — the source format, and why
  every entry traces to SWIFT's file
- `docs/decisions/v1.0.0-decisions.md` D6 — cross-registry validation
  via committed snapshots
- `docs/decisions/v1.0.0-decisions.md` D17 — cross-registry gaps are
  explicitly allowlisted
- `docs/PROVENANCE.md` § Known cross-registry gap
- `docs/LAYERS.md` § Layer 4 — the cross-referenced layer
- `tools/validate.py` — the validator and the allowlist