# ISO 10383 MIC Registry

**A canonical, versioned, machine-readable registry of ISO 10383 Market Identifier Codes: 2,883 MICs (1,594 operating, 1,289 segment) with their parent chains, status, country, category and operator.**

One JSON file is the source of truth. Everything else (SQL, CSV, TSV, Parquet, four language wrappers, a command-line tool, two vendored cross-registry snapshots) is regenerated from it or checked against it, and re-verified on every push.

[![Validate](https://github.com/slimissa/iso10383/actions/workflows/validate.yml/badge.svg)](https://github.com/slimissa/iso10383/actions/workflows/validate.yml)
[![Refresh](https://github.com/slimissa/iso10383/actions/workflows/refresh.yml/badge.svg)](https://github.com/slimissa/iso10383/actions/workflows/refresh.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Schema](https://img.shields.io/badge/schema-1.0.0-green.svg)](./schema.json)
[![Registry](https://img.shields.io/badge/registry-1.0.4-orange.svg)](./CHANGELOG.md)
[![MICs](https://img.shields.io/badge/MICs-2883-blue.svg)](./iso10383.json)
[![Wrappers](https://img.shields.io/badge/wrappers-4-purple.svg)](./wrappers/)
[![Tests](https://img.shields.io/badge/tests-222-success.svg)](./tests/)

---

## Contents

1. [At a glance](#at-a-glance)
2. [Why this exists](#why-this-exists)
3. [Where to start](#where-to-start)
4. [Quick start](#quick-start)
5. [The data model: five layers](#the-data-model-five-layers)
6. [The registry file](#the-registry-file)
7. [Flat exports: SQL, CSV, TSV, Parquet](#flat-exports-sql-csv-tsv-parquet)
8. [Bundled copies and vendored snapshots](#bundled-copies-and-vendored-snapshots)
9. [Worked example: a venue tree in ten commands](#worked-example-a-venue-tree-in-ten-commands)
10. [Command-line interface](#command-line-interface)
11. [Language wrappers](#language-wrappers)
12. [Validation](#validation)
13. [Continuous integration](#continuous-integration)
14. [Refreshing the data](#refreshing-the-data)
15. [Release pipeline](#release-pipeline)
16. [Versioning](#versioning)
17. [Project structure](#project-structure)
18. [Documentation index](#documentation-index)
19. [Contributing](#contributing)
20. [Known limitations](#known-limitations)
21. [FAQ](#faq)
22. [Consumed by](#consumed-by)
23. [License and author](#license-and-author)
24. [What's next](#whats-next)

---

## At a glance

| | |
|---|---|
| **MICs** | 2,883: 1,594 operating, 1,289 segment |
| **Status** | 2,296 `ACTIVE`, 21 `UPDATED`, 566 `EXPIRED` |
| **Hierarchy** | Every segment's parent chain ends at an operating MIC. 1,281 segments sit directly under an operating MIC, 8 sit two levels down. 0 broken chains. |
| **Countries** | 149 distinct `country_code` values: 148 ISO 3166-1 alpha-2 codes plus `ZZ` (3 MICs: `BILT`, `XOFF`, `XXXX`) |
| **Market categories** | 14 of the 16 ISO codes are in use (`ARMS` and `CTPS` are defined, unassigned) |
| **Source** | SWIFT's published `ISO10383_MIC.csv`, snapshot 2026-09-23, `sha256:79de0f77...` recorded in `meta.source_hash` |
| **Source of truth** | [`iso10383.json`](./iso10383.json), validated against [`schema.json`](./schema.json) (version 1.0.0) |
| **Layers** | Five: Raw, Curated, Derived, Bundled, Cross-referenced ([`docs/LAYERS.md`](./docs/LAYERS.md)) |
| **Export formats** | 9 derived files: SQL (4 dialects), CSV/TSV (4 variants), Parquet (1 file) |
| **Wrappers** | Python, JavaScript, Rust, Go, each bundling a byte-identical copy of the JSON |
| **CLI** | `tools/iso10383_cli.py`, nine subcommands, five output modes; needs a checkout, no wrapper installs it |
| **Vendored snapshots** | 2: ISO 3166 (252 codes, v1.6.9) and Exchange Calendar (74 MICs, v2.15.4) |
| **Validation** | Six validator layers, 17 release-gate checks, 147 manifest claims, 222 tests |
| **CI** | Two workflows: `validate.yml` (seven jobs) and `refresh.yml` (monthly) |
| **Version** | 1.0.4, one version number at nine sites |
| **Dependencies** | The JSON needs none. Python, JavaScript and Go wrappers have none. The Rust wrapper depends on `serde` and `serde_json`. Build time: `jsonschema`, `pyarrow==25.0.1`, `pytest`. |
| **License** | Apache 2.0 |

---

## Why this exists

Every trading system, quant library and fintech app maintains its own MIC list, and the lists drift. Some keep expired codes and some drop them. Some flatten the operating-versus-segment hierarchy, and some assume every segment hangs directly off an operating MIC, when in this data eight segments hang off another segment.

**A MIC is the join key that financial data uses to say "where".** An instrument trades on a MIC, a quote comes from a MIC, a filing references a MIC, and an exchange calendar is keyed by one. The argument of this registry is that venue identity is a **join dimension**: every fact table needs it and none should own it. A fact table that carries only a MIC inherits country, category, operator, parent venue and expiry from one versioned file instead of copying them, and a change in SWIFT's monthly publication reaches every consumer through a version bump rather than through a hundred hand-edited lists.

One versioned, schema-validated JSON file, guarded by CI, replaces the lists. The JSON is the contract; the SQL, CSV, Parquet, wrapper and CLI forms are ways to consume it without writing a parser. The registry deliberately stays narrow: it reproduces SWIFT's file and nothing else (see [Known limitations](#known-limitations)).

---

## Where to start

| If you are... | Start with |
|---------------|------------|
| A programmer who wants a library | [Language wrappers](#language-wrappers) |
| A database engineer | [`iso10383.postgresql.sql`](./iso10383.postgresql.sql) and the other dialects; see [SQL](#sql) |
| An analyst in Excel, Sheets, pandas or DuckDB | [`iso10383.csv`](./iso10383.csv) or [`iso10383.parquet`](./iso10383.parquet); see [CSV and TSV](#csv-and-tsv) and [Parquet](#parquet) |
| A shell user | [Command-line interface](#command-line-interface) |
| Asking "which venues sit under this operator?" | `iso10383 segments XJPX` and the [worked example](#worked-example-a-venue-tree-in-ten-commands) |
| Evaluating whether to trust the data | [`docs/PROVENANCE.md`](./docs/PROVENANCE.md), [Validation](#validation) and [Known limitations](#known-limitations) |
| Running the monthly refresh | [Refreshing the data](#refreshing-the-data) |
| Cutting a release | [Release pipeline](#release-pipeline) and [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) |
| Contributing a correction or a tool change | [Contributing](#contributing) and [`CONTRIBUTING.md`](./CONTRIBUTING.md) |
| Joining MICs from another registry | [`docs/JOINS.md`](./docs/JOINS.md) and [Consumed by](#consumed-by) |

---

## Quick start

Nothing here is published to PyPI, npm, crates.io or a Go proxy. Every path below starts from a clone:

```bash
git clone https://github.com/slimissa/iso10383.git
cd iso10383
```

### Direct download

```bash
curl -O https://raw.githubusercontent.com/slimissa/iso10383/main/iso10383.json
```

For anything reproducible, pin a release tag instead of `main`. Tags are immutable ([ADR 0005](./docs/decisions/0005-tag-discipline.md)); the versions are listed in [`CHANGELOG.md`](./CHANGELOG.md).

### Python (3.9+)

```bash
pip install -e wrappers/python
```

```python
from iso10383 import MICRegistry

reg = MICRegistry()                          # bundled snapshot
xnys = reg.by_mic("XNYS")
print(xnys.mic_type, xnys.country_code)      # OPERATING US

print([s.mic for s in reg.segments("XJPX")][:3])   # ['XJAS', 'XOSE', 'XOSJ']
print(reg.operating_mic("XTKS"))             # XJPX
print(len(reg.expired(since="2024-01-01")))  # 82
```

### JavaScript (Node 18+)

```javascript
const { MICRegistry } = require("./wrappers/javascript");

const reg = new MICRegistry();
const xnys = reg.byMic("XNYS");
console.log(xnys.mic_type, xnys.country_code);  // OPERATING US
console.log(reg.operatingMic("XTKS"));          // XJPX
console.log(reg.segments("XJPX").length);       // 9
```

### Rust (edition 2021)

```toml
[dependencies]
iso10383-registry = { path = "wrappers/rust" }
```

```rust
use iso10383_registry::Registry;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let reg = Registry::load()?;
    let xnys = reg.by_mic("XNYS").unwrap();
    println!("{} {}", xnys.mic_type, xnys.country_code.as_deref().unwrap_or(""));
    println!("{:?}", reg.operating_mic("XTKS"));  // Some("XJPX")
    Ok(())
}
```

### Go (1.21+)

The module path is `github.com/slimissa/iso10383/wrappers/go`. From a clone, point a `replace` directive at the directory:

```go
// go.mod:
//   require github.com/slimissa/iso10383/wrappers/go v0.0.0
//   replace github.com/slimissa/iso10383/wrappers/go => ../iso10383/wrappers/go
import (
    "fmt"
    iso10383 "github.com/slimissa/iso10383/wrappers/go"
)

reg, _ := iso10383.LoadRegistry()
xnys := reg.ByMIC("XNYS")
fmt.Println(xnys.MICType, *xnys.CountryCode)  // OPERATING US
fmt.Println(reg.OperatingMIC("XTKS"))         // XJPX
```

### Any SQL database

```bash
psql -f iso10383.postgresql.sql              # PostgreSQL 12+
mysql < iso10383.mysql.sql                   # MySQL 8+ / MariaDB 10.4+
sqlite3 registry.db < iso10383.sqlite.sql    # SQLite 3.37+
psql -f iso10383.sql                         # generic dialect (PostgreSQL or SQLite)
```

### pandas

```python
import pandas as pd
df = pd.read_parquet("iso10383.parquet")
```

---

## The data model: five layers

The registry is not one file. It is five layers, each with a different authority, a different regeneration cost and a different guarantee. [`docs/LAYERS.md`](./docs/LAYERS.md) is the full model.

| Layer | Name | Lives at | Committed | Authority |
|-------|------|----------|-----------|-----------|
| 0 | **Raw** | `raw/MIC_YYYYMMDD.csv` | No (gitignored) | SWIFT's published file, byte for byte. Only the current snapshot is kept. |
| 1 | **Curated** | [`iso10383.json`](./iso10383.json) | Yes | The registry. Single source of truth for every layer below. |
| 2 | **Derived** | Nine files at the repo root | Yes | Mechanical projections of Layer 1: 4 SQL, 4 CSV/TSV, 1 Parquet |
| 3 | **Bundled** | `wrappers/*/.../iso10383.json` | Yes | Four byte-identical copies of Layer 1 |
| 4 | **Cross-referenced** | `tools/*_snapshot.json` | Yes | Committed snapshots of two sibling registries, used only for validation |

**The rule that governs the layers:** a layer may only assume what the layer below it guarantees, and nothing downstream of Layer 1 can contain a value that is not in Layer 1. Nothing in Layer 4 feeds back into Layers 2 or 3.

**Where the rule is enforced by a tool, not by convention:**

- **Layer 0 to 1.** `tools/fetch_swift_mic.py` is the only tool that reads `raw/`. Its parser raises on an unknown `OPRT/SGMT` or status value, an operating MIC that does not self-reference, a segment that does, a malformed date, or a missing column, and it writes nothing when it raises.
- **Layer 1 to 2.** Each exporter has a `--check` mode that regenerates in memory and compares with the committed file. `export_parquet.py --check` compares bytes.
- **Layer 1 to 3.** `tools/sync_wrappers.py --check` compares the four bundled copies with `iso10383.json`.
- **Layer 1 to 4.** `tools/validate.py` reads the two snapshots (and no sibling repository) at validation time; `gen_*_snapshot.py --check` reproduces each snapshot from its pinned upstream tag.

Only Layer 0 cannot be regenerated from this repository. **Back up `raw/`.** The regeneration order is: Layer 0 to Layer 1 with `fetch_swift_mic.py`, then the exporters and `sync_wrappers.py`; the snapshots are regenerated separately by their own scripts.

[ADR 0010](./docs/decisions/0010-platform-charter.md) records what the platform is and is not, and [ADR 0011](./docs/decisions/0011-reprocessing.md) records that reprocessing from Layer 0 is not a general capability: replaying history means checking out a tag.

---

## The registry file

[`iso10383.json`](./iso10383.json) has two top-level keys, `meta` and `mics`. `mics` is an array sorted by `mic`. Output is deterministic (`json.dumps(..., sort_keys=True)`, LF line endings, trailing newline), and two runs on the same raw file produce byte-identical JSON.

```json
{
  "meta": {
    "version": "1.0.4",
    "updated": "2026-09-23",
    "source_snapshot": "2026-09-23",
    "source_url": "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv",
    "source_hash": "sha256:79de0f7704e260bd49b0d2439f3084891cabc93481da8bdbaa716e15a27211ed",
    "counts": {
      "operating": 1594, "segment": 1289,
      "active": 2296, "updated": 21, "expired": 566,
      "total": 2883
    },
    "broken_chains": []
  },
  "mics": [ "..." ]
}
```

### An operating MIC

```json
{
  "mic": "XNYS",
  "mic_type": "OPERATING",
  "status": "ACTIVE",
  "operating_mic": "XNYS",
  "market_name": "NEW YORK STOCK EXCHANGE, INC.",
  "legal_entity_name": "INTERCONTINENTAL EXCHANGE, INC.",
  "lei": "5493000F4ZO33MV32P92",
  "market_category": "NSPD",
  "acronym": "NYSE",
  "country_code": "US",
  "city": "NEW YORK",
  "website": "WWW.NYSE.COM",
  "creation_date": "2005-05-23",
  "last_update_date": "2025-04-28",
  "last_validation_date": "2025-04-28",
  "expiration_date": null,
  "note": null
}
```

An operating MIC self-references: `operating_mic == mic`.

### A segment MIC

`XTKS`, the Tokyo Stock Exchange segment under Japan Exchange Group:

```json
{
  "mic": "XTKS",
  "mic_type": "SEGMENT",
  "status": "ACTIVE",
  "operating_mic": "XJPX",
  "market_name": "TOKYO STOCK EXCHANGE",
  "legal_entity_name": "TOKYO STOCK EXCHANGE, INC.",
  "lei": "353800279ADEFGKNTV65",
  "market_category": "NSPD",
  "acronym": "TSE",
  "country_code": "JP",
  "city": "TOKYO",
  "website": "WWW.JPX.CO.JP",
  "creation_date": "2005-06-27",
  "last_update_date": "2016-05-23",
  "last_validation_date": null,
  "expiration_date": null,
  "note": null
}
```

A segment never self-references. Its `operating_mic` is its direct parent.

### A multi-level chain

The parent of a segment can itself be a segment. The 2026-09-23 snapshot has eight such entries, and the schema models them directly instead of assuming a two-level tree:

| Segment | Parent | Root operating MIC |
|---------|--------|--------------------|
| `EXPA` | `MTAA` | `XMIL` |
| `ICAT` | `ICAH` | `ICAP` |
| `LIQH` | `LIQU` | `ICPM` |
| `NBXO` | `XBXO` | `XNAS` |
| `PCDS` | `TPCD` | `XTUP` |
| `THRD` | `XNIM` | `XNAS` |
| `VRXP` | `XMLI` | `XPAR` |
| `XEAS` | `XEQT` | `XBER` |

There is no `root_mic` field: the root is computed by walking `operating_mic` until it equals `mic`. A stored root would be a second value to keep in sync when a parent changes ([`docs/JOINS.md`](./docs/JOINS.md)). The validator and the parser refuse chains deeper than eight levels or chains that do not terminate.

### An expired MIC

`XJAS`, the TSE JASDAQ segment that closed on 2022-04-04:

```json
{
  "mic": "XJAS",
  "mic_type": "SEGMENT",
  "status": "EXPIRED",
  "operating_mic": "XJPX",
  "market_name": "TOKYO STOCK EXCHANGE JASDAQ",
  "market_category": "NSPD",
  "creation_date": "2010-10-25",
  "last_update_date": "2022-03-28",
  "last_validation_date": "2022-03-28",
  "expiration_date": "2022-04-04",
  "note": "CLOSURE OF THIS MARKET ON 4 APRIL 2022."
}
```

(Other keys omitted here for length; every entry carries all 17.) Every `EXPIRED` entry has an `expiration_date`, and no other entry has one: 566 and 566 in this snapshot.

### Field reference

Seventeen fields per entry, every one present on every entry. The schema (`additionalProperties: false` at every level) requires ten keys to be present: `mic`, `mic_type`, `status` and `operating_mic` (never `null`), and `market_name`, `country_code`, `creation_date`, `last_update_date`, `last_validation_date` and `expiration_date` (present; the schema allows `null`). The other seven are optional and nullable. Absent values are JSON `null`, never an empty string.

| Field | Type | Null count | Meaning |
|-------|------|-----------:|---------|
| `mic` | string | 0 | Primary key. `^[A-Z0-9]{4}$`. 44 contain a digit; `3579` is all digits. |
| `mic_type` | string | 0 | `OPERATING` or `SEGMENT` |
| `status` | string | 0 | `ACTIVE`, `UPDATED` or `EXPIRED` |
| `operating_mic` | string | 0 | Parent MIC. Self for operating MICs. |
| `market_name` | string | 0 | Name as SWIFT publishes it |
| `legal_entity_name` | string or null | 1,494 | Registered legal name of the operator |
| `lei` | string or null | 629 | 20-character Legal Entity Identifier (all 2,254 present values are 20 characters) |
| `market_category` | string or null | 0 | One of the 16 ISO codes |
| `acronym` | string or null | 1,867 | Short name |
| `country_code` | string or null | 0 | ISO 3166-1 alpha-2, or `ZZ` |
| `city` | string or null | 0 | City of operation |
| `website` | string or null | 163 | Operator's website, as published (upper case) |
| `creation_date` | date or null | 0 | ISO 8601 |
| `last_update_date` | date or null | 0 | ISO 8601 |
| `last_validation_date` | date or null | 1,896 | ISO 8601 |
| `expiration_date` | date or null | 2,317 | ISO 8601; present exactly when `status` is `EXPIRED` |
| `note` | string or null | 1,324 | Free text from the source |

Ten fields are never null in this snapshot: the four non-nullable keys plus `market_name`, `country_code`, `creation_date`, `last_update_date`, `market_category` and `city`.

### Coverage

| Group | Count |
|-------|------:|
| Operating | 1,594 (1,334 active, 256 expired, 4 updated) |
| Segment | 1,289 (962 active, 310 expired, 17 updated) |
| Total | 2,883 |
| Active / Updated / Expired | 2,296 / 21 / 566 |
| Segments directly under an operating MIC | 1,281 |
| Segments under another segment | 8 |
| Broken parent chains | 0 |
| Expired on or after 2024-01-01 | 82 |
| Largest country counts | GB 603, US 504, DE 216, NL 123, FR 108, JP 89 |

### Enums

Three closed vocabularies. An unknown value raises in the parser and fails the schema.

**`mic_type`**: `OPERATING` identifies an entity that operates an exchange, trading platform or trade reporting facility; `SEGMENT` identifies a section of an entity that specialises in particular instruments or is regulated differently ([`docs/action_types.md`](./docs/action_types.md)).

**`status`**

| Value | Meaning | Count |
|-------|---------|------:|
| `ACTIVE` | In force | 2,296 |
| `UPDATED` | Changed since the last publication. Not a permanent state: it reverts to `ACTIVE` in a later snapshot. | 21 |
| `EXPIRED` | No longer in force; `expiration_date` is set | 566 |

**`market_category`**: sixteen codes from the ISO 10383 Release 2.0 factsheet. The 2026-09-23 snapshot uses 14.

| Code | Meaning | Count |
|------|---------|------:|
| `NSPD` | Not-Systematic Price Disseminator | 1,307 |
| `MLTF` | Multilateral Trading Facility | 381 |
| `SINT` | Systematic Internaliser | 351 |
| `RMKT` | Regulated Market | 303 |
| `ATSS` | Alternative Trading System | 143 |
| `OTHR` | Other | 129 |
| `OTFS` | Organised Trading Facility | 128 |
| `SEFS` | Systematic Externaliser | 30 |
| `CASP` | Consolidated Access Service Provider | 30 |
| `RMOS` | Regulated Market Off-Session | 27 |
| `APPA` | Approved Publication Arrangement | 26 |
| `DCMS` | Data Communication and Messaging Service | 22 |
| `TRFS` | Trade Reporting Facility | 5 |
| `IDQS` | Identifier Quotation Service | 1 |
| `ARMS` | Arrangement for Reporting | 0 |
| `CTPS` | Consolidated Tape Provider | 0 |

**Countries.** Every `country_code` is an ISO 3166-1 alpha-2 code or `ZZ`, ISO 10383's placeholder for "no fixed country", which is not an ISO 3166 code. The validator skips `ZZ` and checks the other 148 against the vendored ISO 3166 snapshot.

Design decisions behind these fields are recorded in [`docs/decisions/v1.0.0-decisions.md`](./docs/decisions/v1.0.0-decisions.md) (D2 one array, D3 self-reference, D4 categories, D5 closed enums), [ADR 0002](./docs/decisions/0002-operating-segment-model.md) (operating/segment model) and [ADR 0004](./docs/decisions/0004-market-category-codes.md) (category codes).

---

## Flat exports: SQL, CSV, TSV, Parquet

All nine flat exports are Layer 2. They are regenerated from `iso10383.json`, committed, and compared in CI by each generator's `--check` mode. `tools/export_columns.py` is the single source of column order for every exporter.

| Artifact | Columns | Rows | Generator |
|----------|--------:|-----:|-----------|
| `iso10383.sql`, `.postgresql.sql`, `.mysql.sql`, `.sqlite.sql` | 11 (`mics`) | 2,883 | `tools/export_sql.py` |
| `iso10383.csv`, `.excel.csv`, `.european.csv`, `.tsv` | 17 | 2,883 | `tools/export_csv.py` |
| `iso10383.parquet` | 17 | 2,883 | `tools/export_parquet.py` |

The column sets are nested on purpose. The 11 SQL columns are the foreign-key-ready minimum (`mic`, `mic_type`, `status`, `operating_mic`, `market_name`, `country_code`, `market_category`, and the four dates). The 17 CSV and Parquet columns append `legal_entity_name`, `acronym`, `lei`, `city`, `website` and `note` for human analysis, in that order.

### SQL

Four self-contained files, each in one transaction (`BEGIN;` ... `COMMIT;`) and safe to run twice.

| File | Target | Idempotency | Foreign key |
|------|--------|-------------|-------------|
| [`iso10383.sql`](./iso10383.sql) | Generic dialect: `ON CONFLICT DO NOTHING` (PostgreSQL 9.5+, SQLite 3.24+). Not SQL-92: it will not run on SQL Server, Oracle or Db2. | `ON CONFLICT DO NOTHING` | none declared |
| [`iso10383.postgresql.sql`](./iso10383.postgresql.sql) | PostgreSQL 12+ | `ON CONFLICT (mic) DO NOTHING` | `fk_mics_operating`, deferrable |
| [`iso10383.mysql.sql`](./iso10383.mysql.sql) | MySQL 8+ / MariaDB 10.4+ | `INSERT IGNORE`, one multi-row statement | none declared |
| [`iso10383.sqlite.sql`](./iso10383.sqlite.sql) | SQLite 3.37+ | `INSERT OR IGNORE` | declared, deferrable; with `PRAGMA foreign_keys = ON` the file loads cleanly |

Each file creates two tables, `market_categories` (16 rows) and `mics` (2,883 rows, `mic` primary key, `CHECK` constraints on `mic_type`, `status` and `market_category`), plus three indexes (`operating_mic`, `country_code`, `status`). `operating_mic` is `NOT NULL` in every dialect; operating MICs point to themselves. The PostgreSQL and SQLite files additionally declare the self-referencing foreign key, deferred so that a child row can load before its parent. The generic and MySQL files declare no foreign key.

```sql
-- Every venue under the Japan Exchange Group.
SELECT mic, market_name FROM mics WHERE operating_mic = 'XJPX';

-- Every active exchange in Germany.
SELECT mic, market_name FROM mics WHERE country_code = 'DE' AND status = 'ACTIVE';
```

**What is intentionally absent:** `legal_entity_name`, `lei`, `acronym`, `city`, `website` and `note`. The SQL export is a reference table for foreign keys, not a mirror of the JSON. For those fields use the CSV, the Parquet or the JSON.

### CSV and TSV

Four files, one per audience. LF line endings everywhere, headers always present, 17 columns, 2,883 data rows (2,884 lines). There is no comment header: it would break `pandas.read_csv` and violate RFC 4180.

| File | Audience | Quirk |
|------|----------|-------|
| [`iso10383.csv`](./iso10383.csv) | Every CSV parser | RFC 4180, comma-delimited |
| [`iso10383.excel.csv`](./iso10383.excel.csv) | Excel on Windows | UTF-8 BOM, so non-ASCII names render without an import prompt. The only file with a BOM. |
| [`iso10383.european.csv`](./iso10383.european.csv) | European Excel locales | Semicolon-delimited; opens without the import dialog |
| [`iso10383.tsv`](./iso10383.tsv) | Terminal, clipboard, Google Sheets, SQL clients | Tab-separated |

Consumer notes:

- **Nulls are empty fields** (JSON `null` becomes `""`), so `expiration_date` is empty for 2,317 rows.
- **Dates are plain `YYYY-MM-DD` text.** Ask pandas to parse them: `pd.read_csv("iso10383.csv", parse_dates=["creation_date", "expiration_date"])`.
- **`mic` is text, not a number.** `3579` is a valid MIC. Spreadsheet applications treat an all-digit cell as a number, so keep the column as text when you re-save.

```python
import pandas as pd
df = pd.read_csv("iso10383.csv")
print(df.shape)   # (2883, 17)
```

### Parquet

[`iso10383.parquet`](./iso10383.parquet): columnar, typed, snappy-compressed, one row group, 2,883 rows, readable by pandas, Polars, DuckDB, Spark and warehouse loaders. Columns follow `CSV_COLUMNS` (17).

Typing, because Parquet has a type system:

- `mic_type`, `status`, `country_code` and `market_category` are dictionary-encoded strings.
- `creation_date`, `last_update_date`, `last_validation_date` and `expiration_date` are `date32`, not text. pandas returns them as `datetime.date` objects (dtype `object`) with `None` for null; pass `date_as_object=False` to `to_pandas()` for `datetime64`.
- Null is a real null: `WHERE expiration_date IS NULL` returns the 2,317 non-expired rows.

**Footer metadata.** The footer carries `iso10383.version`, `iso10383.updated`, `iso10383.source_snapshot` and `iso10383.source_hash`, so a consumer who receives only the `.parquet` file can tell which registry version produced it. The footer's `iso10383.version` is one of the nine version sites.

```python
import pyarrow.parquet as pq
t = pq.read_table("iso10383.parquet")
print(t.schema.metadata[b"iso10383.version"])   # b'1.0.4'
```

### Comparison semantics and the build pin

`export_csv.py --check` and `export_sql.py --check` compare bytes. `export_parquet.py --check` also compares **bytes** (`OK: iso10383.parquet in sync (2883 rows, bytes)`), because the Parquet writer sorts the footer dictionary before writing and two runs on the same `pyarrow` version produce identical files. Byte output depends on the `pyarrow` version, so [`constraints.txt`](./constraints.txt) pins `pyarrow==25.0.1`. [`requirements-dev.txt`](./requirements-dev.txt) applies it with `-c constraints.txt`, and every CI job that installs `pyarrow` (`validate-json`, `check-exports`, `check-cli` and `refresh.yml`) installs with `-c constraints.txt`. A manifest claim keeps a bare `pip install pyarrow` out of `validate.yml`. [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) § Version-pinned byte outputs states the rule.

---

## Bundled copies and vendored snapshots

ISO 10383 has no aggregated layer: it publishes one grain (one row per MIC) and every derived file keeps it. The artifacts that are not a base export are the Layer 3 bundles and the Layer 4 snapshots.

### Layer 3: bundled copies

**Grain:** one byte-identical copy of `iso10383.json` per wrapper. **Join key:** none; it is the same file.

| Copy | Embedded by |
|------|-------------|
| `wrappers/python/src/iso10383/data/iso10383.json` | package data |
| `wrappers/javascript/src/data/iso10383.json` | `require` of the bundled file |
| `wrappers/rust/data/iso10383.json` | compiled in |
| `wrappers/go/data/iso10383.json` | `//go:embed data/iso10383.json` |

`tools/sync_wrappers.py` writes them and `sync_wrappers.py --check` verifies them (`OK: 4 wrapper copies in sync`). They are byte-identical so that a wrapper never disagrees with the root JSON.

### Layer 4: vendored snapshots

Two committed snapshots provide the cross-reference data. No runtime dependency on either sibling repository exists.

| Snapshot | Grain | Join key into this registry | Contents | Source |
|----------|-------|-----------------------------|----------|--------|
| [`tools/iso3166_snapshot.json`](./tools/iso3166_snapshot.json) | one entry per alpha-2 code | `mics[].country_code` | 252 codes | ISO 3166 v1.6.9 |
| [`tools/exchange_calendar_snapshot.json`](./tools/exchange_calendar_snapshot.json) | one entry per MIC | `mics[].mic` | 74 MICs | Exchange Calendar v2.15.4 |

Each has a `.meta.json` sibling with `source_version`, `vendored_at`, `vendored_from`, and a nested `meta` object holding `review_by` (2027-09-28 and 2027-01-10) and `refresh_cadence` (`monthly` for both). The snapshot files stay byte-for-byte as generated; the `.meta.json` records where they came from.

Each is produced by a generator that fetches the pinned tag named in its meta, never `main`: `tools/gen_iso3166_snapshot.py` reads `…/v<source_version>/iso3166.json`, and `tools/gen_exchange_calendar_snapshot.py` runs `git clone --branch v<source_version>`. Both have a `--check` mode that reproduces the committed snapshot from that tag and compares bytes. Both run in the `check-snapshots` CI job and in the release gate.

Two further mechanisms keep a snapshot honest, and they answer different questions:

- **Scheduled re-verification**: `tools/check_snapshot_freshness.py` fails when `review_by` has passed, whether or not anything upstream changed.
- **Cross-reference check**: `tools/check_iso3166_current.py` and `tools/check_exchange_calendar_current.py` compare the snapshot with the live sibling. A code or MIC set difference fails under `--strict`. A version-label drift prints `warning: version drift: ...` and does not change the exit code.

The Exchange Calendar snapshot's 74 MICs are 68 operating-active, 3 segment-active and 3 expired operating MICs (`XJKT`, `XBSP`, `XTAD`); all 74 are in this registry. [`docs/exchange_calendar_mics.txt`](./docs/exchange_calendar_mics.txt) is a 74-line reference list of them.

---

## Worked example: a venue tree in ten commands

`examples/` does not exist in this repository, so this is a reproducible session instead: a shell pass against the CLI and one pandas read of the Parquet. Every output below was produced from the committed files at version 1.0.4 (snapshot 2026-09-23). Run it from the repository root; the CLI is written `iso10383` for `python3 tools/iso10383_cli.py`.

### In the shell

```bash
$ iso10383 lookup XNYS | head -6
acronym               NYSE
city                  NEW YORK
country_code          US
creation_date         2005-05-23
expiration_date
last_update_date      2025-04-28

$ iso10383 parent XTKS
XTKS -> XJPX

$ iso10383 segments XJPX --raw mic
XJAS
XOSE
XOSJ
XTAM
XTK1
XTK2
XTK3
XTKS
XTKT

$ iso10383 expired --since 2024-01-01 --raw mic | wc -l
82

$ iso10383 list --country DE --status ACTIVE --raw mic | wc -l
182

$ iso10383 validate XNYS XLON XTKS XPAR; echo "exit $?"
OK: 4 MIC(s) validated
exit 0

$ iso10383 validate XNYS ZZZZ; echo "exit $?"
not found: ZZZZ
exit 1

$ iso10383 --registry /nonexistent.json info; echo "exit $?"
registry not found: /nonexistent.json
exit 3
```

`segments XJPX` lists nine children and not `XJPX` itself. The SQL query `WHERE operating_mic = 'XJPX'` returns ten rows, because an operating MIC is its own parent.

### In pandas

```python
import pandas as pd
df = pd.read_parquet("iso10383.parquet")
print(df.shape)                                   # (2883, 17)

# The grain is one row per MIC: 2 types x 3 statuses.
print(df.groupby(["mic_type", "status"], observed=True).size())
# mic_type   status
# OPERATING  ACTIVE     1334
#            EXPIRED     256
#            UPDATED       4
# SEGMENT    ACTIVE      962
#            EXPIRED     310
#            UPDATED      17

# Operators with the most direct segments.
seg = df[df.mic_type == "SEGMENT"]
print(seg.groupby("operating_mic").size().sort_values(ascending=False).head(3))
# XSTO    36
# XMTS    24
# XWAR    23
```

Resolving the root operator of every MIC is a walk up `operating_mic`, because there is no `root_mic` column:

```python
by = df.set_index("mic")
def root(m):
    while by.at[m, "operating_mic"] != m:
        m = by.at[m, "operating_mic"]
    return m

df["root"] = df["mic"].map(root)
print((df.root != df.operating_mic).sum())        # 8
print(df.root.value_counts().head(3).to_string())
# XSTO    37
# XMTS    25
# XWAR    24
```

Eight MICs have a root different from their direct parent (the chains in [The registry file](#the-registry-file)). Grouping by `operating_mic` alone would credit `XBXO` and `XNIM`, but not `XNAS`, with the venues that sit under them; grouping by `root` credits `XNAS`. That is the reason a consumer that wants "the operator" should not stop at one hop.

Expirations per year, from the same frame:

```python
exp = df[df.status == "EXPIRED"]
print(pd.to_datetime(exp.expiration_date).dt.year.value_counts().sort_index().tail(3).to_string())
# 2024    26
# 2025    24
# 2026    32
```

---

## Command-line interface

The CLI is [`tools/iso10383_cli.py`](./tools/iso10383_cli.py), a repository artifact: it needs a checkout of this repository, and no wrapper installs it as a command. `bin/iso10383` is a repo-local shim for it. The Python wrapper's `python -m iso10383` is a shim that looks for `tools/iso10383_cli.py` in a source checkout and exits 3 with a one-line message when it cannot find one. All commands are read-only and offline. Nine subcommands:

| Subcommand | Purpose |
|------------|---------|
| `lookup MIC` | All fields for one MIC |
| `list` | Filter across the registry with `--country CC`, `--category CODE`, `--status {ACTIVE,UPDATED,EXPIRED}`, `--mic-type {OPERATING,SEGMENT}` |
| `segments MIC` | Direct children of a parent MIC |
| `parent MIC` | The `operating_mic` of a MIC, printed as `MIC -> PARENT` |
| `expired [--since YYYY-MM-DD]` | Expired MICs, optionally on or after a date |
| `validate MIC...` | Exit 0 if every MIC exists |
| `search QUERY` | Substring on `market_name` and `acronym` |
| `info` | Registry metadata (`meta` block and counts) |
| `check` | Built-in smoke test: `OK: 2883 MICs, 1594 operating, 1289 segment, 0 broken chains` |

**Global option:** `--registry PATH` (or the environment variable `ISO10383_REGISTRY`; default `./iso10383.json`). **Per-command options:** `--color {never,auto,always}`, `--no-color`, `--quiet`.

**Output modes**, mutually exclusive on every subcommand: `--json` (object or array), `--jsonl` (one object per line), `--csv`, `--tsv` (columns match `iso10383.csv` and `iso10383.tsv`), `--raw FIELD` (bare values, one per line).

**Exit codes:** 0 success; 1 not found (`lookup`, `validate`); 2 usage error; 3 registry file missing or invalid. A script can tell "not in the registry" from "you typed the command wrong".

**Color** is on when stdout is a terminal and off when piped. Override with `ISO10383_COLOR=never|auto|always`, `--color`, `--no-color`, or `NO_COLOR`.

```bash
# Every operating MIC in Japan, MIC codes only.
iso10383 list --country JP --mic-type OPERATING --raw mic

# Look up every active German venue.
iso10383 list --country DE --status ACTIVE --raw mic | xargs -I{} iso10383 lookup {} --json

# Guard an order-routing call.
iso10383 validate XNYS XLON XTKS XPAR || echo "unknown MIC"

# Branch on "not in the registry" versus "usage error".
iso10383 lookup "$MIC" >/dev/null 2>&1
case $? in 0) echo found ;; 1) echo unknown ;; 2) echo usage ;; 3) echo no-registry ;; esac

# Registry metadata for a script.
iso10383 info --json
```

---

## Language wrappers

Four wrappers, one contract. Each is verified against the shared fixture [`tests/cross_language_consistency.json`](./tests/cross_language_consistency.json) and each bundles a byte-identical copy of `iso10383.json` (see [Bundled copies](#layer-3-bundled-copies)).

| Language | Package | Source | Minimum | Import | Tests |
|----------|---------|--------|---------|--------|------:|
| Python | `iso10383-registry` | [`wrappers/python`](./wrappers/python) | Python 3.9 | `from iso10383 import MICRegistry` | 29 |
| JavaScript | `iso10383-registry` | [`wrappers/javascript`](./wrappers/javascript) | Node 18 | `const { MICRegistry } = require("iso10383-registry")` | 28 |
| Rust | `iso10383-registry` | [`wrappers/rust`](./wrappers/rust) | edition 2021 | `use iso10383_registry::Registry;` | 26 |
| Go | `github.com/slimissa/iso10383/wrappers/go` | [`wrappers/go`](./wrappers/go) | Go 1.21 | `import iso10383 "github.com/slimissa/iso10383/wrappers/go"` | 28 |

Each wrapper has its own README with the full API. Python, JavaScript and Go have no runtime dependencies; the Rust crate depends on `serde` and `serde_json`.

### One API, four spellings

| Operation | Python | JavaScript | Rust | Go |
|-----------|--------|------------|------|----|
| Load | `MICRegistry()` | `new MICRegistry()` | `Registry::load()` | `LoadRegistry()` |
| Lookup | `.by_mic("XNYS")` | `.byMic("XNYS")` | `.by_mic("XNYS")` | `.ByMIC("XNYS")` |
| Direct segments | `.segments("XJPX")` | `.segments("XJPX")` | `.segments("XJPX")` | `.Segments("XJPX")` |
| Parent | `.operating_mic("XTKS")` | `.operatingMic("XTKS")` | `.operating_mic("XTKS")` | `.OperatingMIC("XTKS")` |
| Expired | `.expired(since="2024-01-01")` | `.expired("2024-01-01")` | `.expired(Some("2024-01-01"))` | `.Expired("2024-01-01")` |
| By country | `.by_country("US")` | `.byCountry("US")` | `.by_country("US")` | `.ByCountry("US")` |
| By status | `.by_status("ACTIVE")` | `.byStatus("ACTIVE")` | `.by_status("ACTIVE")` | `.ByStatus("ACTIVE")` |
| By type | `.by_mic_type("SEGMENT")` | `.byMicType("SEGMENT")` | `.by_mic_type("SEGMENT")` | `.ByMICType("SEGMENT")` |
| By category | `.by_category("NSPD")` | `.byCategory("NSPD")` | `.by_category("NSPD")` | `.ByCategory("NSPD")` |
| Search | `.search("nasdaq")` | `.search("nasdaq")` | `.search("nasdaq")` | `.Search("nasdaq")` |
| Validate | `.validate([...])` | `.validate([...])` | `.validate([...])` | `.Validate([]string{...})` |

`validate` returns whether every MIC exists plus the list of missing ones (Python: `(False, ['ZZZZ'])`). Lookups accept lower-case input and tie order in `expired` is the same in all four, both pinned by shared-fixture cases. `search("nasdaq")` returns 81 entries in the Python wrapper and in the CLI.

### Verify every wrapper agrees

```bash
bash tools/check_cross_language.sh            # run all suites, report skips
bash tools/check_cross_language.sh --strict   # a skipped suite fails
```

The script runs the Python, JavaScript, Rust and Go suites, then `sync_wrappers.py --check`. It does not diff wrapper output: each suite checks the shared fixture independently. A suite whose toolchain (`node`, `cargo`, `go`) is missing prints `SKIP`; without `--strict` that does not fail the script. With `--strict`, as in the release gate and the `check-cross-language` job, a skipped suite exits 1. Exit 1 also means a suite failed; exit 2 means `python3` is missing or an argument is unknown. A clean strict run prints `OK: 5 suite(s) passed, 0 skipped`.

### The fixture-anchor rule

Tests must not hardcode fixture values. Each language reads its expected values from the shared fixture through an anchor module (`wrappers/python/tests/anchors.py`, `wrappers/javascript/test/fixture.js`), and `tests/test_fixture.py` validates the fixture itself, so a missing anchor fails at startup rather than silently.

---

## Validation

[`tools/validate.py`](./tools/validate.py) has six independent layers, each runnable in isolation:

```bash
python3 tools/validate.py                       # all six
python3 tools/validate.py --only coverage       # repeatable
python3 tools/validate.py --skip cross-reference
python3 tools/validate.py --strict              # promote warnings to errors
python3 tools/validate.py --advisory            # cross-registry gaps become warnings
```

Exit codes: 0 pass (warnings allowed), 1 data error, 2 usage error (file not found), 3 schema violation or malformed JSON. A clean run prints `OK: 2883 MICs validated`.

| Check | Tool | What it catches |
|-------|------|-----------------|
| **Schema** | `validate.py` + `schema.json` | JSON Schema draft-07; `additionalProperties: false` at every level; closed enums for `mic_type`, `status`, `market_category`; the 10 required keys |
| **Integrity** | `validate.py` | MIC pattern `^[A-Z0-9]{4}$`, country pattern `^[A-Z]{2}$`, ISO 8601 dates, non-empty strings |
| **Business** | `validate.py` | MIC uniqueness; operating MICs self-reference; segments do not; `EXPIRED` has an `expiration_date` |
| **Cross-reference** | `validate.py` | Every segment chain terminates at an operating MIC (max 8 hops); every `country_code` except `ZZ` is in the ISO 3166 snapshot; every MIC in the Exchange Calendar snapshot is in the registry |
| **Ground truth** | `validate.py` | Spot checks: `XNYS` (OPERATING, US), `XLON` (OPERATING, GB), `XTKS` (SEGMENT, JP), `XPAR` (FR) |
| **Coverage** | `validate.py` | Operating >= 1,500, segment >= 1,000, total >= 2,500 |
| **Raw-to-curated parse** | `fetch_swift_mic.py` | Unknown type or status values, bad self-reference, malformed dates, missing columns, broken chains with `--strict` |
| **Refresh diff** | `refresh_diff.py` | ADDED / CHANGED / REMOVED between two registry files; a REMOVED count above 0 opens the refresh PR as a draft |
| **Version consistency** | `check_version_consistency.py` | Any of the nine sites disagreeing; the schema version disagreeing with the schema badge |
| **Registry freshness** | `check_registry_freshness.py` | `meta.source_snapshot` more than 60 days old |
| **Snapshot freshness** | `check_snapshot_freshness.py` | A vendored snapshot past its `review_by` date; takes `--today YYYY-MM-DD` |
| **Release claims** | `check_release_claims.py` | A documentation or version claim that no longer matches the tree |
| **Mojibake** | `check_mojibake.py` | UTF-8 / Latin-1 round-trip corruption, replacement characters, unclosed code fences; `--path` scans one file |
| **ISO 3166 drift** | `check_iso3166_current.py` | Snapshot code set differs from the live sibling (`--strict` fails; a version-label drift only warns) |
| **Exchange Calendar drift** | `check_exchange_calendar_current.py` | Snapshot MIC set differs from the live sibling (same severity rules) |
| **Snapshot reproduction** | `gen_iso3166_snapshot.py --check`, `gen_exchange_calendar_snapshot.py --check` | A committed snapshot that differs byte-for-byte from the pinned tag |
| **Export drift** | `export_csv.py`, `export_sql.py`, `export_parquet.py` with `--check` | A derived file that is stale against `iso10383.json` |
| **Wrapper sync** | `sync_wrappers.py --check` | A bundled copy that differs from `iso10383.json` |
| **CLI smoke test** | `iso10383_cli.py check` | Counts or chain integrity wrong when read through the CLI |
| **Cross-language** | `check_cross_language.sh --strict` | A wrapper suite that fails or cannot run |

`tools/check_iso4217_current.py` is retained but inactive: it exits 0 with a note because ISO 10383 has no currency field and no ISO 4217 snapshot, and neither CI nor the release gate runs it.

### Cross-registry checks are blocking

Cross-registry validation has been blocking by default since v1.0.1 (D6, D17): an unexpected gap is an error, and `--advisory` reverts to the v1.0.0 behaviour. The allowlist `tools/validate.py::KNOWN_EXCHANGE_CALENDAR_GAPS` is **empty**. Its three former entries (`XBEK`, `XNBO`, `XQSE`) were renamed upstream at Exchange Calendar v2.4.2 to `XBEY`, `XNAI` and `DSMD`, all present in this registry. The mechanism stays, and adding a MIC to the allowlist requires an ADR amendment ([ADR 0007](./docs/decisions/0007-cross-registry-allowlist.md)).

### Release claims

[`tools/release_claims.json`](./tools/release_claims.json) holds 147 machine-checkable claims, each of the form `{file, contains}` or `{file, absent}`: 6 for 1.0.3, 5 for 1.0.4 and 136 under `doc-facts`. `check_release_claims.py 1.0.4` verifies the `doc-facts` set plus the 1.0.4 set (141 claims) and exits non-zero on the first false one. It runs in the `validate-json` CI job and in the release gate. The claims exist to stop classes of drift from coming back: a version string or count that disagrees with the tree, a tool name that no longer exists, mojibake, an unclosed code fence, a snapshot that disagrees with its meta, a bare `pip install pyarrow`, and the stale phrases a past audit removed (for example a wrong dialect label for the generic SQL file). Claims describe state, not intent ([`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) rule 6c).

### Tests

| Suite | Command | Tests |
|-------|---------|------:|
| Root (Python) | `python3 -m pytest tests/ -q` | 111 |
| Python wrapper | `python3 -m pytest wrappers/python/tests -q` | 29 |
| JavaScript | `(cd wrappers/javascript && node --test)` | 28 |
| Rust | `(cd wrappers/rust && cargo test --quiet)` | 26 |
| Go | `(cd wrappers/go && go test ./... -count=1)` | 28 |
| **Total** | | **222** |

The Tests badge above reads 222, the sum of this table. The root suite is spread over twelve files in `tests/`: `test_check_mojibake.py` (17), `test_cli.py` (16), `test_checks.py` (13), `test_export_sql.py` (12), `test_iso10383_codes.py` (11), `test_export_parquet.py` (9), `test_validate_schema.py` (9), `test_export_csv.py` (7), `test_wrappers.py` (6), `test_self_reference.py` (5), `test_fixture.py` (3), `test_scripts.py` (3).

---

## Continuous integration

Two workflows in [`.github/workflows`](./.github/workflows):

| Workflow | Runs on | Jobs | Protects against |
|----------|---------|------|------------------|
| **`validate.yml`** | push to `main`, pull requests to `main`, manual dispatch | seven, below | A stale derived file, a failing validator, a drifting wrapper, a snapshot that no longer reproduces, a version mismatch |
| **`refresh.yml`** | 00:00 UTC on the 15th of every month, manual dispatch | one: download, parse, diff, regenerate, validate, open a pull request | A registry that silently falls behind SWIFT's monthly file |

CI runs seven jobs on every push and pull request:

| Job | What runs | What it guards |
|-----|-----------|----------------|
| `validate-json` | `validate.py`, version consistency, registry and snapshot freshness, release claims, both `check_*_current.py --strict`, root `pytest` | The data, the version sites, the documentation claims |
| `check-exports` | `export_csv.py`, `export_sql.py`, `export_parquet.py`, `sync_wrappers.py`, all with `--check` | A derived or bundled file that is stale |
| `check-cli` | `iso10383_cli.py check`, `tests/test_cli.py` | The CLI against the data |
| `check-wrappers` | Matrix of four (python, javascript, rust, go) | Each wrapper's own suite, on Node 22, Go 1.22, stable Rust and Python 3.12 |
| `check-cross-language` | `check_cross_language.sh --strict`; needs `check-wrappers` | A skipped or failing suite |
| `check-snapshots` | `gen_iso3166_snapshot.py --check`, `gen_exchange_calendar_snapshot.py --check`; needs `check-wrappers` | A vendored snapshot that no longer reproduces from its pinned tag |
| `check-mojibake` | `check_mojibake.py` | Encoding corruption and unclosed fences in any text file |

Every job that installs `pyarrow` installs with `-c constraints.txt`. [ADR 0006](./docs/decisions/0006-ci-toolchain-parity.md) records why the local gate and CI run the same toolchain.

---

## Refreshing the data

SWIFT publishes the MIC file on the **second Monday of each month**; modifications become effective on the fourth Monday. `tools/check_registry_freshness.py` fails CI when `meta.source_snapshot` is more than **60 days** old, two missed publication cycles, which signals that the update process broke rather than that the source is late.

### The monthly process

[`refresh.yml`](./.github/workflows/refresh.yml) runs on the 15th. It downloads the current file to `raw/MIC_new.csv`, copies the old registry aside, parses the new file into `iso10383.json` (`--version` from `VERSION`, `--snapshot-date` today), diffs old against new with `refresh_diff.py`, regenerates the exports and bundles, runs the validator and the root tests, and opens a pull request with `peter-evans/create-pull-request@v6`. Nothing merges on its own. **A refresh with `REMOVED > 0` opens the PR as a draft**, and a human converts it to ready after reading the removed MICs in the workflow log: a removed MIC is the change class most likely to break a consumer. The history of that guard, including the 2026-10-10 defect fix, is in [ADR 0003](./docs/decisions/0003-monthly-refresh.md) and [ADR 0011](./docs/decisions/0011-reprocessing.md). The registry is a monthly batch, not a stream.

Manually:

```bash
cp iso10383.json /tmp/iso10383.old.json            # snapshot the old registry first
python3 tools/fetch_swift_mic.py --download --force --strict --version "$(cat VERSION)"
python3 tools/refresh_diff.py /tmp/iso10383.old.json iso10383.json
python3 tools/export_csv.py
python3 tools/export_sql.py
python3 tools/export_parquet.py
python3 tools/sync_wrappers.py
python3 tools/validate.py
python3 tools/check_version_consistency.py
python3 -m pytest tests/ -q
```

### Audit

`meta.source_hash` is the `sha256:` digest of the raw file the JSON came from. To verify a JSON against a raw file:

```bash
python3 -c "
import hashlib, json
from pathlib import Path
d = json.load(open('iso10383.json'))
h = 'sha256:' + hashlib.sha256(Path('raw/MIC_YYYYMMDD.csv').read_bytes()).hexdigest()
print('match' if h == d['meta']['source_hash'] else 'MISMATCH')
"
```

Replace `MIC_YYYYMMDD.csv` with the cached raw file's name. Two runs on the same raw file produce byte-identical JSON.

---

## Release pipeline

Releases are cut by [`scripts/release.sh`](./scripts/release.sh):

```bash
bash scripts/release.sh <version> --dry-run   # print every step; changes nothing
bash scripts/release.sh <version>             # release
```

The script conforms to [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md), the pattern shared across the registry family, and its header names two divergences: one per-push workflow is polled today, and the tag-move procedure is recovery-only ([ADR 0005](./docs/decisions/0005-tag-discipline.md) § Scope). In order:

1. **Preconditions.** An orphan-variable check, `git fetch origin main`, branch is `main`, `HEAD` equals `origin/main`, clean working tree, tag `v<version>` free locally and on `origin`, a `## [<version>]` section in `CHANGELOG.md`, `gh` installed, and `VERSION` differs from the target. Any failure exits 1.
2. **Version sites.** Writes `VERSION`, `iso10383.json` `meta.version`, the Python `pyproject.toml` and `__init__.py`, `package.json`, `Cargo.toml` and the README badge. The changelog heading is written by hand beforehand, and the Parquet footer follows from regeneration, which makes nine sites.
3. **Regenerate** the exports and the bundles, in layer order.
4. **Version consistency** (`check_version_consistency.py`) after regeneration, so a site the bump missed fails here.
5. **Gate.** Seventeen `gate` calls, in this order; each records its exit code in `GATE_LOG` and stops the release on a non-zero exit:

   1. `python3 tools/check_version_consistency.py`
   2. `python3 tools/validate.py`
   3. `python3 tools/check_registry_freshness.py`
   4. `python3 tools/check_snapshot_freshness.py`
   5. `python3 tools/check_mojibake.py`
   6. `python3 tools/check_release_claims.py "$VERSION"`
   7. `python3 tools/check_iso3166_current.py --strict`
   8. `python3 tools/check_exchange_calendar_current.py --strict`
   9. `python3 tools/iso10383_cli.py check`
   10. `python3 tools/export_csv.py --check`
   11. `python3 tools/export_sql.py --check`
   12. `python3 tools/export_parquet.py --check`
   13. `python3 tools/sync_wrappers.py --check`
   14. `python3 -m pytest tests/ -q`
   15. `bash tools/check_cross_language.sh --strict`
   16. `python3 tools/gen_iso3166_snapshot.py --check`
   17. `python3 tools/gen_exchange_calendar_snapshot.py --check`

6. **Commit and push** (`Release v<version>`), then **poll every workflow run for the release SHA** every 15 seconds for up to 600 seconds. It continues only when every run has completed with success; a failure or a timeout exits 1 before the tag exists.
7. **Tag** only on green: the message is the `CHANGELOG.md` section (first line `Release v<version>`), checked for a header, a body and placeholders, then `git tag -a -F ... --cleanup=verbatim`. The recorded message is read back with `git for-each-ref` and compared with the file; on a mismatch the local tag is deleted and nothing is pushed. Then `git push origin "v<version>"`.
8. **Verification document.** Writes `docs/v<version>-verification.md` with the commit SHA, the tag object SHA, and the exit code of every gate from `GATE_LOG`, so a gate added to the script cannot be missing from the document.

Tags are immutable ([ADR 0005](./docs/decisions/0005-tag-discipline.md)). Five verification documents exist: [`v1.0.0`](./docs/v1.0.0-verification.md), [`v1.0.1`](./docs/v1.0.1-verification.md), [`v1.0.2`](./docs/v1.0.2-verification.md), [`v1.0.3`](./docs/v1.0.3-verification.md), [`v1.0.4`](./docs/v1.0.4-verification.md). The gate's `pyarrow` and toolchain requirements are the ones in [Flat exports](#comparison-semantics-and-the-build-pin).

---

## Versioning

One version number, nine sites, all enforced by [`tools/check_version_consistency.py`](./tools/check_version_consistency.py):

| # | Site | Why it is a site |
|---|------|------------------|
| 1 | `VERSION` | The source of truth |
| 2 | `CHANGELOG.md` top released heading | The release history must name the version it describes |
| 3 | `iso10383.json` `meta.version` | A consumer holding only the JSON can tell what it is |
| 4 | `iso10383.parquet` footer `iso10383.version` | A consumer holding only the Parquet can tell |
| 5 | `wrappers/python/pyproject.toml` | The Python package version |
| 6 | `wrappers/python/src/iso10383/__init__.py` `__version__` | The version the imported module reports |
| 7 | `wrappers/javascript/package.json` | The npm package version |
| 8 | `wrappers/rust/Cargo.toml` | The crate version |
| 9 | `README.md` badge | The version a reader sees first |

CI fails if any disagree. Wrapper package versions track the registry version (D16). The schema has its own version (`schema.json` `version`, currently 1.0.0), which the same script checks against the schema badge; it is not a registry-version site, and a schema change does not bump the other nine.

Deliberate exclusions:

- **Go is not a site.** Go modules carry no version in `go.mod`; the version is the git tag.
- **The SQL and CSV files are not sites.** The SQL files carry `-- version:` in a comment header, and their `--check` mode fails when it is stale.
- **The two snapshots have their own versions.** `source_version` in each `.meta.json` is the sibling's version, not this registry's.

The registry follows [Semantic Versioning](https://semver.org/): major for breaking schema changes, minor for new MICs, new optional fields or new tooling, patch for data corrections.

---

## Project structure

```text
iso10383/
├── VERSION                              # Registry version, source of truth
├── iso10383.json                        # Layer 1: the registry (2,883 MICs)
├── schema.json                          # JSON Schema draft-07 contract, version 1.0.0
├── README.md                            # This file
├── CHANGELOG.md                         # Release history, [Unreleased] on top
├── CONTRIBUTING.md                      # The four rules, source discipline, change workflows
├── LICENSE                              # Apache 2.0
├── constraints.txt                      # Output-affecting pins (pyarrow==25.0.1)
├── requirements-dev.txt                 # jsonschema, pyarrow, pytest; applies constraints.txt
├── .gitattributes                       # LF endings for text exports; parquet is binary
├── .gitignore                           # raw/, caches, .venv, rust target and lockfile
│
├── iso10383.sql                         # Layer 2: generic dialect (ON CONFLICT DO NOTHING)
├── iso10383.postgresql.sql              # Layer 2: PostgreSQL 12+
├── iso10383.mysql.sql                   # Layer 2: MySQL 8+ / MariaDB 10.4+
├── iso10383.sqlite.sql                  # Layer 2: SQLite 3.37+
├── iso10383.csv                         # Layer 2: CSV, RFC 4180, 17 columns
├── iso10383.excel.csv                   # Layer 2: CSV with UTF-8 BOM
├── iso10383.european.csv                # Layer 2: CSV, semicolon-delimited
├── iso10383.tsv                         # Layer 2: TSV
├── iso10383.parquet                     # Layer 2: Parquet, typed, 17 columns
│
├── bin/
│   └── iso10383                         # Repo-local shim for tools/iso10383_cli.py
│
├── tools/
│   ├── fetch_swift_mic.py               # Layer 0 to 1: download and parse SWIFT's CSV
│   ├── refresh_diff.py                  # ADDED / CHANGED / REMOVED between two registry files
│   ├── validate.py                      # Six-layer validator
│   ├── export_columns.py                # Canonical column order for every exporter
│   ├── export_sql.py                    # SQL generator, 4 dialects (--check)
│   ├── export_csv.py                    # CSV/TSV generator, 4 files (--check)
│   ├── export_parquet.py                # Parquet generator, byte-stable (--check)
│   ├── sync_wrappers.py                 # Layer 3: bundled-copy sync (--check)
│   ├── iso10383_cli.py                  # The command-line interface
│   ├── gen_iso3166_snapshot.py          # Layer 4: ISO 3166 snapshot from its pinned tag (--check)
│   ├── gen_exchange_calendar_snapshot.py  # Layer 4: Exchange Calendar snapshot from its pinned tag (--check)
│   ├── iso3166_snapshot.json            # Layer 4: 252 alpha-2 codes, v1.6.9
│   ├── iso3166_snapshot.meta.json       # Vendoring metadata and review_by
│   ├── exchange_calendar_snapshot.json  # Layer 4: 74 MICs, v2.15.4
│   ├── exchange_calendar_snapshot.meta.json  # Vendoring metadata and review_by
│   ├── check_version_consistency.py     # The nine version sites, plus the schema badge
│   ├── check_registry_freshness.py      # meta.source_snapshot within 60 days
│   ├── check_snapshot_freshness.py      # Vendored snapshots within review_by
│   ├── check_release_claims.py          # Verifies the claims manifest
│   ├── release_claims.json              # 147 {file, contains|absent} claims
│   ├── check_mojibake.py                # Encoding corruption and unclosed fences
│   ├── check_iso3166_current.py         # Snapshot vs live ISO 3166 (--strict)
│   ├── check_exchange_calendar_current.py  # Snapshot vs live Exchange Calendar (--strict)
│   ├── check_iso4217_current.py         # Retained, inactive: no ISO 4217 snapshot exists
│   └── check_cross_language.sh          # The four wrapper suites plus sync (--strict)
│
├── scripts/
│   └── release.sh                       # The release pipeline
│
├── tests/
│   ├── cross_language_consistency.json  # Shared fixture for all four wrappers
│   ├── conftest.py                      # Shared pytest setup
│   ├── test_check_mojibake.py           # Mojibake checker, each class at runtime
│   ├── test_checks.py                   # The checking tools
│   ├── test_cli.py                      # CLI behaviour and exit codes
│   ├── test_export_csv.py               # CSV/TSV exporter
│   ├── test_export_parquet.py           # Parquet exporter
│   ├── test_export_sql.py               # SQL exporter
│   ├── test_fixture.py                  # The shared fixture itself
│   ├── test_iso10383_codes.py           # Known-code ground truth
│   ├── test_scripts.py                  # release.sh and verification-doc properties
│   ├── test_self_reference.py           # Operating self-reference, chain termination
│   ├── test_validate_schema.py          # Validator layers against bad fixtures
│   ├── test_wrappers.py                 # Wrapper copies and shims
│   └── fixtures/
│       ├── bad_cycle.csv                # Parser input: cyclic parent chain
│       ├── bad_missing_parent.csv       # Parser input: parent absent
│       ├── valid_three_level.csv        # Parser input: a valid three-level chain
│       └── validator/
│           ├── business_bad_self_ref.json        # Business layer failure
│           ├── business_expired_no_date.json     # Business layer failure
│           ├── coverage_low_operating.json       # Coverage layer failure
│           ├── groundtruth_xnys_wrong_country.json  # Ground-truth layer failure
│           ├── integrity_bad_mic.json            # Integrity layer failure
│           └── schema_bogus_field.json           # Schema layer failure
│
├── wrappers/
│   ├── python/
│   │   ├── README.md                    # Python API
│   │   ├── pyproject.toml               # Package manifest (version site)
│   │   ├── src/iso10383/
│   │   │   ├── __init__.py              # Exports; __version__ (version site)
│   │   │   ├── __main__.py              # python -m iso10383 shim
│   │   │   ├── registry.py              # MIC and MICRegistry
│   │   │   └── data/iso10383.json       # Layer 3 copy
│   │   └── tests/
│   │       ├── anchors.py               # Fixture anchors
│   │       ├── conftest.py              # pytest setup
│   │       └── test_registry.py         # 29 tests
│   ├── javascript/
│   │   ├── README.md                    # JavaScript API
│   │   ├── package.json                 # Package manifest (version site)
│   │   ├── src/index.js                 # MICRegistry
│   │   ├── src/data/iso10383.json       # Layer 3 copy
│   │   ├── test/fixture.js              # Fixture anchors
│   │   └── test/registry.test.js        # 28 tests (node --test)
│   ├── rust/
│   │   ├── README.md                    # Rust API
│   │   ├── Cargo.toml                   # Crate manifest (version site)
│   │   ├── src/lib.rs                   # Registry
│   │   ├── data/iso10383.json           # Layer 3 copy
│   │   ├── examples/smoke.rs            # End-to-end smoke example
│   │   └── tests/registry.rs            # 26 tests
│   └── go/
│       ├── README.md                    # Go API
│       ├── go.mod                       # Module path; carries no version
│       ├── registry.go                  # Registry (embeds data/)
│       ├── registry_test.go             # 28 tests
│       └── data/iso10383.json           # Layer 3 copy
│
├── docs/
│   ├── LAYERS.md                        # The five-layer model
│   ├── PROVENANCE.md                    # Source, mapping, refresh, audit, known gaps
│   ├── JOINS.md                         # The MIC join graph, from the leaf side
│   ├── RELEASE_PATTERN.md               # Release invariants shared across the registry family
│   ├── action_types.md                  # OPERATING vs SEGMENT, statuses, categories
│   ├── source_format.md                 # SWIFT's file, verbatim ground truth
│   ├── mic_lei_source_format.md         # MIC to LEI reconnaissance (ADR 0008)
│   ├── mic_bic_source_format.md         # MIC to BIC reconnaissance (ADR 0009)
│   ├── exchange_calendar_mics.txt       # The 74 MICs Exchange Calendar references
│   ├── v1.0.0-verification.md          # Gate record for v1.0.0
│   ├── v1.0.1-verification.md          # Gate record for v1.0.1
│   ├── v1.0.2-verification.md          # Gate record for v1.0.2
│   ├── v1.0.3-verification.md          # Gate record for v1.0.3
│   ├── v1.0.4-verification.md          # Gate record for v1.0.4
│   └── decisions/
│       ├── v1.0.0-decisions.md          # D1 to D17
│       ├── 0001-source-format.md        # What SWIFT's file is
│       ├── 0002-operating-segment-model.md  # One array, self-reference, multi-level
│       ├── 0003-monthly-refresh.md      # Monthly cadence and the REMOVED > 0 guard
│       ├── 0004-market-category-codes.md    # Closed enum of the 16 codes
│       ├── 0005-tag-discipline.md       # Immutable tags and the recovery exception
│       ├── 0006-ci-toolchain-parity.md  # Local gate and CI run the same toolchain
│       ├── 0007-cross-registry-allowlist.md # Blocking cross-registry checks, empty allowlist
│       ├── 0008-mic-lei-companion-declined.md  # Why there is no MIC to LEI file
│       ├── 0009-mic-bic-companion-declined.md  # Why there is no MIC to BIC file
│       ├── 0010-platform-charter.md     # What the platform is, and its limits
│       ├── 0011-reprocessing.md         # Monthly batch; no general reprocessing
│       └── 0012-agent-read-surface.md   # What a future agent may read
│
└── .github/
    └── workflows/
        ├── validate.yml                 # Seven jobs on push and pull request
        └── refresh.yml                  # Monthly refresh, opens a pull request
```

---

## Documentation index

| Document | What does it answer? |
|----------|----------------------|
| [`docs/LAYERS.md`](./docs/LAYERS.md) | Which layer does a file belong to, how is it produced and validated, and what is irreplaceable? |
| [`docs/PROVENANCE.md`](./docs/PROVENANCE.md) | Where does each field come from, how often is it refreshed, how do I audit it, and what is not covered? |
| [`docs/JOINS.md`](./docs/JOINS.md) | Which registries reference `mic`, at what granularity, and what does this registry not answer? |
| [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) | What invariants does every release refuse on, and what are the operator-hygiene rules? |
| [`docs/action_types.md`](./docs/action_types.md) | What do `OPERATING`, `SEGMENT` and each status mean, and which combinations occur? |
| [`docs/source_format.md`](./docs/source_format.md) | Exactly what does SWIFT's file contain (headers, value sets, dates)? |
| [`docs/mic_lei_source_format.md`](./docs/mic_lei_source_format.md) | What did the MIC to LEI reconnaissance find, and what would reopen it? |
| [`docs/mic_bic_source_format.md`](./docs/mic_bic_source_format.md) | Which sources were checked for a MIC to BIC mapping, and what would reopen it? |
| [`docs/decisions/v1.0.0-decisions.md`](./docs/decisions/v1.0.0-decisions.md) | Why was each v1.0.0 design choice (D1 to D17) made? |
| [`docs/decisions/`](./docs/decisions) | Why was each later choice made? One ADR per decision, twelve in all (0001 to 0012). |
| [`docs/decisions/0012-agent-read-surface.md`](./docs/decisions/0012-agent-read-surface.md) | What may a future agent read, and at what freshness? |
| `docs/v<version>-verification.md` | What did the release gate print when this version shipped? |
| [`CHANGELOG.md`](./CHANGELOG.md) | What changed in each release, and what is queued under `[Unreleased]`? |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | What are the four rules, and how do I fix data, add a field, add an export or cut a release? |
| `wrappers/*/README.md` | What is the full API of each wrapper? |

---

## Contributing

Open an issue before starting a large change. Data corrections go through a tool, never a hand edit of `iso10383.json`. The quick workflow, in the order the release script expects:

1. Set up (once): `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt && pip install -e wrappers/python`
2. Change the source or the tool. A data change means a new SWIFT file: `python3 tools/fetch_swift_mic.py --download --force --strict --version "$(cat VERSION)"`
3. Validate: `python3 tools/validate.py` (must exit 0)
4. Regenerate the derived files, Layer 2 then Layer 3:
   `python3 tools/export_csv.py && python3 tools/export_sql.py && python3 tools/export_parquet.py && python3 tools/sync_wrappers.py`
5. Check the drift gates: `python3 tools/export_csv.py --check && python3 tools/export_sql.py --check && python3 tools/export_parquet.py --check && python3 tools/sync_wrappers.py --check`
6. Check the conventions: `python3 tools/check_version_consistency.py && python3 tools/check_mojibake.py && python3 tools/check_release_claims.py "$(cat VERSION)"`
7. Run the tests: `python3 -m pytest tests/ -q`
8. Run every wrapper suite: `bash tools/check_cross_language.sh --strict` (needs `node`, `cargo` and `go`; drop `--strict` if you touched only Python)
9. Rehearse the release: `bash scripts/release.sh <version> --dry-run`
10. Open a pull request. CI runs seven jobs.

**Source discipline.** SWIFT's published MIC file is the only accepted source: no third-party lists, no mirrors, no Wikipedia, no aggregators. If a value cannot be traced to the published file, the field stays `null`.

**Four rules for scripts.**

1. No heredocs for patch scripts: write `/tmp/script.py`, run it standalone, check its exit code.
2. `set -euo pipefail` at the top of every shell script.
3. Adversarial tests on `/tmp` copies, never on the working tree.
4. File-first: write a script to a file, run the file, read the output.

Everything else, including how to add a field, an export format or a wrapper method, is in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

---

## Known limitations

Stated plainly, because a canonical registry is a claim and a claim needs its edges drawn.

- **One source.** Everything traces to SWIFT's published `ISO10383_MIC.csv`. A MIC that appears in a national exchange's own publications but not in that file is not here.
- **Monthly lag.** SWIFT publishes on the second Monday of the month and the refresh runs on the 15th, so a venue that opens mid-month is absent until the next cycle. This is a property of the standard and of ADR 0011's batch shape, not a defect.
- **A snapshot, not a history.** `UPDATED` is transient: it means "changed since the last publication" and reverts to `ACTIVE` later. No file records what changed in a MIC or when beyond the four date fields. Replaying an earlier state means checking out an earlier tag; Layer 0 keeps only the current raw file.
- **No LEI, BIC or ISIN companion.** The `lei` field carries SWIFT's published LEI where there is one (2,254 of 2,883 entries; 629 are null). GLEIF's mapping was found to be a subset of that field and a companion file was declined ([ADR 0008](./docs/decisions/0008-mic-lei-companion-declined.md)). No MIC to BIC source file was found ([ADR 0009](./docs/decisions/0009-mic-bic-companion-declined.md)). MIC to ISIN is out of scope (D11).
- **No trading currency, operating hours or regulatory status.** Trading currency is not stored per MIC; the nearest derivation is `country_code` to ISO 4217, which cannot express a venue trading in a non-local currency. Operating hours belong to Exchange Calendar. Regulatory status is out of scope (D11).
- **Sparse optional fields.** 1,867 entries have no `acronym`, 1,494 no `legal_entity_name`, 1,324 no `note`, 163 no `website` and 1,896 no `last_validation_date`. A null is the source's silence, never a guess.
- **Three MICs have no country.** `BILT`, `XOFF` and `XXXX` carry `ZZ`, which is not an ISO 3166 code; the validator skips it.
- **Text is as published.** Names and websites are upper case, as SWIFT supplies them. The registry does not normalise.
- **The SQL export is a reference table.** It carries 11 of the 17 fields, and only the PostgreSQL and SQLite files declare the self-referencing foreign key.
- **Chains are capped at eight hops.** The deepest in this snapshot is three levels. A deeper chain is refused by the parser and the validator.
- **The cross-checks cover 74 MICs, not all of them.** Exchange Calendar references 74 MICs; the other 2,809 have no sibling that checks them.
- **Network-dependent gates.** `check_*_current.py` and `gen_*_snapshot.py --check` reach GitHub; offline, they cannot run.
- **Language packages are not published** to PyPI, npm, crates.io or a Go proxy. Install from a clone.
- **No XLSX or XML distribution.** SWIFT's original offers both; this registry publishes JSON, SQL, CSV, TSV and Parquet only.

---

## FAQ

**Why does every segment have a parent, and why does every operating MIC point to itself?**
So `operating_mic` is `NOT NULL` everywhere and a join never needs a special case. The root is reached by walking `operating_mic` until it equals `mic` ([ADR 0002](./docs/decisions/0002-operating-segment-model.md)).

**Why is there no `root_mic` column?**
It would be a second value to keep consistent with `operating_mic` when a parent changes. Eight chains have three levels, so the walk is short, and the [worked example](#worked-example-a-venue-tree-in-ten-commands) shows it in pandas.

**What does a null mean?**
The source file had no value, and the field stays null rather than carrying a guess. In JSON it is `null`, in CSV an empty field, in Parquet a null, in SQL `NULL`.

**What does `UPDATED` mean, and should I treat it as active?**
It means the entry changed since the last publication (21 entries in this snapshot). It is not expired. A consumer that wants "currently valid" should accept `ACTIVE` and `UPDATED` and exclude `EXPIRED`.

**Why does `validate.py` fail when Exchange Calendar references an unknown MIC?**
Cross-registry checks have been blocking since v1.0.1, and the allowlist of tolerated gaps is empty. Fix the sibling or the registry; adding an allowlist entry needs an ADR amendment ([ADR 0007](./docs/decisions/0007-cross-registry-allowlist.md)). `--advisory` downgrades the failure to a warning.

**Why does `check_cross_language.sh --strict` fail on my machine?**
A wrapper toolchain (`node`, `cargo` or `go`) is missing, and `--strict` refuses to pass with a skipped suite. Install the toolchain or run without `--strict`.

**Why does the SQL export lack `lei` and `website`?**
It is the foreign-key-ready minimum, 11 columns. The CSV, TSV and Parquet carry all 17.

**Why are the exports committed instead of built on demand?**
So a consumer can download one file and run nothing, and so drift between the JSON and a derived file fails CI instead of reaching users.

**How do I know which registry version produced a file I was handed?**
JSON: `meta.version`. Parquet: footer key `iso10383.version`. SQL: the `-- version:` comment on line 3.

**Why can't I `pip install iso10383-registry`?**
Publication is deferred until a consumer needs it (see [What's next](#whats-next)). Use `pip install -e wrappers/python` from a clone.

**Why does `iso10383` not exist as a command after installing the Python wrapper?**
The CLI is a repository artifact. Use `python3 tools/iso10383_cli.py` or `bin/iso10383` from a checkout.

---

## Consumed by

ISO 10383 is the leaf of the MIC join graph: other registries reference `mic`; this one references none of them except for validation. [`docs/JOINS.md`](./docs/JOINS.md) names every edge. Each row gives the proof that exists in this repository, and says where the proof lives in a sibling repository that is not part of this tree.

| Project | Edge | Proof |
|---------|------|-------|
| [Exchange Calendar](https://github.com/slimissa/exchange-calendar) | `exchanges/*.json` carries `mic` (or `code`); JOINS records 74 entries at v2.15.0 | `tools/exchange_calendar_snapshot.json` (74 MICs, v2.15.4) reproduced by `gen_exchange_calendar_snapshot.py --check`; `check_exchange_calendar_current.py --strict` compares it with the live sibling; `validate.py` fails if any of the 74 is missing here |
| [ISO 3166](https://github.com/slimissa/iso3166) | Reverse edge: this registry's `country_code` joins ISO 3166's alpha-2 codes | `tools/iso3166_snapshot.json` (252 codes, v1.6.9), reproduced by `gen_iso3166_snapshot.py --check`; `validate.py` checks every `country_code` except `ZZ` against it |
| Asset Identifiers | `exchange` and `listings[].exchange` reference a MIC, "Either" granularity | Declared in that repository's `schema.json`, per `docs/JOINS.md`. JOINS records that the public repository holds only the schema and a fixture, so the edge is verified against a schema, not records. Not checkable from this tree. |
| Corporate Actions | `exchange` per action | `docs/JOINS.md` marks it planned and records that none of its 240 actions carries an `exchange` field as of 2026-10-11. Not checkable from this tree. |
| [Tempus](https://github.com/slimissa/Tempus), [LAS_Shell](https://github.com/slimissa/Las_shell) | Compile-time `@market_context` validation (Tempus); market status and prompt display (LAS_Shell) | None in this repository. Both are named as intended consumers; neither appears in `docs/JOINS.md`, and no artifact here depends on them. |

No external adopter is recorded. *Using this registry in your project? Open a pull request to add a row.*

---

## License and author

Apache 2.0. See [`LICENSE`](./LICENSE). The MIC data is factual information sourced from SWIFT's published ISO 10383 file; the compilation, schema, tooling, wrappers and documentation are licensed works.

**Le P'tit**, [github.com/slimissa](https://github.com/slimissa)

---

## What's next

Nothing is scheduled. D14 forbids a roadmap before the previous release has shipped, and v1.0.4 has; the next release follows the first trigger below that fires.

| Deferred item | Trigger to start | Where decided |
|---------------|------------------|---------------|
| **Wrapper publication** to PyPI, npm, crates.io and a Go proxy | A consumer tries to install a wrapper from a package registry, or needs one | README (this section), [ADR 0010](./docs/decisions/0010-platform-charter.md) reopening condition 2 |
| **MIC to LEI companion** | A MIC to LEI pair in GLEIF's file that `iso10383.json` does not carry, or a MIC whose LEI differs between SWIFT's field and GLEIF's file; checked by re-running the procedure in `docs/mic_lei_source_format.md` (no CI monitors it) | [ADR 0008](./docs/decisions/0008-mic-lei-companion-declined.md) |
| **MIC to BIC companion** | A source file appears with a named publication, redistributable terms and a counted reconnaissance | [ADR 0009](./docs/decisions/0009-mic-bic-companion-declined.md) |
| **A streaming or sub-monthly refresh** | SWIFT offers a push or change feed, a consumer needs freshness under a day, or a source changes continuously | [ADR 0011](./docs/decisions/0011-reprocessing.md) |
| **A feature outside the charter** (hours, regulatory status, trading currency, MIC to ISIN) | A consumer asks for it; it is then a new decision, not an extension | [ADR 0010](./docs/decisions/0010-platform-charter.md) |
| **An agent and its proposal schema** | An agent is built; the read-surface table and a freshness check for `docs/JOINS.md` drift are the prerequisites | [ADR 0012](./docs/decisions/0012-agent-read-surface.md) |
| **`check_workflows_covered` in `release.sh`** | A second per-push workflow is added; the poll cannot otherwise tell that an expected workflow has not started | `scripts/release.sh` header, [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) invariant 6 |
| **An ISO 4217 snapshot** | A field that references a currency is added to this registry | `tools/check_iso4217_current.py` docstring |

See [`CHANGELOG.md`](./CHANGELOG.md) for release history and [`docs/decisions/`](./docs/decisions/) for locked decisions.
