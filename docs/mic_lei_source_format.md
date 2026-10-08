# GLEIF MIC-to-LEI Source Format — Ground Truth

Reconnaissance for the v1.1.0 MIC→LEI companion, performed on
2026-10-05 against GLEIF's 2026-09-18 publication and ISO 10383
v1.0.4. Concluded that the companion is unnecessary: GLEIF's file is
a strict subset of the `lei` field already present on
`iso10383.json`. See § Finding and § Decision below.

---

## Source

| | |
|--|--|
| Source page | https://www.gleif.org/en/lei-data/lei-mapping/download-mic-to-lei-relationship-files |
| Download URL pattern | `https://mapping.gleif.org/api/v2/mic-lei/<UUID>/download` |
| Snapshot file | `LEI-MIC-20260918.zip` |
| Inner file | `lei-mic-20260918T000007.csv` |
| Downloaded | 2026-10-05 |
| Registry version compared against | `iso10383.json` v1.0.4 |
| Registry snapshot date | 2026-09-23 |

The download URL carries a per-publication UUID. The UUID changes
every month, so the URL cannot be hardcoded. A future fetcher reads
the source page, extracts the newest `LEI-MIC-YYYYMMDD.zip` link,
and downloads from the UUID-scoped URL.

---

## File format

| Property | Value |
|----------|-------|
| Container | ZIP, one CSV inside |
| CSV size | 26,632 bytes (2026-09-18 publication) |
| Encoding | UTF-8, ASCII-only content |
| Line endings | LF |
| Delimiter | Comma |
| Quote character | None — no quoted fields in the file |
| Embedded commas | None in any column |
| Header row | Yes, line 1 |

The file is small enough to parse in one pass with `csv.DictReader`.
The parser does not need streaming. Quoting is not required on read,
but the parser uses `csv.DictReader` anyway for consistency with the
rest of the tooling in the repository.

---

## Verbatim column headers

```
LEI,MIC
```

Two columns. Both uppercase. Both required. No optional columns.

- **`LEI`** — 20-character ISO 17442 Legal Entity Identifier.
- **`MIC`** — 4-character ISO 10383 Market Identifier Code. Operating
  MICs only; the file contains no segment MICs.

The order matters: `LEI` is column 1, `MIC` is column 2. A parser
that reads by name rather than position is unaffected; one that reads
by position must respect this order.

---

## Row count

**1,024 MIC-LEI pairs** in the 2026-09-18 publication.

The count grows over time. The 2022 first publication had
approximately 600 pairs. GLEIF adds pairs when a new operating
entity obtains an LEI and registers its MIC, and removes them when an
LEI is annulled or marked as a duplicate by GLEIF, or when the MIC
expires at SWIFT.

The count is a property of the file, not a fixed target. A future
reconnaissance records whatever the current publication contains.

---

## Value formats

| Field | Pattern | Rows failing |
|-------|---------|--------------|
| `LEI` | `^[A-Z0-9]{18}[0-9]{2}$` | **0** |
| `MIC` | `^[A-Z0-9]{4}$` | **0** |

Both columns are 100% compliant in the current publication. No row
requires coercion, correction, or skipping.

The `LEI` pattern enforces ISO 17442: eighteen uppercase alphanumeric
characters followed by two numeric check digits. The two check digits
are computed by ISO/IEC 7064 MOD 97-10. The reconnaissance verified
the check digits on every row: all 1,024 pass.

The `MIC` pattern matches the primary key format of `iso10383.json`.

---

## Duplicates

**Unique MICs:** 1,024.
**Duplicated:** 0.

Every MIC appears exactly once. The file is a MIC-LEI *pairing* table
— the relationship between a single MIC and a single LEI — not a
MIC-to-many-LEIs table. A MIC that appears twice would mean the
pairing is broken at the source.

A future reconnaissance that finds duplicates records them and
investigates. Today's publication is clean.

---

## Cross-check against `iso10383.json`

