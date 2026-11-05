# Enrichment: why some fields are null

Seven fields in the registry are null for many entries: `acronym`,
`legal_entity_name`, `note`, `website`, `last_validation_date`, and two
more covered at the end (`lei`, `expiration_date`). This page says why,
what a null does and does not tell you, and what you can do about it.

The short answer is the same for the first five: **the source is silent.**
SWIFT's file has an empty cell, and the registry does not invent a value.

## Why a null is source silence, not a failure

Two things could in principle make a field null: SWIFT published nothing,
or the registry failed to work something out. Only the first happens.

- **There is no derivation.** [`PROVENANCE.md`](./PROVENANCE.md) states
  that every field comes from a single source column and that no field is
  computed from another registry at build time. For these fields the
  fetcher's whole job is `clean(cell)` (`tools/fetch_swift_mic.py`): strip
  whitespace, and turn an empty string into `null`. A field is null if and
  only if its source cell is empty or blank.
- **The rule is deliberate.** "If a value cannot be traced to [the SWIFT
  file], the field stays `null`" (`PROVENANCE.md`, Source of truth). No
  third-party lists, no scraping, no fallback.
- **A bad value is not a null.** A date that is not `YYYYMMDD` raises an
  error and stops the refresh (`to_iso_date`); it is never quietly nulled.
  So a null date is an empty cell, not a parse failure.

What a null does **not** tell you: whether the venue has an acronym, a
website or a legal entity (it may), whether SWIFT meant to leave the cell
empty, or why. The file does not say, and neither does the registry.

## How common, and where the fields are

Counts on snapshot 2026-09-23 (2,883 entries). They change with each
monthly refresh; the snippet below recomputes them.

| Field | Source column | Null | Operating | Segment | Active | Expired | Updated |
|-------|---------------|-----:|----------:|--------:|-------:|--------:|--------:|
| `acronym` | `ACRONYM` | 1,867 | 1,002 | 865 | 1,409 | 444 | 14 |
| `legal_entity_name` | `LEGAL ENTITY NAME` | 1,494 | 982 | 512 | 1,111 | 383 | 0 |
| `note` | `COMMENTS` | 1,324 | 805 | 519 | 1,117 | 201 | 6 |
| `website` | `WEBSITE` | 163 | 139 | 24 | 28 | 135 | 0 |
| `last_validation_date` | `LAST VALIDATION DATE` | 1,896 | 1,171 | 725 | 1,447 | 449 | 0 |
| `lei` | `LEI` | 629 | 450 | 179 | 416 | 212 | 1 |
| `expiration_date` | `EXPIRY DATE` | 2,317 | 1,338 | 979 | 2,296 | 0 | 21 |

