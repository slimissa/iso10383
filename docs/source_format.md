# ISO 10383 Source Format — Ground Truth

**Source URL:** https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv
**Downloaded:** 2026-09-23
**Size:** 589,482 bytes
**Data rows:** [output of the Python script's "rows:" line]

## File format

- UTF-8, LF line endings
- **Every field is quoted with `"`**
- **Fields containing commas are present** in `MARKET NAME-INSTITUTION
  DESCRIPTION`, `LEGAL ENTITY NAME`, and `COMMENTS`. `cut -d,` and
  `awk -F,` corrupt output on these rows. The parser must use Python's
  `csv` module or equivalent.
- Header row present as line 1
- All header names are ALL CAPS

## Verbatim column headers (17 columns)

1 MIC
2 OPERATING MIC
3 OPRT/SGMT
4 MARKET NAME-INSTITUTION DESCRIPTION
5 LEGAL ENTITY NAME
6 LEI
7 MARKET CATEGORY CODE
8 ACRONYM
9 ISO COUNTRY CODE (ISO 3166)
10 CITY
11 WEBSITE
12 STATUS
13 CREATION DATE
14 LAST UPDATE DATE
15 LAST VALIDATION DATE
16 EXPIRY DATE
17 COMMENTS
text


Mapping to JSON field names (from `v1.0.0-decisions.md`):

| Source column | JSON field |
|---------------|------------|
| MIC | `mic` |
| OPERATING MIC | `operating_mic` |
| OPRT/SGMT | (derives `mic_type`) |
| MARKET NAME-INSTITUTION DESCRIPTION | `market_name` |
| LEGAL ENTITY NAME | `legal_entity_name` |
| LEI | `lei` (out of scope v1.0.0, D11) |
| MARKET CATEGORY CODE | `market_category` |
| ACRONYM | `acronym` |
| ISO COUNTRY CODE (ISO 3166) | `country_code` |
| CITY | `city` |
| WEBSITE | `website` |
| STATUS | `status` |
| CREATION DATE | `creation_date` |
| LAST UPDATE DATE | `last_update_date` |
| LAST VALIDATION DATE | `last_validation_date` |
| EXPIRY DATE | `expiration_date` |
| COMMENTS | `note` |

## OPRT/SGMT value set

1594 OPRT
1289 SGMT
text


Two values. **Confirms D5**: `mic_type` ∈ {OPERATING, SEGMENT}.

## STATUS value set

2096 ACTIVE
527 EXPIRED
19 UPDATED
text


Three values. **Confirms D2**: `status` ∈ {ACTIVE, UPDATED, EXPIRED}.

## MARKET CATEGORY CODE value set

[paste output of the Python script's MARKET CATEGORY section]


## Self-reference case

Rows where `MIC == OPERATING MIC`: **1594**

This matches the `OPRT` count exactly. Every operating MIC has
`OPERATING MIC == MIC`. Every segment MIC has `OPERATING MIC`
pointing to its parent.

**Confirms D3**: `operating_mic` is non-null for every entry.
Operating MICs self-reference; segment MICs point to their parent.
No cycle-detection rule will be added; self-reference is the pattern.

## Date format

All dates are `YYYYMMDD` (e.g. `20210927`), not ISO 8601. The fetcher
converts to ISO 8601 on output.

## Snapshot date source

The file does not embed a publication date. The snapshot date is the
download date: **2026-09-23**.

## Consequences for Phase 1 (parser)

1. **Use `csv.DictReader`**, not `cut` or `split(",")`. Quoted fields
   with internal commas exist.
2. **Convert `YYYYMMDD` → `YYYY-MM-DD`** for `creation_date`,
   `last_update_date`, `last_validation_date`, `expiration_date`.
3. **Empty string → `null`** for optional fields (`lei`, `expiration_date`,
   `comments`, `acronym`).
4. **`mic_type` is derived**, not sourced directly: `OPRT` → `OPERATING`,
   `SGMT` → `SEGMENT`. The parser maps, the schema enforces.
5. **`operating_mic` is never null.** For rows where `OPRT/SGMT == OPRT`,
   set `operating_mic = mic`. For rows where `OPRT/SGMT == SGMT`, set
   `operating_mic` to the source `OPERATING MIC` value.

## Consequences for Phase 2 (schema)

1. The `market_category` enum is the set shown above, closed.
2. The `status` enum is `{ACTIVE, UPDATED, EXPIRED}`, closed.
3. The `mic_type` enum is `{OPERATING, SEGMENT}`, closed.
4. `operating_mic` has the same `^[A-Z0-9]{4}$` pattern as `mic` and is
   never null.