The registry at v1.0.4 carries 1,594 operating MICs and 1,289 segment
MICs, for a total of 2,883 entries. Each entry has an `lei` field,
populated by SWIFT from its own source. The field is nullable.

### The four counts

| Metric | Count |
|--------|-------|
| Registry operating MICs | 1,594 |
| GLEIF file MICs | 1,024 |
| Operating MICs with an LEI in GLEIF | 1,024 |
| Operating MICs without an LEI in GLEIF | 570 |
| GLEIF MICs not present as operating MICs in the registry | 0 |

Every MIC in GLEIF's file resolves to an operating MIC in the
registry. None is a segment MIC. None is absent.

### Existing `lei` field coverage

The registry's `lei` field, populated by SWIFT's MIC file:

| Metric | Count | Percentage |
|--------|-------|------------|
| Populated | 1,144 | 71.8% |
| Null | 450 | 28.2% |

SWIFT populates more operating MICs than GLEIF does. The 120-entry
difference is the subject of § What the 120 are.

### Agreement between the two sources

| Agreement class | Count |
|-----------------|-------|
| Same LEI where both sources have a value | 1,024 |
| Different LEI where both sources have a value | **0** |
| Field populated, absent from GLEIF | 120 |
| Field null, present in GLEIF | **0** |

The two sources agree on every MIC they share. There is no
disagreement to reconcile.

### The coverage matrix

|  | GLEIF has LEI | GLEIF absent | Total |
|--|---------------|--------------|-------|
| **SWIFT has LEI** | 1,024 | 120 | 1,144 |
| **SWIFT null** | 0 | 450 | 450 |
| **Total** | 1,024 | 570 | 1,594 |

The union of the two sources is 1,144 — exactly SWIFT's populated
count. GLEIF adds nothing to the union.

---

## Finding

**GLEIF's MIC-to-LEI Mapping Table is a strict subset of the `lei`
field on `iso10383.json`.**

The proof is the coverage matrix. Every MIC-LEI pair GLEIF publishes
is already in the registry, and every value agrees. The registry
carries 120 pairs GLEIF does not. There are no pairs in GLEIF that
the registry lacks. There are no disagreements where both sources
have a value.

**The relationship is structural, not coincidental.** GLEIF's own
license agreement states that it extracts the mapping from SWIFT's
published MIC directory. When SWIFT expires a MIC, GLEIF removes the
pair; SWIFT keeps the `lei` field on the entry as a historical
record. That asymmetry is why the field is a strict superset.

**A companion file as planned in D11 would duplicate existing data.**
A `mic-lei.json` with one entry per operating MIC would ship 1,024
rows whose values are already in `iso10383.json`, and would omit the
120 rows the field carries and GLEIF does not.

Three specific conclusions follow:

1. **There is nothing to reconcile.** A companion's value would be in
   recording where the sources differ. They do not differ.
2. **There is nothing to enrich.** Enrichment requires GLEIF to add
   a value the registry lacks. It does not.
3. **There is a duplicate-of-truth risk.** A consumer reading both
   sources would have to know which to prefer. The registry field is
   the more complete source; a companion would add confusion rather
   than clarity.

The reconnaissance has answered the question the v1.1.0 roadmap
posed. The answer is that there is no work to do.

---

## What the 120 are

The 120 operating MICs that SWIFT populates with an LEI and GLEIF
does not are not a mystery. Every one of them is explained.

**118 are expired operating MICs.** Their `status` in
`iso10383.json` is `EXPIRED`. GLEIF pruned the pair when the MIC was
deactivated. SWIFT kept the field.

**2 are ACTIVE:**

| MIC | LEI | Name |
|-----|-----|------|
| `CBMS` | `213800AB3875YAOXX245` | CBM SARB |
| `HEGX` | `5493005SLPBS4GLS2A55` | NADEX |

Both are US binary options venues. Both carry an LEI in SWIFT's
field that GLEIF does not publish. The likely explanations are:

- The LEI is marked `ANNULLED` or `DUPLICATE` in GLEIF's Golden Copy
  and GLEIF excludes such LEIs from its mapping file by policy.
