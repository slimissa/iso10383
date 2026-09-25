# Provenance — ISO 10383 MIC Registry

What this registry contains, where it comes from, how it is refreshed,
how it is audited, and what is intentionally not covered.

---

## Source of truth

**One source:** the SWIFT-published ISO 10383 MIC file, hosted at
`https://www.iso20022.org/market-identifier-codes`.

No third-party MIC lists, no mirrors, no Wikipedia, no aggregators.
The published file is the only authority. If a value cannot be traced
to it, the field stays `null`.

The registry does not scrape. The fetcher downloads the published CSV,
parses it, and emits `iso10383.json`. A copy of the raw CSV is cached
in `raw/` (gitignored) and never re-downloaded unless `--force` is
passed. The cache is the artifact that `meta.source_hash` refers to.

---

## File format consumed

The source file, as of the 2026-09-23 snapshot:

| Property | Value |
|----------|-------|
| Encoding | UTF-8, LF line endings |
| Size | 589,482 bytes |
| Data rows | 2,883 |
| Columns | 17, all header names ALL CAPS, every field quoted |
| Field delimiter | `,` |
| Quote character | `"` |
| Escaping | Doubled quotes (`""`) inside quoted fields |

**Every field is quoted.** Fields containing commas exist in
`MARKET NAME-INSTITUTION DESCRIPTION`, `LEGAL ENTITY NAME`, and
`COMMENTS`. `cut -d,` and `awk -F,` corrupt these rows. The parser
uses Python's `csv` module.

### Verbatim column headers

```
 1  MIC
 2  OPERATING MIC
 3  OPRT/SGMT
 4  MARKET NAME-INSTITUTION DESCRIPTION
 5  LEGAL ENTITY NAME
 6  LEI
 7  MARKET CATEGORY CODE
 8  ACRONYM
 9  ISO COUNTRY CODE (ISO 3166)
10  CITY
11  WEBSITE
12  STATUS
13  CREATION DATE
14  LAST UPDATE DATE
15  LAST VALIDATION DATE
16  EXPIRY DATE
17  COMMENTS
```

### Column to JSON field mapping

| Source column | JSON field | Notes |
|---------------|------------|-------|
| `MIC` | `mic` | Primary key. |
| `OPERATING MIC` | `operating_mic` | Parent MIC. Non-null for every entry. |
| `OPRT/SGMT` | *(derives `mic_type`)* | `OPRT` → `OPERATING`, `SGMT` → `SEGMENT`. Not stored directly. |
| `MARKET NAME-INSTITUTION DESCRIPTION` | `market_name` | |
| `LEGAL ENTITY NAME` | `legal_entity_name` | |
| `LEI` | `lei` | Out of scope for v1.0.0 (D11); stored but unused. |
| `MARKET CATEGORY CODE` | `market_category` | |
| `ACRONYM` | `acronym` | |
| `ISO COUNTRY CODE (ISO 3166)` | `country_code` | |
| `CITY` | `city` | |
| `WEBSITE` | `website` | |
| `STATUS` | `status` | |
| `CREATION DATE` | `creation_date` | |
| `LAST UPDATE DATE` | `last_update_date` | |
| `LAST VALIDATION DATE` | `last_validation_date` | |
| `EXPIRY DATE` | `expiration_date` | |
| `COMMENTS` | `note` | |

### Value sets observed

**`OPRT/SGMT`** — two values, closed enum (D5):

```
1594  OPRT
1289  SGMT
```

**`STATUS`** — three values, closed enum (D2):

```
2296  ACTIVE
 566  EXPIRED
  21  UPDATED
```

**`MARKET CATEGORY CODE`** — 14 of the 16 codes defined by the
Release 2.0 factsheet appear in the 2026-09-23 snapshot. `ARMS` and
`CTPS` are defined but currently unassigned. The registry's enum is
the union of all 16 (D4).

```
1307  NSPD     381  MLTF     351  SINT     303  RMKT
 143  ATSS     129  OTHR     128  OTFS      30  SEFS
  30  CASP      27  RMOS      26  APPA      22  DCMS
   5  TRFS       1  IDQS
```

### Date format

All dates in the source are `YYYYMMDD` (e.g. `20210927`), not ISO
8601. The fetcher converts to `YYYY-MM-DD` on output. Empty dates map
to `null`.

### Snapshot date

