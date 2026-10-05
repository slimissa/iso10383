# GLEIF MIC-to-LEI Source Format — Ground Truth

**Source page:** https://www.gleif.org/en/lei-data/lei-mapping/download-mic-to-lei-relationship-files
**Download URL pattern:** https://mapping.gleif.org/api/v2/mic-lei/<UUID>/download
**Snapshot file:** LEI-MIC-YYYYMMDD.zip
**Snapshot used:** LEI-MIC-20260918.zip
**Downloaded:** 2026-10-05

## File format

- **Container:** ZIP
- **Inner file:** [filename].csv
- **Delimiter:** comma
- **Qualifier:** double quotation mark
- **Encoding:** UTF-8
- **Line endings:** LF or CRLF — confirm

## Verbatim column headers

```
[paste from Step 2 output]
```

## Row count

```
[paste from Step 2 output]
```

## Value formats

| Field | Pattern | Rows failing |
|-------|---------|--------------|
| LEI   | `^[A-Z0-9]{18}[0-9]{2}$` | [N] |
| MIC   | `^[A-Z0-9]{4}$` | [N] |

## Duplicate MICs

Unique MICs: [N]. Duplicated: [M].

## Cross-check against iso10383.json

| Metric | Count |
|--------|-------|
| GLEIF file MICs | [N] |
| Registry operating MICs | 1,594 |
| Operating MICs with an LEI in the file | [N] |
| Operating MICs without an LEI in the file | [M] |
| GLEIF MICs not present as operating MICs | [K] |

**Existing `lei` field coverage on operating MICs** (from SWIFT's MIC file):

| Metric | Count | % |
|--------|-------|---|
| Populated | [N] | [%] |
| Null | [M] | [%] |

**Agreement between SWIFT's field and GLEIF's file:**

| Agreement | Count |
|-----------|-------|
| Same LEI where both have one | [N] |
| Different LEI where both have one | [M] |
| Field populated, absent from file | [K] |
| Field null, present in file | [J] |

## Snapshot date source

Filename: `LEI-MIC-YYYYMMDD.zip`. The ZIP name carries the publication date. [Confirm whether the CSV carries any date column.]

## License

The MIC/LEI Mapping Table License Agreement v1.0 permits redistribution of the Mapping Table in whole or in part, including commercial use and sub-licensing, provided the required notice is included with any copy.

**Required notice (verbatim from the PDF):**

```
[paste the notice exactly as it appears]
```

**Decision:** the companion file ships committed, with the required notice in `meta.license` or a sibling `NOTICE` file. This is the same shape as `iso10383.json`, not the Asset Identifiers user-supplied-data shape.

## File-shape decision

[Choose one:]

- **Enrichment** — the existing `lei` field covers most operating MICs and agrees with the file. Companion records disagreements and the reconciliation.
- **New mapping** — the existing `lei` field covers few operating MICs. Companion is a full table for every operating MIC with an LEI in the file.
- **Hybrid** — partial overlap. Companion carries a `source` field per entry.

**Chosen:** [Enrichment / New mapping / Hybrid]

**Reasoning:** [one paragraph from the numbers above]