- SWIFT added the LEI to its file after GLEIF's last extraction
  cycle.

Distinguishing the two requires GLEIF's Golden Copy, which is not
part of this reconnaissance. Neither MIC affects the decision: the
subset relationship holds regardless of why GLEIF omits them.

A future maintainer investigating the same question records the
resolution of these two in this section.

---

## Snapshot date source

The publication date is in the ZIP filename: `LEI-MIC-YYYYMMDD.zip`.

The CSV inside adds a timestamp: `lei-mic-YYYYMMDDTHHMMSS.csv`. The
two dates are the same day in the current publication. A future
publication could in principle carry different dates if GLEIF
regenerates the CSV on a different day than the ZIP packaging; the
reconnaissance has not observed this, but the parser should read the
ZIP name for the snapshot date, not the CSV name.

Neither the ZIP nor the CSV carries a date column. A consumer that
needs the publication date reads the filename.

`meta.source_snapshot` for a future refresh reads from the ZIP
filename: the eight digits between `LEI-MIC-` and `.zip`.

---

## Refresh cadence

Monthly, on or around the second Monday. The publication list from
the source page for 2026 covers nine calendar months:

| Publication | Date |
|-------------|------|
| `LEI-MIC-20260120.zip` | 2026-01-20 |
| `LEI-MIC-20260209.zip` | 2026-02-09 |
| `LEI-MIC-20260210.zip` | 2026-02-10 |
| `LEI-MIC-20260309.zip` | 2026-03-09 |
| `LEI-MIC-20260413.zip` | 2026-04-13 |
| `LEI-MIC-20260511.zip` | 2026-05-11 |
| `LEI-MIC-20260608.zip` | 2026-06-08 |
| `LEI-MIC-20260713.zip` | 2026-07-13 |
| `LEI-MIC-20260728.zip` | 2026-07-28 |
| `LEI-MIC-20260810.zip` | 2026-08-10 |
| `LEI-MIC-20260914.zip` | 2026-09-14 |
| `LEI-MIC-20260918.zip` | 2026-09-18 |

Twelve publications in nine calendar months. February, July, and
September each carry a mid-month correction in addition to the
scheduled release — `2026-02-09` / `2026-02-10`, `2026-07-13` /
`2026-07-28`, and `2026-09-14` / `2026-09-18`. The second publication
in a month is a correction cycle, not a scheduled release.

A future refresh process reads whatever the source page links as the
newest file. It does not assume a fixed day.

---

## License

The MIC/LEI Mapping Table License Agreement v1.0 governs the file.
The agreement is published on GLEIF's download page alongside the
factsheet and the CSV import guide.

### What the license permits

Redistribution is permitted. The license grants each member of the
public a non-exclusive, transferable, sub-licensable, royalty-free
license to use the Mapping Table:

- In all territories worldwide.
- For the maximum duration permitted by applicable law.
- In any current or future medium.
- For any purpose, including commercial, advertising, and
  promotional purposes.

### The one condition

Any copy of the Mapping Table, in whole or in part, must include the
following notice:

```
SWIFT © and database rights [insert date of the Mapping Table version].
All rights reserved. This Mapping Table has been developed by SWIFT.
Any use of the Mapping Table, in whole or in part, is subject to the
MIC/LEI Mapping Table License Agreement as published with the Mapping
Table available on GLEIF's website. The Mapping Table is updated
monthly. For the latest MIC information and updates, always refer to
https://www.iso20022.org/market-identifier-codes.
```

The bracketed `[insert date of the Mapping Table version]` is a
placeholder in the license text. The license expects a **month and
year**, not a full ISO date. For the snapshot used in this
reconnaissance, the value is:

```
September 2026
```

### What this means for the companion

**If the companion had shipped, redistribution would have been
permitted.** The file would have shipped committed, the same shape as
`iso10383.json`, with the notice in `meta.license` or a sibling
`NOTICE` file. This is not the Asset Identifiers user-supplied-data
shape; there is no data-license split.