All of these are in the JSON, CSV, TSV and Parquet files. **The SQL
exports do not carry them,** except `last_validation_date` and
`expiration_date`: the SQL table has 11 of the 17 fields and is a foreign-key reference table (see the
README's SQL section). Use JSON, CSV or Parquet when you need these.

```python
import json
from collections import Counter

registry = json.load(open("iso10383.json", encoding="utf-8"))
mics = registry["mics"]
by_mic = {m["mic"]: m for m in mics}

print("snapshot", registry["meta"]["source_snapshot"], "-", len(mics), "entries")
for field in ("acronym", "legal_entity_name", "note", "website",
              "last_validation_date", "lei", "expiration_date"):
    nulls = [m for m in mics if m[field] is None]
    by_type = Counter(m["mic_type"] for m in nulls)
    by_status = Counter(m["status"] for m in nulls)
    # segments whose own value is null while their operating MIC has one
    gap = sum(1 for m in nulls
              if m["mic_type"] == "SEGMENT"
              and by_mic[m["operating_mic"]][field] is not None)
    print(f"{field:22} null {len(nulls):5}  "
          f"OPERATING {by_type['OPERATING']:5}  SEGMENT {by_type['SEGMENT']:5}  "
          f"ACTIVE {by_status['ACTIVE']:5}  EXPIRED {by_status['EXPIRED']:4}  "
          f"UPDATED {by_status['UPDATED']:3}  segment-null/operating-set {gap}")
```

The schema allows null in more fields than these (`market_name`, `city`,
`country_code`, `market_category`, `creation_date`, `last_update_date`),
but this snapshot has none there.

## `acronym`

**Source:** the `ACRONYM` column. **Null:** 1,867 of 2,883, in both
operating and segment entries.

SWIFT left the cell empty. That is not a statement that the venue has no
acronym. 171 segment entries have no acronym while their operating MIC has
one; the registry does not copy it down, because it cannot tell whether
SWIFT meant the segment to share it.

**If you need one:** the registry has no other source. Treat it as
display text, never as a key or a join column.

## `legal_entity_name`

**Source:** `LEGAL ENTITY NAME`. **Null:** 1,494, including 383 expired
and 982 operating entries.

The cell is empty in the source. A null does not mean no legal entity
exists. The related `lei` column is separate and has its own gaps (below);
the registry publishes it as SWIFT gives it and does not map MICs to LEIs
([ADR 0008](./decisions/0008-mic-lei-companion-declined.md)). 123 segment
entries have no name while their operating MIC has one.

**If you need one:** resolve it outside this registry, and record where it
came from.

## `note`

**Source:** the `COMMENTS` column, which this registry names `note`.
**Null:** 1,324.

`note` is SWIFT's free text, in SWIFT's wording and upper case (for
example "REGISTERED MARKET FOR EQUITIES."). Null means SWIFT wrote no
comment. The registry does not parse it or derive fields from it. A comment can be
specific to the entry it sits on, so the registry does not copy it down
(115 segments have no note while their operating MIC has one).

## `website`

**Source:** `WEBSITE`. **Null:** 163; 135 of them are on expired entries
and 28 on active ones.

The cell is empty. The registry stores the string as given, with
whitespace stripped. It does not normalise the URL or check that it
resolves, so a non-null website can be stale. All 24 segments with no
website have an operating MIC that has one; the registry does not copy it.

**If you need a website for an active entry that has none:** that is the
28 cases to look at by hand, outside this registry.

## `last_validation_date`

**Source:** `LAST VALIDATION DATE` (`YYYYMMDD` in the file, `YYYY-MM-DD`
here). **Null:** 1,896, including 1,447 active entries; none of the 21
`UPDATED` entries is null.

An empty cell means SWIFT published no validation date. Do not read it as
"never validated", and do not read an old date as "unreliable": the file
says nothing either way. This is SWIFT's date. It is unrelated to
`meta.source_snapshot`, which is when this registry downloaded the file.

## The other two nullable fields

- **`lei`** follows the same rule: the `LEI` cell is empty (629 entries),
  and the registry does not look an LEI up anywhere else
  ([ADR 0008](./decisions/0008-mic-lei-companion-declined.md)).
- **`expiration_date` is not source silence.** Its null has a meaning:
  the entry has not expired. Every `EXPIRED` entry has an
  `expiration_date` and no other entry has one (566 and 566 in this
  snapshot), and the validator rejects an expired entry without one
  (`tools/validate.py`). Test `status`, not the date, to ask whether a MIC
  is expired.

## If you choose to enrich

The registry will not fill a null from another entry, and neither SWIFT's
file nor the registry says that a segment should inherit its operating
MIC's values. If you want that in your own data, do it in your layer and
keep track of which values you added:

```python
mics = {m["mic"]: m for m in registry["mics"]}

def with_operating_fallback(mic, field):
    """Your choice, not the registry's: the entry's value, else its operating MIC's."""
    m = mics[mic]
    if m[field] is not None:
        return m[field], "own"
    return mics[m["operating_mic"]][field], "inherited"
```

For example, a segment with no `acronym` returns the operating MIC's
acronym tagged `"inherited"`, and an entry with its own acronym returns it
tagged `"own"`. Keep the tag: a value you inherited is a different claim
from a value SWIFT published. Everything else about where values come from
is in [`PROVENANCE.md`](./PROVENANCE.md).
