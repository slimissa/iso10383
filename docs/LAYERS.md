# Layers — ISO 10383 MIC Registry

The registry is not one file. It is five layers of derived data,
each with a different authority, a different regeneration cost, and
a different guarantee. This document names them, explains what
belongs at each, and describes the validation that runs at every
boundary.

The point of the layering is simple: **only one layer is
irreplaceable, and it is not the one committed to git.** Everything
committed can be regenerated from the raw source file with a single
command. The raw source file is the only artifact that, once lost,
cannot be rebuilt from this repository alone.

---

## The five layers

| Layer | Name | Lives at | Committed | Authority |
|-------|------|----------|-----------|-----------|
| 0 | **Raw** | `raw/MIC_YYYYMMDD.csv` | No (gitignored) | The SWIFT-published file, byte-for-byte |
| 1 | **Curated** | `iso10383.json` | Yes | The registry. Single source of truth for every downstream layer. |
| 2 | **Derived** | Nine files at repo root (SQL, CSV, TSV, Parquet) | Yes | Mechanical projections of Layer 1. No independent information. |
| 3 | **Bundled** | `wrappers/*/…/iso10383.json` | Yes | Byte-identical copies of Layer 1, four times over. |
| 4 | **Cross-referenced** | `tools/*_snapshot.json` | Yes | Committed snapshots of sibling registries. Used only for validation. |

Every committed file traces to Layer 0 through Layer 1. No file
committed to this repository contains information that is not in the
raw SWIFT file or in a committed sibling snapshot.

---

## Layer 0 — Raw

**Path:** `raw/MIC_YYYYMMDD.csv`

**Committed:** No. `.gitignore` excludes `raw/`.

**Authority:** Absolute. This is what SWIFT published. The registry
does not edit, extend, or annotate it.

### What belongs here

- The CSV downloaded from
  `https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv`,
  saved with the download date in the filename.

### What does not belong here

- Any file that has been transformed. Transformation is Layer 1.
- Any file that has been manually edited. The raw file is a
  byte-for-byte copy of what SWIFT's server returned.
- Historical raw files from previous months. Only the current
  snapshot is kept locally. Previous snapshots are recoverable from
  SWIFT's own archive if needed; this repository does not preserve
  them.

### Why it is not committed

Two reasons:

1. **Size.** The raw file is ~590 KB. Committing a new one every
   month would add ~7 MB per year to the repository for no benefit,
   since the derived registry captures everything downstream
   consumers need.
2. **Licensing.** SWIFT's terms permit use of the file. They do not
   necessarily permit redistribution in the original form. The
   derived registry is a transformative use; the raw copy is not.
   Keeping the raw file gitignored sidesteps the question.

### How it is produced

By hand, or by the fetcher:

```bash
python3 tools/fetch_swift_mic.py --download --force
```

The download is the **only** network step in the entire build. Every
other layer is produced from this file, offline.

### How it is verified

The registry does not verify Layer 0. Layer 0 verifies the registry.
Every `iso10383.json` carries `meta.source_hash`, a `sha256:` digest
of the raw file it was parsed from. Regenerate the digest and compare:

```bash
python3 -c "
import hashlib, json
from pathlib import Path
d = json.load(open('iso10383.json'))
h = 'sha256:' + hashlib.sha256(Path('raw/MIC_YYYYMMDD.csv').read_bytes()).hexdigest()
print('match' if h == d['meta']['source_hash'] else 'MISMATCH')
"
```

If the hash does not match, either the wrong raw file is being
compared or the registry was generated from a different one. Both
are Layer 1 errors, not Layer 0 errors.

---

## Layer 1 — Curated

**Path:** `iso10383.json`

**Committed:** Yes. This is the registry.

**Authority:** The single source of truth for Layers 2, 3, and every
downstream consumer.

### What belongs here

- The parsed, validated, canonical representation of Layer 0.
- Every field from the source file, mapped to a named JSON key.
- Metadata: version, updated, source snapshot, source URL, source
  hash, counts, broken chains.