The companion is declined (see § Decision), so the notice is not
currently used. It is recorded here so a future maintainer
investigating the same source has the license terms without
re-downloading the PDF and re-reading the agreement.

**Verify the notice against the license PDF before using it.** The
text above was transcribed from the license agreement at the time of
this reconnaissance. If the PDF has been revised since, the current
text supersedes.

---

## Decision

**Declined. The companion file does not ship.**

The v1.1.0 release that D11 planned does not happen. No
`mic-lei.json` is created. No schema, fetcher, validator, exports,
or CLI additions are built. The registry stays at v1.0.4.

The registry's `lei` field is the source of truth for an operating
MIC's legal entity identifier. A consumer that wants the LEI reads
the entry. No lookup file is required.

See [ADR 0008](./decisions/0008-mic-lei-companion-declined.md) for
the full decision record, the alternatives considered, and the
consequences.

---

## What a future maintainer should do

The declaration "the two sources agree" is a fact about the
2026-09-18 publication, not a permanent guarantee. Two set-based
conditions warrant re-running the reconnaissance:

**1. A MIC in GLEIF but not in SWIFT's field.** If a future
cross-check finds even one MIC-LEI pair that GLEIF publishes and
`iso10383.json` does not carry, GLEIF has become a source of new
data rather than a duplicate. The companion decision may flip.

**2. A MIC with different LEI values in the two sources.** If a
future cross-check finds even one MIC whose LEI differs between
SWIFT's field and GLEIF's file, the reconciliation the companion was
supposed to provide becomes worth shipping, and the disagreement is
itself a finding.

Neither condition is monitored by CI today. A future maintainer
re-runs the procedure below on the current publication to check both.

The 118 expired MICs are not a trigger. The two ACTIVE exceptions
(`CBMS`, `HEGX`) are not a trigger unless GLEIF's reason for omitting
them turns out to be a data-quality issue in SWIFT's field.

---

## Reproduction

The reconnaissance that produced every number in this document was a
one-off script. A future maintainer can rebuild it from this
section. The procedure is nine steps.

**1. Download the newest ZIP.**

```bash
mkdir -p ~/mic-lei-recon/raw
cd ~/mic-lei-recon/raw
# From the source page, find the newest LEI-MIC-YYYYMMDD.zip link.
# Download it by hand or with curl.
```

**2. Extract and identify the CSV.**

```bash
unzip -o LEI-MIC-*.zip
ls *.csv
```

**3. Parse the CSV.**

```python
import csv
with open("lei-mic-*.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
```

**4. Format checks.** Confirm every `LEI` matches
`^[A-Z0-9]{18}[0-9]{2}$` and every `MIC` matches `^[A-Z0-9]{4}$`.
Zero failures is expected.

**5. Duplicate check.** Confirm `len(set(row["MIC"])) == len(rows)`.

**6. Load the registry.**

```python
import json
reg = json.load(open("iso10383.json"))
op = {m["mic"]: m for m in reg["mics"] if m["mic_type"] == "OPERATING"}
```

**7. Cross-check.** Compute:

- `len(rows)` — GLEIF file MICs
- `len(op)` — registry operating MICs
- `len(set(r["MIC"] for r in rows) & set(op))` — in both
- `len(set(r["MIC"] for r in rows) - set(op))` — GLEIF only
- `sum(1 for m in op.values() if m.get("lei"))` — SWIFT populated
- Agreement count: for each MIC in both, compare `op[mic]["lei"]` to
  the GLEIF row's `LEI`.

**8. Compare to this document.** Every count in the tables above
should match. If any does not, the source or the registry has
changed since 2026-10-05, and the finding needs to be re-derived.

**9. Update this document if the finding changes.** If the numbers
still show a strict subset, the decision stands. If they do not, the
decision is re-opened and ADR 0008 is amended.

The full script that produced the numbers above was a one-off. It
was not committed. The procedure above is its equivalent.