The source file does not embed a publication date. The snapshot date
is the download date, passed explicitly to the fetcher with
`--snapshot-date`. The monthly refresh workflow passes the current
UTC date.

---

## The hierarchy model

Every MIC has a parent MIC. There is no other shape.

- An **operating MIC** identifies an entity that operates an exchange,
  a trading platform, or a trade reporting facility. Its
  `operating_mic` is itself: `operating_mic == mic`.
- A **segment MIC** identifies a section of an entity that specialises
  in specific instruments or is regulated differently. Its
  `operating_mic` is its parent. The parent may itself be a segment.

The parent chain terminates at an operating MIC. The 2026-09-23
snapshot contains eight three-level chains. Example:

```
XEAS  (SEGMENT, parent XEQT)
 └── XEQT  (SEGMENT, parent XBER)
      └── XBER  (OPERATING)
```

The fetcher resolves every chain from its leaf up to its operating
MIC. Chains deeper than eight levels are refused. Cycles are refused.
A missing parent is recorded in `meta.broken_chains` and does not
abort the parse.

The 2026-09-23 snapshot has **0 broken chains**.

### Why this is unusual

ISO 4217 and ISO 3166 have flat lists. MIC is the first registry in
the family with a self-referential parent field. The schema models
this directly: `operating_mic` is a required, non-null string with the
same pattern as `mic`. The SQL export declares `operating_mic` as a
self-referencing foreign key with `NOT NULL`. The Python and JavaScript
wrappers accept `operating_mic == mic` for operating MICs and reject
it for segments. The Rust and Go wrappers rely on the type system to
make the same distinction impossible to violate.

---

## Field-by-field sourcing

Every field is derived from a single source column. No field is
computed from another registry at build time. Enrichment from sibling
registries is a validation step, not a data step.

| Field | Source | Refresh cadence |
|-------|--------|-----------------|
| `mic` | `MIC` column | Monthly with the source file |
| `mic_type` | Derived from `OPRT/SGMT` | Monthly |
| `status` | `STATUS` column | Monthly |
| `operating_mic` | `OPERATING MIC` column | Monthly |
| `market_name` | `MARKET NAME-INSTITUTION DESCRIPTION` | Monthly |
| `legal_entity_name` | `LEGAL ENTITY NAME` | Monthly |
| `lei` | `LEI` column | Monthly |
| `market_category` | `MARKET CATEGORY CODE` | Monthly |
| `acronym` | `ACRONYM` | Monthly |
| `country_code` | `ISO COUNTRY CODE (ISO 3166)` | Monthly |
| `city` | `CITY` | Monthly |
| `website` | `WEBSITE` | Monthly |
| `creation_date` | `CREATION DATE`, converted | Monthly |
| `last_update_date` | `LAST UPDATE DATE`, converted | Monthly |
| `last_validation_date` | `LAST VALIDATION DATE`, converted | Monthly |
| `expiration_date` | `EXPIRY DATE`, converted | Monthly |
| `note` | `COMMENTS` | Monthly |

No field is hand-curated. No field is populated from a source other
than the SWIFT file. Hand-edits to `iso10383.json` are detected by the
validator and refused in CI.

### Country codes

`country_code` carries the ISO 3166-1 alpha-2 code published by SWIFT.
One value in the current snapshot is not a valid ISO 3166 code:
`ZZ`, which ISO 10383 uses as a placeholder for "no fixed country."
The validator treats `ZZ` as a known non-ISO placeholder and does not
flag it.

Every other `country_code` must exist in the committed ISO 3166
snapshot (`tools/iso3166_snapshot.json`). Cross-registry validation is
**advisory in v1.0.0** and blocking in v1.0.1 (D6).

---

## Refresh cadence

SWIFT publishes the MIC file on the **second Monday of each month**.
Modifications become effective on the fourth Monday. Requests received
by the first Monday are processed for that month's publication.

CI fails if `meta.source_snapshot` is more than **60 days old**
(`tools/check_snapshot_freshness.py`). Sixty days is one full missed
cycle — a signal that the update process broke, not that the source is
late.

### The monthly process, automated

`.github/workflows/refresh.yml` runs on the **15th of every month at
00:00 UTC** and on manual dispatch. It:

1. Downloads the current SWIFT file.
2. Snapshots the old registry to `/tmp/iso10383.old.json`.
3. Runs `tools/fetch_swift_mic.py` with `--snapshot-date` set to the
   current UTC date.