### What does not belong here

- Any value not present in Layer 0.
- Any transformation of a value beyond:
  - `OPRT`/`SGMT` → `OPERATING`/`SEGMENT` (derived field, D3, D5)
  - `YYYYMMDD` → `YYYY-MM-DD` (date format)
  - Empty string → `null` (JSON convention)
  - Whitespace stripping
- Any validation of a value against a sibling registry. That is
  Layer 4's job.
- Any hand-written commentary. The `note` field is copied verbatim
  from the source's `COMMENTS` column.

### How it is produced

By `tools/fetch_swift_mic.py`:

```bash
python3 tools/fetch_swift_mic.py --raw raw/MIC_20260923.csv --snapshot-date 2026-09-23
```

The fetcher's contract:

1. **Parse strictly.** A malformed row raises. A missing required
   column raises. An unknown value in a closed enum raises.
2. **Resolve every parent chain.** Every segment's `operating_mic`
   is followed upward until an operating MIC is reached. Chains
   deeper than eight levels, cycles, and missing parents are
   recorded in `meta.broken_chains` and do not abort the parse.
3. **Emit deterministically.** `json.dumps(..., indent=2,
   sort_keys=True, ensure_ascii=False)`, entries sorted by `mic`,
   LF line endings, trailing newline.

Two runs on the same raw file produce byte-identical output. This is
what makes every downstream `--check` mode meaningful: if Layer 1 is
deterministic, every layer above it must also be.

### The determinism guarantee, precisely

Byte-identical output rests on four decisions:

| Decision | Enforced by |
|----------|-------------|
| Sorted keys at every level | `sort_keys=True` |
| Stable entry order | `sorted(entries, key=lambda e: e["mic"])` |
| LF line endings | `open(..., newline="")` on the raw parse; `write_text` with LF |
| No locale-dependent formatting | No `strptime` with locale, no `%c`, no thousand separators |

A change to any of the four is a Layer 1 change and requires a
rationale in the decisions register.

### How it is validated

Six independent layers, run by `tools/validate.py`:

| Layer | What it checks | Authority |
|-------|----------------|-----------|
| Schema | JSON Schema draft-07, `additionalProperties: false` at every level, closed enums | `schema.json` |
| Integrity | MIC patterns, country patterns, ISO 8601 dates, non-empty strings | `tools/validate.py` |
| Business | MIC uniqueness, self-reference rules for operating MICs, non-self-reference for segments, expired entries have `expiration_date` | `tools/validate.py` |
| Cross-reference | Every parent chain terminates at an operating MIC. Every `country_code` exists in the ISO 3166 snapshot (advisory). | `tools/validate.py` |
| Ground truth | `XNYS`, `XLON`, `XTKS`, `XPAR` spot checks | `tools/validate.py` |
| Coverage | Operating ≥ 1500, segment ≥ 1000, total ≥ 2500 | `tools/validate.py` |

Exit codes: 0 pass (warnings allowed), 1 data error, 2 usage error,
3 schema violation or malformed JSON. `--strict` promotes
cross-registry warnings to errors.

### How it is refreshed

Monthly, from a new Layer 0. The diff policy is documented in
`docs/PROVENANCE.md` § Refresh cadence. `REMOVED > 0` fails the
refresh until a human confirms (D10).

### What makes it irreplaceable

Nothing. Layer 1 is a deterministic function of Layer 0 plus the
fetcher's code. As long as `raw/MIC_YYYYMMDD.csv` is available,
`iso10383.json` can be regenerated in under a second.

The reason it is committed is convenience: every downstream consumer
reads it directly, and committing it means the repository is useful
without running any code.

---

## Layer 2 — Derived

**Paths:** nine files at repo root.

```
iso10383.sql                 ANSI SQL-92
iso10383.postgresql.sql      PostgreSQL 12+
iso10383.mysql.sql           MySQL 8+ / MariaDB 10.4+
iso10383.sqlite.sql          SQLite 3.37+
iso10383.csv                 RFC 4180, UTF-8
iso10383.excel.csv           UTF-8 BOM for Windows Excel
iso10383.european.csv        Semicolon-delimited
iso10383.tsv                 Tab-separated
iso10383.parquet             Typed, columnar
```

**Committed:** Yes. All nine.

**Authority:** None. Every file is a mechanical projection of Layer 1.
No file contains a value that is not in Layer 1.

### What belongs here

- Format translations of the same data: text, columns, types.
- Nothing else.

### What does not belong here

- Any new field.
- Any joined data from a sibling registry.
- Any computed value.
- Any commentary. The SQL files carry a header comment with the
  registry version and source snapshot; that comment is metadata,
  not data.

### How they are produced

Four tools, one per family:

| Family | Tool | Output |
|--------|------|--------|
| SQL | `tools/export_sql.py` | `iso10383.sql`, `.postgresql.sql`, `.mysql.sql`, `.sqlite.sql` |
| CSV / TSV | `tools/export_csv.py` | `iso10383.csv`, `.excel.csv`, `.european.csv`, `.tsv` |
| Parquet | `tools/export_parquet.py` | `iso10383.parquet` |
| (Metadata) | `tools/export_columns.py` | Column order, single source |

Column order is defined once, in `tools/export_columns.py`. All four
CSV variants and the Parquet file use `CSV_COLUMNS`; the SQL exports
use `SQL_COLUMNS`. The two tuples share a prefix: `SQL_COLUMNS` is
the FK-ready minimum; `CSV_COLUMNS` adds the human-analysis fields.

### The idempotency contract

Every SQL file is safe to run twice. Each dialect uses its own
mechanism:

| Dialect | Idempotency |
|---------|-------------|
| PostgreSQL | `INSERT ... ON CONFLICT (mic) DO NOTHING` |
| MySQL | `INSERT IGNORE` |
| SQLite | `INSERT OR IGNORE` |
| ANSI | `INSERT ... ON CONFLICT DO NOTHING` (documented; the consumer's engine determines support) |

The two tables in the SQL exports:

- `mics` — one row per MIC. `mic` primary key. `operating_mic`
  self-referencing foreign key with `NOT NULL`. `status` and
  `mic_type` are `CHECK`-constrained. `market_category` is
  `CHECK`-constrained against the 16-code enum.
- `market_categories` — a lookup table for the 16 four-letter codes
  and their human-readable labels.

The `market_categories` labels are the one place in the entire
project where a value is written by hand. They are read from a
Python literal in `tools/export_sql.py`. If ISO ever renames a
category code, the label changes in one file and every SQL export
follows. The labels are not part of the registry.

### How they are validated

Each family has a `--check` mode that regenerates the file in
memory and compares it to the committed artifact:

```bash
python3 tools/export_sql.py --check
python3 tools/export_csv.py --check
python3 tools/export_parquet.py --check
```

If any committed file is stale — different from what a fresh build
would produce — the tool exits 1 and names the file. CI runs all
three on every push.

### The Parquet exception

Parquet embeds a writer timestamp in the file, so byte comparison is
not stable across runs. `export_parquet.py --check` does not compare
bytes. It compares the two things that matter:

1. The four footer keys: `iso10383.version`, `iso10383.updated`,
   `iso10383.source_snapshot`, `iso10383.source_hash`.
2. The row count.

If both match, the Parquet file is considered current. The test
suite (`tests/test_export_parquet.py`) additionally verifies that
the typed columns are the expected types — `date32` for the four
date fields, dictionary-encoded for `mic_type`, `status`,
`country_code`, `market_category`.

### What makes them regenerable

Every Layer 2 file is a pure function of Layer 1. Nothing is
hand-authored. The only manual text is the header comment in each
SQL file and the category labels in `tools/export_sql.py`. Everything
else is data from Layer 1.

If a Layer 2 file is lost:

```bash
python3 tools/export_sql.py
python3 tools/export_csv.py
python3 tools/export_parquet.py
```

That is the entire recovery procedure.

---

## Layer 3 — Bundled

**Paths:** four byte-identical copies of Layer 1.

```
wrappers/python/src/iso10383/data/iso10383.json
wrappers/javascript/src/data/iso10383.json
wrappers/rust/data/iso10383.json
wrappers/go/data/iso10383.json
```

**Committed:** Yes. All four.

**Authority:** None. Each is a copy of Layer 1.

### Why they exist

Each wrapper package must be installable and usable without the
repository. `pip install iso10383-registry`, `npm install
iso10383-registry`, `cargo add iso10383-registry`, and `go get` all
produce a working registry with no runtime file dependency. The
snapshot ships inside the package.

This is D15: wrappers bundle the registry.

### How they are produced

By `tools/sync_wrappers.py`:

```bash
python3 tools/sync_wrappers.py
```

The tool copies Layer 1 to each of the four destinations.

### How they are validated

`tools/sync_wrappers.py --check` compares each bundle to Layer 1:

```bash
python3 tools/sync_wrappers.py --check
```

Expected output:

```
OK: 4 wrapper copies in sync
```

If any copy has drifted, the tool prints `stale: <path>` and exits 1.
Missing targets print `missing: <path>` and are noted but do not
fail while wrappers are still being built. In CI (Phase 7), missing
targets are a hard failure.

`tests/test_wrappers.py::test_all_bundles_byte_identical` performs
the same check from the test suite.

### Why they must be byte-identical

Four reasons:

1. **Consumer trust.** A user who loads the Go wrapper and the
   Python wrapper on the same day must see the same MICs. Byte
   identity is the strongest form of that guarantee.
2. **Cross-language tests.** The shared contract fixture is a
   single JSON file. If the four bundles differ, the same test
   case would produce different answers in different languages.
   Byte identity is what makes the cross-language check meaningful.
3. **Version consistency.** All four wrappers declare the same
   package version (D16). The bundled JSON carries `meta.version`.
   If they disagree, `check_version_consistency.py` fails.
4. **Audit.** A downstream consumer who finds an error in the
   Python bundle can check the Go bundle and know it has the same
   error. Copy drift would make debugging a game of whack-a-mole.

### How to update them

Never by hand. `sync_wrappers.py` is the only supported path. Any
manual edit will be detected and reverted by the next `--check`.

---

## Layer 4 — Cross-referenced

**Paths:** two snapshots.

```
tools/iso3166_snapshot.json
tools/exchange_calendar_snapshot.json
```

**Committed:** Yes.

**Authority:** None for the registry's own data. Layer 4 does not
contribute fields to Layer 1. It is validation input, not data.

### What belongs here

- The set of country codes from the ISO 3166 registry, reduced to
  what this registry needs for cross-reference: `alpha_2` codes.
- The set of MICs referenced by the Exchange Calendar registry,
  reduced to a plain list.

Nothing else. The snapshots are intentionally narrow.

### What does not belong here

- Full copies of sibling registries. A snapshot is a projection,
  not a mirror.
- Any field this registry does not read.

### How they are produced

By two scripts:

```bash
python3 tools/gen_iso3166_snapshot.py
python3 tools/gen_exchange_calendar_snapshot.py
```

Each fetches the sibling registry from GitHub, reduces it to the
minimal set this registry needs, and writes a small JSON file with
the source URL, source version, count, and set.

The outputs are committed. A consumer never needs network access to
run validation — the snapshot is on disk.

### How they are validated

Used by the validator's cross-reference layer:

| Snapshot | Rule |
|----------|------|
| ISO 3166 | Every `country_code` in the registry is either a valid alpha-2 or the placeholder `ZZ` |
| Exchange Calendar | Every MIC referenced by Exchange Calendar exists in this registry |

Both rules are **advisory in v1.0.0** and blocking in v1.0.1 (D6).
The validator prints warnings to stderr and exits 0 unless `--strict`
is passed.

### The bidirectional pattern

This is the first pair in the ecosystem where each side verifies the
other:

- This registry reads an ISO 3166 snapshot.
- The ISO 3166 registry reads an ISO 4217 snapshot.
- Exchange Calendar reads this registry's MICs.

Every arrow is a committed snapshot. No repository is a runtime
dependency of any other. The snapshots are the interface.

### The known gap

Three MICs referenced by Exchange Calendar do not exist in this
registry's Layer 1:

- `XBEK` (Beirut Stock Exchange)
- `XNBO` (Nairobi Securities Exchange)
- `XQSE` (Qatar Exchange)

The validator reports this as a warning. It is documented in
`docs/PROVENANCE.md` § Cross-registry snapshots.

The gap exists because the two registries measure different things:
Exchange Calendar covers exchanges that operate (74 of them), while
ISO 10383 covers exchanges that SWIFT has assigned a MIC to. The
three above were either removed from SWIFT's file or never had one.

This is not a bug. It is a finding. Documenting it is what makes the
advisory check useful.

---

## The regeneration DAG

The layers form a directed acyclic graph. Arrows point from a
prerequisite to a dependent artifact.

```
             ┌───────────────────────┐
             │  Layer 0  raw/MIC.csv │
             └───────────┬───────────┘
                         │ fetch_swift_mic.py
                         ▼
             ┌───────────────────────┐
             │  Layer 1  iso10383.json│
             └───────────┬───────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
 ┌──────────┐    ┌──────────────┐   ┌────────────┐
 │ Layer 2  │    │  Layer 3     │   │ Wrappers'  │
 │ 9 files  │    │  4 bundles   │   │  tests     │
 └──────────┘    └──────────────┘   └────────────┘
        ▲                ▲                ▲
        │                │                │
        │         sync_wrappers.py        │
        │                                 │
   export_*.py                            │
                                          │
                            ┌─────────────┴────────────┐
                            │                          │
                            ▼                          ▼
                    ┌──────────────┐          ┌──────────────┐
                    │  Layer 4     │          │  test        │
                    │  2 snapshots │          │  suites      │
                    └──────────────┘          └──────────────┘
                            ▲
                            │
                   gen_*_snapshot.py
                            │
                            ▼
                    ┌──────────────┐
                    │  Sibling     │
                    │  registries  │
                    └──────────────┘
```

Nothing downstream of Layer 1 can produce a value that is not in
Layer 1. Nothing in Layer 4 feeds back into Layers 2 or 3.

---

## What is irreplaceable, and what is not

| Artifact | Layer | Regenerable from | Irreplaceable? |
|----------|-------|------------------|----------------|
| `raw/MIC_YYYYMMDD.csv` | 0 | SWIFT's server, only while the same month's file is published | Yes, after ~6–12 months |
| `iso10383.json` | 1 | Layer 0 + `fetch_swift_mic.py` | No |
| `iso10383.sql` (×4) | 2 | Layer 1 + `export_sql.py` | No |
| `iso10383.csv` (×4) | 2 | Layer 1 + `export_csv.py` | No |
| `iso10383.parquet` | 2 | Layer 1 + `export_parquet.py` | No |
| Wrapper bundles (×4) | 3 | Layer 1 + `sync_wrappers.py` | No |
| Cross-registry snapshots (×2) | 4 | Sibling registries + `gen_*_snapshot.py` | No |

The one artifact worth preserving outside the repository is Layer 0.
SWIFT publishes a new file each month and does not maintain an
archive of previous snapshots on the same URL. Once the next
publication replaces the current one, the previous raw file is no
longer available from SWIFT.

If the exact state of the registry on 2026-09-23 ever needs to be
reproduced bit-for-bit, only `raw/MIC_20260923.csv` and the current
`tools/fetch_swift_mic.py` are required. The committed Layer 1 is a
convenience, not the record.

**Back up `raw/`.** It is not in git.

---

## Validation boundaries

Validation runs at three boundaries. Each has a different scope,
a different failure mode, and a different fix.

### Boundary A — Layer 0 → Layer 1

**What is validated:** the shape of the raw file.

**How:** implicit in `tools/fetch_swift_mic.py`'s parser.

**Failure mode:** a `ValueError` naming the row and the offending
value. The registry is not written.

**Examples:**

- Unknown `OPRT/SGMT` value.
- Operating MIC that does not self-reference.
- Segment MIC that self-references.
- Malformed date.
- Unknown status value.
- Missing required column.

**Fix:** the source has changed in a way the parser does not know
about. Update the value maps, re-run, commit.

### Boundary B — Layer 1 → Layers 2 and 3

**What is validated:** the artifact is a faithful projection of
Layer 1.

**How:** `--check` mode on each exporter, plus `sync_wrappers.py
--check`.

**Failure mode:** the tool prints `stale: <path>` and exits 1.

**Fix:** regenerate.

```bash
python3 tools/export_sql.py
python3 tools/export_csv.py
python3 tools/export_parquet.py
python3 tools/sync_wrappers.py
```

### Boundary C — Layer 1 → Layer 4

**What is validated:** the registry against sibling registries.

**How:** `tools/validate.py` layer 4.

**Failure mode:** warnings on stderr. Exit 0 unless `--strict`.

**Examples:**

- A `country_code` not in the ISO 3166 snapshot (except `ZZ`).
- A MIC in the Exchange Calendar snapshot not in this registry.

**Fix:** either regenerate the snapshot from the sibling, or
investigate the mismatch. Some mismatches are real findings, not
bugs.

### Boundary D — everything → consumers

**What is validated:** the registry's total integrity, from the
consumer's point of view.

**How:** `tools/validate.py` (all six layers) plus the test suite.

**Failure mode:** non-zero exit.

**Fix:** depends on the layer that failed. The validator names the
layer in the message.

---

## CI gates, by layer

Every CI job maps to a layer.

| Job | Layer | Command | Fails on |
|-----|-------|---------|----------|
| `validate-json` | 1 | `tools/validate.py` | Data error, schema violation |
| `validate-json` | 1 | `tools/check_snapshot_freshness.py` | `source_snapshot` older than 60 days |
| `validate-json` | 1 | `tools/check_version_consistency.py` | Any of eight version sites disagree |
| `check-exports` | 2 | `export_*.py --check` (×3) | Stale artifact |
| `check-exports` | 3 | `sync_wrappers.py --check` | Bundle drift |
| `check-cli` | 1 | `iso10383_cli.py check` | Registry invariants |
| `check-wrappers` | 3 | each wrapper's test suite | Any wrapper fails |
| `check-cross-language` | 3 | `tools/check_cross_language.sh` | Wrappers disagree |

Layer 0 is not gated in CI. It is a network artifact. Layer 4 is
advisory and does not fail CI in v1.0.0.

---

## Adding a new derived artifact

If a new Layer 2 file is needed — say, an XML export — the process
is:

1. **Add a tool.** `tools/export_xml.py`. It reads Layer 1, writes
   the artifact, and supports `--check`.
2. **Register the column order.** If it uses a new set of columns,
   add a tuple to `tools/export_columns.py`. Reuse `SQL_COLUMNS` or
   `CSV_COLUMNS` if the shape matches.
3. **Add a test.** `tests/test_export_xml.py`. Follow the pattern of
   `test_export_csv.py`.
4. **Add a CI job.** `.github/workflows/validate.yml`, in the
   `check-exports` group. One line: `python3 tools/export_xml.py
   --check`.
5. **Regenerate and commit.** The artifact joins the nine at repo
   root.
6. **Document.** Add the format to `docs/LAYERS.md` § Layer 2, and
   to the README's Quick Start if it is a first-class consumption
   path.

The tool is the contract. The artifact is disposable.

---

## Adding a new cross-reference

If a new sibling registry joins the ecosystem, and this registry
must validate against it:

1. **Add a generator.** `tools/gen_<sibling>_snapshot.py`. It reads
   the sibling, reduces it to the fields this registry needs, and
   writes `tools/<sibling>_snapshot.json` with source URL, version,
   count, and set.
2. **Commit the snapshot.**
3. **Add a validator rule.** In `tools/validate.py`'s
   cross-reference layer, read the snapshot and check the relevant
   field.
4. **Classify the rule.** Advisory or blocking. In v1.0.0, every
   cross-registry rule is advisory (D6). In v1.0.1, promote the
   mature ones to blocking.
5. **Document the boundary.** `docs/LAYERS.md` § Layer 4, and
   `docs/PROVENANCE.md` § Cross-registry snapshots.
6. **Document the gap.** If the sibling has entries this registry
   does not, list them explicitly. A silent gap is worse than a
   named one.

The snapshot is the interface. The generator is the contract.

---

## The one rule

**Never hand-edit a committed artifact.**

Every committed file except the root README, `CHANGELOG.md`, the
docs, the tools, and the tests is generated. `iso10383.json` is
generated from `raw/`. The nine Layer 2 files are generated from
`iso10383.json`. The four bundles are copied from `iso10383.json`.
The two snapshots are generated from sibling registries.

`--check` modes will detect any hand edit and revert it on the next
regeneration. CI will fail on the push.

If a value in a committed artifact is wrong, the fix is:

1. Fix the tool that generates it.
2. Regenerate.
3. Commit both the tool change and the regenerated artifact in one
   commit.

This is the same rule the sibling registries follow. It is what
makes the layering meaningful: every committed file traces to a
decision in a tool, and every tool traces to a decision in the
register.

---

## Known subtleties

**CSV row count vs. JSON entry count.** Both equal 2,883 on the
current snapshot. They will continue to match because the CSV
exporter emits one row per JSON entry. If a future source file
contains a duplicate `mic`, the fetcher raises before producing
Layer 1. Duplicates never reach Layer 2.

**Parquet's non-determinism.** Parquet embeds a writer timestamp, so
`export_parquet.py --check` compares schema metadata and row count,
not bytes. The typed column set is the contract; the file bytes are
not.

**The `excel.csv` BOM.** `iso10383.excel.csv` begins with the three
UTF-8 BOM bytes `EF BB BF`. The other three CSV/TSV files do not.
`test_export_csv.py::test_excel_csv_has_bom` enforces this.

**The `european.csv` delimiter.** Semicolon, not comma. The other
three use comma (or tab for TSV). This matters for European Excel
locales where comma is the decimal separator.

**No BOM anywhere else.** `iso10383.json`, the SQL files, the
Parquet file, the TSV, and the regular CSV all start with their
first real byte. No BOM. No comment header in the CSVs.

**LF line endings everywhere.** `.gitattributes` enforces this on
checkout. A file with CRLF endings would fail every `--check` mode.

**The `ZZ` country code.** `ZZ` is not an ISO 3166 alpha-2 code. It
is ISO 10383's placeholder for "no fixed country." Three MICs in the
current snapshot carry it. The validator treats it as a known
non-ISO value and does not flag it.

**The `ARMS` and `CTPS` market categories.** The Release 2.0
factsheet defines 16 codes. The 2026-09-23 snapshot uses 14. `ARMS`
and `CTPS` are in the schema's enum but not in the data. If SWIFT
assigns them next month, the schema does not need to change; the
next refresh will include them.

**The 8 three-level parent chains.** `XEAS → XEQT → XBER` is one.
Seven others exist. The schema models parent chains of any depth;
the fetcher resolves them; the validator confirms each terminates
at an operating MIC.

---

## Version history of this document

| Registry version | Change |
|-----------------|--------|
| 0.1.0 | Initial layer document. |