4. Diffs the two registries with `tools/refresh_diff.py`.
5. Regenerates all nine distribution artifacts.
6. Regenerates the four wrapper bundle copies.
7. Runs the six-layer validator and the root test suite.
8. Opens a pull request.

The PR body carries the diff summary. A refresh with `REMOVED > 0`
fails the job's diff step and requires human confirmation before
merging. This is D10.

### The monthly process, manual

```bash
python3 tools/fetch_swift_mic.py --download --force --strict
python3 tools/refresh_diff.py /tmp/iso10383.old.json iso10383.json
python3 tools/export_csv.py
python3 tools/export_sql.py
python3 tools/export_parquet.py
python3 tools/sync_wrappers.py
python3 tools/validate.py
python3 -m pytest tests/ -q
```

Then commit with a `CHANGELOG.md` entry and tag a patch or minor
release per Semantic Versioning.

### What a refresh changes

A typical monthly refresh produces one of four diff shapes:

| Shape | Meaning | Action |
|-------|---------|--------|
| NEW only | New MICs added | Merge after review |
| NEW + EXPIRED | Some existing MICs expired, new ones added | Merge after review |
| CHANGED only | Names, categories, or countries updated | Merge after review |
| Any + REMOVED | At least one MIC removed from the source | Requires human confirmation; D10 |

A "REMOVED > 0" event is the class most likely to break downstream
consumers. A consumer pinned to a MIC that no longer exists will fail
at the next registry load, which is the correct behavior — but it
needs a human to confirm the removal was intentional.

---

## Audit procedure

Every `iso10383.json` carries `meta.source_hash`, a `sha256:` digest of
the raw file the JSON was derived from. Six months from now, if
someone asks "did the October refresh actually run?", the hash answers
it.

### Verify a JSON against its source file

```bash
python3 -c "
import hashlib, json
from pathlib import Path
d = json.load(open('iso10383.json'))
h = 'sha256:' + hashlib.sha256(Path('raw/MIC_YYYYMMDD.csv').read_bytes()).hexdigest()
print('match' if h == d['meta']['source_hash'] else 'MISMATCH')
"
```

### Verify deterministic output

Two runs on the same raw file must produce byte-identical JSON.

```bash
python3 tools/fetch_swift_mic.py --raw raw/MIC_20260923.csv -o /tmp/a.json
python3 tools/fetch_swift_mic.py --raw raw/MIC_20260923.csv -o /tmp/b.json
diff /tmp/a.json /tmp/b.json && echo "deterministic"
```

Determinism rests on three rules:

- `json.dumps(..., sort_keys=True, ensure_ascii=False)` on write.
- Entries sorted by `mic` before serialization.
- LF line endings and a trailing newline.

### Verify the raw file is what SWIFT published

The `meta.source_url` in the registry points to the canonical SWIFT
URL. The `meta.source_hash` in the registry pins the exact bytes that
were parsed. If the file at the URL now differs from that hash, either
SWIFT republished the same snapshot (rare), or the URL is serving a
newer publication. The monthly refresh workflow handles both cases.

### Verify cross-registry consistency

```bash
python3 tools/gen_iso3166_snapshot.py
python3 tools/gen_exchange_calendar_snapshot.py
git diff --stat tools/iso3166_snapshot.json tools/exchange_calendar_snapshot.json
```

If either snapshot changes, the sibling registry has been updated and
this registry's cross-reference validation is now against a stale
snapshot. Regenerate, review, commit.

---

## Cross-registry snapshots

The registry cross-references two sibling registries. Both are
committed as snapshots, not fetched at runtime. The snapshots are the
interface.

| Snapshot | Source | Used for |
|----------|--------|----------|
| `tools/iso3166_snapshot.json` | `github.com/slimissa/iso3166` | Every `country_code` must be a valid alpha-2, except `ZZ` |
| `tools/exchange_calendar_snapshot.json` | `github.com/slimissa/exchange-calendar` | Every MIC referenced by Exchange Calendar must exist here |

Both snapshots are regenerated by scripts (`tools/gen_iso3166_snapshot.py`,
`tools/gen_exchange_calendar_snapshot.py`), committed, and verified by
CI.

### Known cross-registry gap

Three MICs referenced by the Exchange Calendar registry do not appear
in the 2026-09-23 ISO 10383 source file:

- `XBEK` (Beirut Stock Exchange)
- `XNBO` (Nairobi Securities Exchange)
- `XQSE` (Qatar Exchange)

Either they were removed from the source, or Exchange Calendar should
drop them. CI reports this as a **warning**, not a failure. This is
the advisory behavior of D6: cross-registry checks are advisory in
v1.0.0 and blocking in v1.0.1.

The three MICs are in an explicit allowlist at
`tools/validate.py::KNOWN_EXCHANGE_CALENDAR_GAPS`. Adding a MIC to
the allowlist requires an ADR amendment; see
[ADR 0007](./decisions/0007-cross-registry-allowlist.md).

Cross-registry checks are **blocking by default** in v1.0.1: any
MIC outside the allowlist that is referenced by Exchange Calendar
but absent from the registry fails the validator. Pass
`--advisory` to revert to the v1.0.0 behavior.

---

## Known gaps

The following are documented, deliberate limitations of v0.1.0. They
are tracked for future versions.

### Data coverage

- **LEI is stored but unused.** The `lei` field is populated from the
  source when present and is null otherwise. No MIC→LEI mapping file
  ships in v1.0.0. A companion `mic-lei-mapping.json` is planned for
  v1.1.0 (D11).
- **No MIC→BIC mapping.** Out of scope (D11). Planned for v1.2.0.
- **No MIC→ISIN relationship.** The relationship is many-to-many and
  belongs in an asset-identifiers context. Out of scope.
- **No trading currency per MIC.** Derived from `country_code` → ISO
  4217, not stored. Out of scope (D11).
- **No operating hours.** Out of scope (D11). Sourced better from the
  Exchange Calendar registry, which has per-exchange trading hours.
- **No regulatory status per venue.** Out of scope (D11).

### Source limitations

- **The source file is the only authority.** A MIC that appears in a
  national exchange's own publications but not in SWIFT's file is
  not in this registry. This is deliberate: the registry's value is
  that it traces to one source.
- **The source publishes monthly.** A venue that opens mid-month is
  not in the registry until the next publication. This is a
  limitation of the standard, not of this registry.
- **The source file's column set can change.** A new column means a
  schema change. The parser raises on unknown values; the schema
  rejects unknown properties. A new column will fail CI and require
  a deliberate code change.

### Hierarchy

- **Chains deeper than eight levels are refused.** The deepest chain
  in the 2026-09-23 snapshot is three levels. The cap is generous
  and unlikely to fire; if it does, it means the source has produced
  something unusual that warrants review.

### Distribution

- **Wrappers are not published to PyPI, npm, or crates.io** at
  v0.1.0. They install from the repository:
  `pip install -e wrappers/python`,
  `npm install ./wrappers/javascript`,
  `cargo add --path wrappers/rust`. The Go module resolves from git
  via its own tag. Publication is planned for v1.0.0.
- **No HTML or XML distribution.** The source file is available as
  XLSX and XML from SWIFT; this registry publishes JSON, SQL, CSV,
  TSV, and Parquet only. If XLSX or XML is needed, use SWIFT's
  original.

---

## Versioning

One version number, eight sites:

- `VERSION` (text file, the source of truth)
- `CHANGELOG.md` top released heading
- `iso10383.json` → `meta.version`
- `iso10383.parquet` footer → `iso10383.version`
- `wrappers/python/pyproject.toml` → `version`
- `wrappers/javascript/package.json` → `version`
- `wrappers/rust/Cargo.toml` → `version`
- `README.md` badge

`tools/check_version_consistency.py` reads every present site and fails
if any disagree. CI runs it on every push.

The registry follows Semantic Versioning:

- **Major** — breaking schema changes.
- **Minor** — new MICs, new optional fields, new tooling.
- **Patch** — data corrections.

Wrapper package versions track the registry version (D16).

---

## What this document does not cover

- **How to contribute a data correction.** See `CONTRIBUTING.md`.
- **The validator's layer-by-layer rules.** See the docstring in
  `tools/validate.py` and the `--help` output.
- **The decisions behind each architectural choice.** See
  `docs/decisions/v1.0.0-decisions.md`.
- **The verbatim source format as read on 2026-09-23.** See
  `docs/source_format.md`.

---

## Version history of this document

| Registry version | Change |
|-----------------|--------|
| 0.1.0 | Initial provenance document. |