# ISO 10383 MIC Registry

**A canonical, versioned, machine-readable registry of ISO 10383 Market Identifier Codes: 2,893 MICs (1,599 operating, 1,294 segment) with their parent chains, status, country, category and operator.**

One JSON file is the source of truth. Everything else (SQL, CSV, TSV, Parquet, four language wrappers, a command-line tool, two vendored cross-registry snapshots) is regenerated from it or checked against it, and re-verified on every push.

[![Validate](https://github.com/slimissa/iso10383/actions/workflows/validate.yml/badge.svg)](https://github.com/slimissa/iso10383/actions/workflows/validate.yml)
[![Refresh](https://github.com/slimissa/iso10383/actions/workflows/refresh.yml/badge.svg)](https://github.com/slimissa/iso10383/actions/workflows/refresh.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Schema](https://img.shields.io/badge/schema-1.0.0-green.svg)](./schema.json)
[![Registry](https://img.shields.io/badge/registry-1.1.3-orange.svg)](./CHANGELOG.md)
[![MICs](https://img.shields.io/badge/MICs-2893-blue.svg)](./iso10383.json)
[![Wrappers](https://img.shields.io/badge/wrappers-4-purple.svg)](./wrappers/)
[![Tests](https://img.shields.io/badge/tests-265-success.svg)](./tests/)

---

## Contents

1. [At a glance](#1-at-a-glance)
2. [Why this exists](#2-why-this-exists)
3. [Where to start](#3-where-to-start)
4. [Quick start](#4-quick-start)
5. [The data model: five layers](#5-the-data-model-five-layers)
6. [The registry file](#6-the-registry-file)
7. [The hierarchy layer](#7-the-hierarchy-layer)
8. [Flat exports: SQL, CSV, TSV, Parquet](#8-flat-exports-sql-csv-tsv-parquet)
9. [Bundled copies and vendored snapshots](#9-bundled-copies-and-vendored-snapshots)
10. [Worked example: a venue tree in ten commands](#10-worked-example-a-venue-tree-in-ten-commands)
11. [Command-line interface](#11-command-line-interface)
12. [Language wrappers](#12-language-wrappers)
13. [Validation](#13-validation)
14. [Continuous integration](#14-continuous-integration)
15. [Release pipeline](#15-release-pipeline)
16. [Versioning](#16-versioning)
17. [Project structure](#17-project-structure)
18. [Documentation index](#18-documentation-index)
19. [Contributing](#19-contributing)
20. [Known limitations](#20-known-limitations)
21. [FAQ](#21-faq)
22. [Consumed by](#22-consumed-by)
23. [License and author](#23-license-and-author)
24. [What's next](#24-whats-next)

---

## 1. At a glance

| | |
|---|---|
| **MICs** | 2,893: 1,599 operating, 1,294 segment |
| **Status** | 2,304 `ACTIVE`, 9 `UPDATED`, 580 `EXPIRED`. Expired entries stay in the file, with their `expiration_date`. |
| **Hierarchy** | Every segment's parent chain ends at an operating MIC. 1,281 segments sit directly under an operating MIC, 8 sit under another segment (three levels in all). 0 broken chains. |
| **Countries** | 149 distinct `country_code` values: 148 ISO 3166-1 alpha-2 codes plus `ZZ` (3 MICs: `BILT`, `XOFF`, `XXXX`) |
| **Market categories** | 14 of the 16 ISO codes are in use (`ARMS` and `CTPS` are defined, unassigned) |
| **Flat exports** | 9 derived files: SQL (4 dialects), CSV/TSV (4 variants), Parquet (1 file) |
| **Wrappers** | 4: Python, JavaScript, Rust, Go, each bundling a byte-identical copy of the JSON and passing the same 22-case fixture |
| **Release gate** | 18 checks in [`scripts/release.sh`](./scripts/release.sh) |
| **Manifest claims** | One list per released version plus a `doc-facts` list in [`tools/release_claims.json`](./tools/release_claims.json); the counts are in `registry_release.json` (`counts.claims`) |
| **Tests** | 265: 147 root and 118 in the wrappers (31 + 29 + 27 + 31) |
| **Version** | One version number at nine sites (the `VERSION` file; the badge above shows it); the schema is 1.0.0 |
| **Source** | SWIFT's published `ISO10383_MIC.csv`, snapshot 2026-11-09, `sha256:1d7f8aad...` recorded in `meta.source_hash`. The source of truth is [`iso10383.json`](./iso10383.json), validated against [`schema.json`](./schema.json). |
| **Around the data** | Five layers ([`docs/LAYERS.md`](./docs/LAYERS.md)); a CLI with nine subcommands; two vendored snapshots (ISO 3166 and Exchange Calendar, each pinned in its `.meta.json`); three CI workflows; a [`Makefile`](./Makefile) with `package`, `build-wheel`, `test` and `registry-release`; one example, [`examples/orders-5k`](./examples/orders-5k) |
| **Security** | See [SECURITY.md](./SECURITY.md); integrity via `registry_release.json` |
| **Dependencies and license** | The JSON needs none. Python, JavaScript and Go wrappers have none; the Rust wrapper depends on `serde` and `serde_json`. Build time: `jsonschema`, `pyarrow==25.0.1`, `pytest`, `pyyaml`. Apache 2.0. |

### Reproduce every number

Each command runs from a clone, prints one line, and is the source of the figure above (the line it printed when this README was written is shown).

| Figure | Command | Prints |
|--------|---------|--------|
| MICs | `python3 -c "import json; print(len(json.load(open('iso10383.json'))['mics']))"` | `2893` |
| Operating / segment | `python3 -c "import json,collections as c; m=json.load(open('iso10383.json'))['mics']; print(sorted(c.Counter(x['mic_type'] for x in m).items()))"` | `[('OPERATING', 1599), ('SEGMENT', 1294)]` |
| Active / updated / expired | `python3 -c "import json,collections as c; m=json.load(open('iso10383.json'))['mics']; print(sorted(c.Counter(x['status'] for x in m).items()))"` | `[('ACTIVE', 2304), ('EXPIRED', 580), ('UPDATED', 9)]` |
| Segments under an operating MIC / under a segment | `python3 -c "import json; m={x['mic']:x for x in json.load(open('iso10383.json'))['mics']}; s=[x for x in m.values() if x['mic_type']=='SEGMENT']; print(sum(m[x['operating_mic']]['mic_type']=='OPERATING' for x in s), sum(m[x['operating_mic']]['mic_type']=='SEGMENT' for x in s))"` | `1281 8` |
| Broken chains | `python3 tools/validate.py \| tail -1` | `0 broken chains` |
| Distinct country codes | `python3 -c "import json; print(len({x['country_code'] for x in json.load(open('iso10383.json'))['mics']}))"` | `149` |
| Market categories in use | `python3 -c "import json; print(len({x['market_category'] for x in json.load(open('iso10383.json'))['mics']}))"` | `14` |
| Flat exports | `ls iso10383* \| grep -v 'json$' \| wc -l` | `9` |
| Wrappers | `ls wrappers \| wc -l` | `4` |
| Release-gate checks | `grep -c '^gate ' scripts/release.sh` | `17` |
| Manifest claims in the file | `python3 -c "import json; d=json.load(open('tools/release_claims.json')); print(sum(len(v) for v in d.values() if isinstance(v, list)))"` | the value of `counts.claims.in_file` in `registry_release.json` |
| Claims the current gate verifies | `python3 tools/check_release_claims.py "$(cat VERSION)" \| tail -1` | `all N claim(s) verified`, where N is `counts.claims.verified` in `registry_release.json` |
| Root tests | `python3 -m pytest tests/ -q 2>&1 \| tail -1 \| cut -d' ' -f1-2` | `147 passed` |
| Version, nine sites | `python3 tools/check_version_consistency.py \| tail -1` | `OK: all sites agree on <VERSION>`, where `<VERSION>` is the contents of the `VERSION` file |
| Layers | `grep -c '^## Layer' docs/LAYERS.md` | `5` |
| CLI subcommands | `grep -c 'add_parser(' tools/iso10383_cli.py` | `9` |
| CI workflows | `ls .github/workflows \| wc -l` | `3` |

The `0 broken chains` line that `validate.py` prints is a success message: the script reaches it only when no error was raised. The count itself is `meta.broken_chains` in `iso10383.json` and the output of `iso10383_cli.py check`.

---

## 2. Why this exists

Every trading system, quant library and fintech app maintains its own MIC list, and the lists drift. Some keep expired codes and some drop them. Some flatten the operating-versus-segment hierarchy, and some assume every segment hangs directly off an operating MIC, when in this data eight segments hang off another segment.

**A MIC is the join key that financial data uses to say "where".** An instrument trades on a MIC, a quote comes from a MIC, a filing references a MIC, and an exchange calendar is keyed by one. The argument of this registry is that venue identity is a **join dimension**: every fact table needs it and none should own it. A fact table that carries only a MIC inherits country, category, operator, parent venue and expiry from one versioned file instead of copying them, and a change in SWIFT's monthly publication reaches every consumer through a version bump rather than through a hundred hand-edited lists.

One versioned, schema-validated JSON file, guarded by CI, replaces the lists. The JSON is the contract; the SQL, CSV, Parquet, wrapper and CLI forms are ways to consume it without writing a parser. The registry deliberately stays narrow: it reproduces SWIFT's file and nothing else (see [Known limitations](#20-known-limitations)).

Two other things are facts here and not metadata. **Time:** a venue that closed is still a row, with its `expiration_date` (580 of them, 96 on or after 2024-01-01), so a fact table from 2021 still joins. **Hierarchy:** the path from a segment to its operator is explicit in the data, not implied by a naming convention (see [The hierarchy layer](#7-the-hierarchy-layer)). **Currency is not here**: the registry does not store a trading currency, and says so under [Known limitations](#20-known-limitations).

---

## 3. Where to start

| If you are... | Start with |
|---------------|------------|
| A programmer who wants a library | [Language wrappers](#12-language-wrappers) |
| A database engineer | [`iso10383.postgresql.sql`](./iso10383.postgresql.sql) and the other dialects; see [SQL](#sql) |
| An analyst in Excel, Sheets, pandas or DuckDB | [`iso10383.csv`](./iso10383.csv) or [`iso10383.parquet`](./iso10383.parquet); see [CSV and TSV](#csv-and-tsv) and [Parquet](#parquet) |
| A shell user | [Command-line interface](#11-command-line-interface) |
| Asking "which venues sit under this operator?" | `iso10383 segments XJPX` and the [worked example](#10-worked-example-a-venue-tree-in-ten-commands) |
| Evaluating whether to trust the data | [`docs/PROVENANCE.md`](./docs/PROVENANCE.md), [Validation](#13-validation) and [Known limitations](#20-known-limitations) |
| Running the monthly refresh | [Refreshing the data](#refreshing-the-data) |
| Cutting a release | [Release pipeline](#15-release-pipeline) and [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) |
| Wondering why a field is null | [`docs/ENRICHMENT.md`](./docs/ENRICHMENT.md) |
| Weighing "copy the venue fields" against "join on the MIC" | [`examples/orders-5k`](./examples/orders-5k) and [the worked example](#10-worked-example-a-venue-tree-in-ten-commands) |
| Regenerating everything after a change | [`make package`](#build-and-test-with-make) |
| Contributing a correction or a tool change | [Contributing](#19-contributing) and [`CONTRIBUTING.md`](./CONTRIBUTING.md) |
| Joining MICs from another registry | [`docs/JOINS.md`](./docs/JOINS.md) and [Consumed by](#22-consumed-by) |

---

## 4. Quick start

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

### Command line

```bash
python3 tools/iso10383_cli.py parent XTKS      # XTKS -> XJPX
```

The CLI is a repository artifact, covered in [Command-line interface](#11-command-line-interface).

### Build and test with make

```bash
make package      # regenerate the nine flat exports and the four wrapper copies; idempotent
make build-wheel  # package, then build the Python wheel and sdist (needs: pip install build)
make test         # root pytest, then check_cross_language.sh --strict
make registry-release  # regenerate registry_release.json (after make package)
```

`make package` is the one command to run after modifying `iso10383.json`. It runs `export_csv.py`, `export_sql.py`, `export_parquet.py` and `sync_wrappers.py`; running it twice changes nothing the second time.

---

## 5. The data model: five layers

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

- **Layer 0 to 1.** `tools/fetch_swift_mic.py` is the only tool that reads `raw/`. Its parser raises on an unknown `OPRT/SGMT` or status value, an operating MIC that does not self-reference, a segment that does, a malformed date, a missing column or an unexpected one, and it writes nothing when it raises.
- **Layer 1 to 2.** Each exporter has a `--check` mode that regenerates in memory and compares with the committed file. `export_parquet.py --check` compares bytes.
- **Layer 1 to 3.** `tools/sync_wrappers.py --check` compares the four bundled copies with `iso10383.json`.
- **Layer 1 to 4.** `tools/validate.py` reads the two snapshots (and no sibling repository) at validation time; `gen_*_snapshot.py --check` reproduces each snapshot from its pinned upstream tag.

Only Layer 0 cannot be regenerated from this repository. **Back up `raw/`.** The regeneration order is: Layer 0 to Layer 1 with `fetch_swift_mic.py`, then the exporters and `sync_wrappers.py`; the snapshots are regenerated separately by their own scripts.

[ADR 0010](./docs/decisions/0010-platform-charter.md) records what the platform is and is not, and [ADR 0011](./docs/decisions/0011-reprocessing.md) records that reprocessing from Layer 0 is not a general capability: replaying history means checking out a tag.

---

## 6. The registry file

[`iso10383.json`](./iso10383.json) has two top-level keys, `meta` and `mics`. `mics` is an array sorted by `mic`. Output is deterministic (`json.dumps(..., sort_keys=True)`, LF line endings, trailing newline), and two runs on the same raw file produce byte-identical JSON.

```json
{
  "meta": {
    "version": "<the contents of VERSION>",
    "updated": "2026-11-09",
    "source_snapshot": "2026-11-09",
    "source_url": "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv",
    "source_hash": "sha256:79de0f7704e260bd49b0d2439f3084891cabc93481da8bdbaa716e15a27211ed",
    "counts": {
      "operating": 1599, "segment": 1294,
      "active": 2304, "updated": 9, "expired": 580,
      "total": 2893
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

Why each nullable field is null, field by field, is in [`docs/ENRICHMENT.md`](./docs/ENRICHMENT.md). Ten fields are never null in this snapshot: the four non-nullable keys plus `market_name`, `country_code`, `creation_date`, `last_update_date`, `market_category` and `city`.

### Coverage

| Group | Count |
|-------|------:|
| Operating | 1,599 (1,331 active, 264 expired, 4 updated) |
| Segment | 1,294 (973 active, 316 expired, 5 updated) |
| Total | 2,893 |
| Active / Updated / Expired | 2,304 / 9 / 580 |
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
| `ACTIVE` | In force | 2,304 |
| `UPDATED` | Changed since the last publication. Not a permanent state: it reverts to `ACTIVE` in a later snapshot. | 21 |
| `EXPIRED` | No longer in force; `expiration_date` is set | 580 |

**`market_category`**: sixteen codes from the ISO 10383 Release 2.0 factsheet. The 2026-11-09 snapshot uses 14.

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

<details>
<summary>The 149 values of <code>country_code</code></summary>

`AE` `AG` `AL` `AM` `AO` `AR` `AT` `AU` `AZ` `BA` `BB` `BD` `BE` `BG` `BH` `BM` `BO` `BR` `BS` `BW` `BY` `CA` `CH` `CI` `CL` `CM` `CN` `CO` `CR` `CV` `CW` `CY` `CZ` `DE` `DK` `DO` `DZ` `EC` `EE` `EG` `ES` `FI` `FJ` `FO` `FR` `GB` `GE` `GG` `GH` `GI` `GR` `GT` `GY` `HK` `HN` `HR` `HU` `ID` `IE` `IL` `IN` `IQ` `IR` `IS` `IT` `JM` `JO` `JP` `KE` `KG` `KH` `KN` `KR` `KW` `KY` `KZ` `LA` `LB` `LI` `LK` `LT` `LU` `LV` `LY` `MA` `MD` `ME` `MG` `MK` `MN` `MT` `MU` `MV` `MW` `MX` `MY` `MZ` `NA` `NG` `NI` `NL` `NO` `NP` `NZ` `OM` `PA` `PE` `PG` `PH` `PK` `PL` `PS` `PT` `PY` `QA` `RO` `RS` `RU` `RW` `SA` `SC` `SD` `SE` `SG` `SI` `SK` `SV` `SY` `SZ` `TH` `TN` `TR` `TT` `TW` `TZ` `UA` `UG` `US` `UY` `UZ` `VC` `VE` `VG` `VN` `VU` `ZA` `ZM` `ZW` `ZZ`

</details>

The multi-level chains (a segment whose parent is a segment) are in [The hierarchy layer](#7-the-hierarchy-layer).

Design decisions behind these fields are recorded in [`docs/decisions/v1.0.0-decisions.md`](./docs/decisions/v1.0.0-decisions.md) (D2 one array, D3 self-reference, D4 categories, D5 closed enums), [ADR 0002](./docs/decisions/0002-operating-segment-model.md) (operating/segment model) and [ADR 0004](./docs/decisions/0004-market-category-codes.md) (category codes).

---

## 7. The hierarchy layer

Every entry has an `operating_mic`. An operating MIC points to itself. A segment points to its **direct parent**, and the parent of a segment can itself be a segment, so the hierarchy is a tree of unknown depth, not a two-level list ([ADR 0002](./docs/decisions/0002-operating-segment-model.md), D2 and D3 in [`v1.0.0-decisions.md`](./docs/decisions/v1.0.0-decisions.md)).

| Measure | Value |
|---------|------:|
| Operating MICs | 1,599 |
| Operating MICs that have at least one segment | 376 |
| Segments directly under an operating MIC (one hop to the root) | 1,281 |
| Segments under another segment (two hops to the root) | 8 |
| Chains of three hops or more | 0 |
| Broken chains (cycle, missing parent, deeper than 8 hops) | 0 |

The parser and the validator refuse a chain longer than eight hops, a cycle, and a missing parent ([`tools/validate.py`](./tools/validate.py), `chain_terminates`). The deepest chain in this snapshot has three entries.

### The eight chains of three entries

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

`XEAS` is the Equiduct segment (`EXPIRED`) under `XEQT` (Boerse Berlin Equiduct Trading), which is under `XBER`, the operating MIC for Boerse Berlin. Grouping by `operating_mic` alone credits `XEAS` to `XEQT` and never to `XBER`.

### There is no `root_mic`

A stored root would be a second value to keep in sync with `operating_mic` whenever a parent changes ([ADR 0002](./docs/decisions/0002-operating-segment-model.md); [`docs/JOINS.md`](./docs/JOINS.md)). The root is computed by walking `operating_mic` until it equals `mic`. With at most three entries in a chain the walk is short.

In pandas:

```python
import pandas as pd
df = pd.read_parquet("iso10383.parquet")
by = df.set_index("mic")

def root(m):
    while by.at[m, "operating_mic"] != m:
        m = by.at[m, "operating_mic"]
    return m

df["root"] = df["mic"].map(root)
print((df.root != df.operating_mic).sum())        # 8
print(df.root.value_counts().head(3).to_string())
# root
# XSTO    37
# XMTS    25
# XWAR    24
```

Eight MICs have a root different from their direct parent (the chains above). Grouping by `operating_mic` alone would credit `XBXO` and `XNIM` with their own segments but not with the ones one level further down, which is why the walk is needed.

In SQL, with the 11-column export (`iso10383.sqlite.sql` loaded into a database), a recursive query returns the same eight rows:

```sql
WITH RECURSIVE walk(mic, cur, hops) AS (
  SELECT mic, mic, 0 FROM mics
  UNION ALL
  SELECT w.mic, m.operating_mic, w.hops + 1
  FROM walk w JOIN mics m ON m.mic = w.cur
  WHERE m.operating_mic <> w.cur
)
SELECT mic, cur AS root, MAX(hops) AS hops
FROM walk GROUP BY mic HAVING MAX(hops) >= 2 ORDER BY mic;
-- EXPA|XMIL|2, ICAT|ICAP|2, LIQH|ICPM|2, NBXO|XNAS|2,
-- PCDS|XTUP|2, THRD|XNAS|2, VRXP|XPAR|2, XEAS|XBER|2
```

The CLI gives the direct parent only (`iso10383 parent XEAS` prints `XEAS -> XEQT`); walking further is a loop over `parent`, or the queries above.

---

## 8. Flat exports: SQL, CSV, TSV, Parquet

All nine flat exports are Layer 2. They are regenerated from `iso10383.json`, committed, and compared in CI by each generator's `--check` mode. `tools/export_columns.py` is the single source of column order for every exporter.

| Artifact | Columns | Rows | Generator |
|----------|--------:|-----:|-----------|
| `iso10383.sql`, `.postgresql.sql`, `.mysql.sql`, `.sqlite.sql` | 11 (`mics`) | 2,893 | `tools/export_sql.py` |
| `iso10383.csv`, `.excel.csv`, `.european.csv`, `.tsv` | 17 | 2,893 | `tools/export_csv.py` |
| `iso10383.parquet` | 17 | 2,893 | `tools/export_parquet.py` |

The column sets are nested on purpose. The 11 SQL columns are the foreign-key-ready minimum (`mic`, `mic_type`, `status`, `operating_mic`, `market_name`, `country_code`, `market_category`, and the four dates). The 17 CSV and Parquet columns append `legal_entity_name`, `acronym`, `lei`, `city`, `website` and `note` for human analysis, in that order.

### SQL

Four self-contained files, each in one transaction (`BEGIN;` ... `COMMIT;`) and safe to run twice.

| File | Target | Idempotency | Foreign key |
|------|--------|-------------|-------------|
| [`iso10383.sql`](./iso10383.sql) | Generic dialect: `ON CONFLICT DO NOTHING` (PostgreSQL 9.5+, SQLite 3.24+). Not SQL-92: it will not run on SQL Server, Oracle or Db2. | `ON CONFLICT DO NOTHING` | none declared |
| [`iso10383.postgresql.sql`](./iso10383.postgresql.sql) | PostgreSQL 12+ | `ON CONFLICT (mic) DO NOTHING` | `fk_mics_operating`, deferrable |
| [`iso10383.mysql.sql`](./iso10383.mysql.sql) | MySQL 8+ / MariaDB 10.4+ | `INSERT IGNORE`, one multi-row statement | none declared |
| [`iso10383.sqlite.sql`](./iso10383.sqlite.sql) | SQLite 3.37+ | `INSERT OR IGNORE` | declared, deferrable; with `PRAGMA foreign_keys = ON` the file loads cleanly |

Each file creates two tables, `market_categories` (16 rows) and `mics` (2,893 rows, `mic` primary key, `CHECK` constraints on `mic_type`, `status` and `market_category`), plus three indexes (`operating_mic`, `country_code`, `status`). `operating_mic` is `NOT NULL` in every dialect; operating MICs point to themselves. The PostgreSQL and SQLite files additionally declare the self-referencing foreign key, deferred so that a child row can load before its parent. The generic and MySQL files declare no foreign key.

```sql
-- Every venue under the Japan Exchange Group.
SELECT mic, market_name FROM mics WHERE operating_mic = 'XJPX';

-- Every active exchange in Germany.
SELECT mic, market_name FROM mics WHERE country_code = 'DE' AND status = 'ACTIVE';
```

**What is intentionally absent:** `legal_entity_name`, `lei`, `acronym`, `city`, `website` and `note`. The SQL export is a reference table for foreign keys, not a mirror of the JSON. For those fields use the CSV, the Parquet or the JSON.

### CSV and TSV

Four files, one per audience. LF line endings everywhere, headers always present, 17 columns, 2,893 data rows (2,894 lines). There is no comment header: it would break `pandas.read_csv` and violate RFC 4180.

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
print(df.shape)   # (2893, 17)
```

### Parquet

[`iso10383.parquet`](./iso10383.parquet): columnar, typed, snappy-compressed, one row group, 2,893 rows, readable by pandas, Polars, DuckDB, Spark and warehouse loaders. Columns follow `CSV_COLUMNS` (17).

Typing, because Parquet has a type system:

- `mic_type`, `status`, `country_code` and `market_category` are dictionary-encoded strings.
- `creation_date`, `last_update_date`, `last_validation_date` and `expiration_date` are `date32`, not text. pandas returns them as `datetime.date` objects (dtype `object`) with `None` for null; pass `date_as_object=False` to `to_pandas()` for `datetime64`.
- Null is a real null: `WHERE expiration_date IS NULL` returns the 2,317 non-expired rows.

**Footer metadata.** The footer carries `iso10383.version`, `iso10383.updated`, `iso10383.source_snapshot` and `iso10383.source_hash`, so a consumer who receives only the `.parquet` file can tell which registry version produced it. The footer's `iso10383.version` is one of the nine version sites.

```python
import pyarrow.parquet as pq
t = pq.read_table("iso10383.parquet")
print(t.schema.metadata[b"iso10383.version"])   # the contents of VERSION, as bytes
```

### Comparison semantics and the build pin

`export_csv.py --check` and `export_sql.py --check` compare bytes. `export_parquet.py --check` also compares **bytes** (`OK: iso10383.parquet in sync (2893 rows, bytes)`), because the Parquet writer sorts the footer dictionary before writing and two runs on the same `pyarrow` version produce identical files. Byte output depends on the `pyarrow` version, so [`constraints.txt`](./constraints.txt) pins `pyarrow==25.0.1`. [`requirements-dev.txt`](./requirements-dev.txt) applies it with `-c constraints.txt`, and every CI job that installs `pyarrow` (`validate-json`, `check-exports`, `check-cli` and `refresh.yml`) installs with `-c constraints.txt`. [`tests/test_pip_pins.py`](./tests/test_pip_pins.py) parses `validate.yml` and `refresh.yml` and fails, naming the file, job and line, if any `pip install` line that mentions `pyarrow` lacks `-c constraints.txt`; it runs in the root suite, which the release gate runs. It is a structural test because a substring claim cannot see a second, unpinned install line added next to a pinned one. [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) § Version-pinned byte outputs states the rule.

---

## 9. Bundled copies and vendored snapshots

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
| [`tools/iso3166_snapshot.json`](./tools/iso3166_snapshot.json) | one entry per alpha-2 code | `mics[].country_code` | 252 codes | ISO 3166, at the `source_version` in `iso3166_snapshot.meta.json` |
| [`tools/exchange_calendar_snapshot.json`](./tools/exchange_calendar_snapshot.json) | one entry per MIC | `mics[].mic` | 74 MICs | Exchange Calendar, at the `source_version` in `exchange_calendar_snapshot.meta.json` |

Each has a `.meta.json` sibling with `source_version`, `vendored_at`, `vendored_from`, and a nested `meta` object holding `review_by` and `refresh_cadence` (`monthly` for both). The snapshot files stay byte-for-byte as generated; the `.meta.json` records where they came from.

Each is produced by a generator that fetches the pinned tag named in its meta, never `main`: `tools/gen_iso3166_snapshot.py` reads `…/v<source_version>/iso3166.json`, and `tools/gen_exchange_calendar_snapshot.py` runs `git clone --branch v<source_version>`. Both have a `--check` mode that reproduces the committed snapshot from that tag and compares bytes. Both run in the `check-snapshots` CI job and in the release gate.

Two further mechanisms keep a snapshot honest, and they answer different questions:

- **Scheduled re-verification**: `tools/check_snapshot_freshness.py` fails when `review_by` has passed, whether or not anything upstream changed.
- **Cross-reference check**: `tools/check_iso3166_current.py` and `tools/check_exchange_calendar_current.py` compare the snapshot with the live sibling. A code or MIC set difference fails under `--strict`. A version-label drift prints `warning: version drift: ...` and does not change the exit code. A sibling that cannot be reached exits 1 (nothing was compared) unless `--advisory` is passed, which exits 0 and still prints the note.

The Exchange Calendar snapshot's 74 MICs are 68 operating-active, 3 segment-active and 3 expired operating MICs (`XJKT`, `XBSP`, `XTAD`); all 74 are in this registry. [`docs/exchange_calendar_mics.txt`](./docs/exchange_calendar_mics.txt) is a 74-line reference list of them.

---

## 10. Worked example: a venue tree in ten commands

A reproducible session: a shell pass against the CLI and a pandas read of the Parquet, then a runnable example that puts a number on the join argument. Every output below was produced from the committed files at version 1.1.0 (snapshot 2026-09-23). Run the first two parts from the repository root; the CLI is written `iso10383` for `python3 tools/iso10383_cli.py`.

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

The root of every MIC (a walk up `operating_mic`, because there is no `root_mic` column) is in [The hierarchy layer](#7-the-hierarchy-layer).

Expirations per year, from the same frame:

```python
exp = df[df.status == "EXPIRED"]
print(pd.to_datetime(exp.expiration_date).dt.year.value_counts().sort_index().tail(3).to_string())
# 2024    26
# 2025    24
# 2026    32
```

### The cost of copying: `examples/orders-5k`

[`examples/orders-5k`](./examples/orders-5k) is a runnable comparison of the argument in [Why this exists](#2-why-this-exists). `generate_facts.py` builds 5,000 fictional orders across 50 real venues, as a narrow table (the MIC only) and a wide one (registry fields copied in). `analyze.py` measures both and then simulates a registry change. **Real:** the 50 venues and their registry fields. **Synthetic:** every order. The example's own README says so line by line.

```bash
cd examples/orders-5k && pip install -r requirements.txt
python3 generate_facts.py && python3 analyze.py
```

```text
5,000 synthetic orders, 50 real venues, registry snapshot 2026-09-23

1. Storage
                    parquet   in memory    as CSV
   narrow           108,060     234,333   295,441
   wide             129,415     712,533   721,371
   copying adds 21,355 bytes of Parquet and 478,200 bytes in memory (95 per order)
   the join's other side, iso10383.parquet, is 202,257 bytes, shared by every table
   narrow + the whole registry file: 310,317 bytes, more than wide (129,415) in Parquet at this row count

2. Join on mic
   5,000 of 5,000 orders found their MIC in the registry
   joined fields equal the copied fields: True
   on the day the copy is made, the two layouts agree

3. A registry change (simulated; iso10383.parquet is not touched)
   ATLN: market_name changes; BAMX: status becomes EXPIRED
   registry rows to change:        2
   order rows the join corrects:   1,708 of 5,000, with no write to the orders
   order rows the copy leaves stale: 1,708
   to fix the copy, those rows must be found and rewritten
```

How to read it, and what it does not claim:

- **Parquet size is not the argument.** Dictionary encoding absorbs the repeated strings, so the copy adds about 20% to the file, and at 5,000 rows the registry file is larger than that saving.
- **Memory and text are.** In memory the wide table is about 3 times the narrow one; as CSV about 2.4 times.
- **Correctness is the difference.** On day one the join and the copy agree. After a registry change the join corrects every affected order with no write to the orders, and the copy keeps the old value until it is rewritten. The change in part 3 is simulated; `iso10383.parquet` is never written.
- **A copy is right when you want the value as of the order date.** Then record the registry version with the order instead of copying whole fields.


---

## 11. Command-line interface

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
| `check` | Built-in smoke test: `OK: 2893 MICs, 1599 operating, 1294 segment, 0 broken chains` |

**Global option:** `--registry PATH` (or the environment variable `ISO10383_REGISTRY`; default `./iso10383.json`). **Per-command options:** `--color {never,auto,always}`, `--no-color`, `--quiet`.

**Output modes**, mutually exclusive on every subcommand: `--json` (object or array), `--jsonl` (one object per line), `--csv`, `--tsv` (columns match `iso10383.csv` and `iso10383.tsv`), `--raw FIELD` (bare values, one per line).

MIC arguments and the `--country`, `--category`, `--status` and `--mic-type` filters are case-insensitive, as in the four wrappers: `iso10383 lookup xnys` finds `XNYS`, and `iso10383 list --country us` lists the same rows as `--country US`.

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

## 12. Language wrappers

Four wrappers, one contract. Each is verified against the shared fixture [`tests/cross_language_consistency.json`](./tests/cross_language_consistency.json) and each bundles a byte-identical copy of `iso10383.json` (see [Bundled copies](#layer-3-bundled-copies)).

| Language | Package | Source | Minimum | Import | Tests |
|----------|---------|--------|---------|--------|------:|
| Python | `iso10383-registry` | [`wrappers/python`](./wrappers/python) | Python 3.9 | `from iso10383 import MICRegistry` | 31 |
| JavaScript | `iso10383-registry` | [`wrappers/javascript`](./wrappers/javascript) | Node 18 | `const { MICRegistry } = require("./wrappers/javascript")` | 29 as `node --test` reports them (28 `test()` definitions plus the fixture-anchor module) |
| Rust | `iso10383-registry` | [`wrappers/rust`](./wrappers/rust) | edition 2021 | `use iso10383_registry::Registry;` | 27 |
| Go | `github.com/slimissa/iso10383/wrappers/go` | [`wrappers/go`](./wrappers/go) | Go 1.21 | `import iso10383 "github.com/slimissa/iso10383/wrappers/go"` | 31 |

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

The query surface is eleven methods in every wrapper: the ten operations above plus `all()`. The shared fixture, [`tests/cross_language_consistency.json`](./tests/cross_language_consistency.json), has 22 cases over those operations, and the four wrapper suites hold 31 + 29 + 27 + 31 = 118 tests.

### Verify every wrapper agrees

```bash
bash tools/check_cross_language.sh            # run all suites, report skips
bash tools/check_cross_language.sh --strict   # a skipped suite fails
```

The script runs the Python, JavaScript, Rust and Go suites, then `sync_wrappers.py --check`. It does not diff wrapper output: each suite checks the shared fixture independently. A suite whose toolchain (`node`, `cargo`, `go`) is missing prints `SKIP`; without `--strict` that does not fail the script. With `--strict`, as in the release gate and the `check-cross-language` job, a skipped suite exits 1. Exit 1 also means a suite failed; exit 2 means `python3` is missing or an argument is unknown. A clean strict run prints `OK: 5 suite(s) passed, 0 skipped`.

### The fixture-anchor rule

Tests must not hardcode fixture values. Each language reads its expected values from the shared fixture through an anchor module (`wrappers/python/tests/anchors.py`, `wrappers/javascript/test/fixture.js`), and `tests/test_fixture.py` validates the fixture itself, so a missing anchor fails at startup rather than silently.

---

## 13. Validation

[`tools/validate.py`](./tools/validate.py) has six independent layers, each runnable in isolation:

```bash
python3 tools/validate.py                       # all six
python3 tools/validate.py --only coverage       # repeatable
python3 tools/validate.py --skip cross-reference
python3 tools/validate.py --strict              # promote warnings to errors
python3 tools/validate.py --advisory            # cross-registry gaps become warnings
```

Exit codes: 0 pass (warnings allowed), 1 data error, 2 usage error (file not found), 3 schema violation or malformed JSON. A clean run prints `OK: 2893 MICs validated`.

### The release gate, in order

The 18 checks of [`scripts/release.sh`](./scripts/release.sh), in the order it runs them. Each is a `gate` call: the script records its exit code and stops on a non-zero one.

| # | Check | Tool | What it catches |
|--:|-------|------|-----------------|
| 1 | Version consistency | `check_version_consistency.py` | Any of the nine sites disagreeing; the schema version disagreeing with the schema badge |
| 2 | Six-layer validator | `validate.py` | Any data error in the six layers below |
| 3 | Registry freshness | `check_registry_freshness.py` | `meta.source_snapshot` more than 60 days old; takes `--today YYYY-MM-DD` |
| 4 | Snapshot freshness | `check_snapshot_freshness.py` | A vendored snapshot past its `review_by` date; takes `--today YYYY-MM-DD` |
| 5 | Mojibake | `check_mojibake.py` | Six byte patterns of UTF-8 / Latin-1 round-trip corruption (five literal signatures, one regex range), plus unclosed code fences; `--path` scans one file |
| 6 | Release claims | `check_release_claims.py "$VERSION"` | A documentation or version claim that no longer matches the tree |
| 7 | ISO 3166 drift | `check_iso3166_current.py --strict` | Snapshot code set differs from the live sibling (`--strict` fails; a version-label drift only warns; an unreachable sibling fails unless `--advisory`) |
| 8 | Exchange Calendar drift | `check_exchange_calendar_current.py --strict` | Snapshot MIC set differs from the live sibling (same severity rules, including the unreachable case) |
| 9 | CLI smoke test | `iso10383_cli.py check` | Counts or chain integrity wrong when read through the CLI |
| 10 | CSV/TSV export drift | `export_csv.py --check` | A derived file that is stale against `iso10383.json` |
| 11 | SQL export drift | `export_sql.py --check` | Same, for the four SQL files |
| 12 | Parquet export drift | `export_parquet.py --check` | Same, compared byte for byte (hence the `pyarrow==25.0.1` pin) |
| 13 | Wrapper sync | `sync_wrappers.py --check` | A bundled copy that differs from `iso10383.json`, or a missing one (`--allow-missing` tolerates a missing copy; a stale one still fails) |
| 14 | Root test suite | `python3 -m pytest tests/ -q` | Any of the 147 root tests, including the AST test (`tests/test_generators.py`) that forbids clock reads, aliased or not, in the snapshot generators |
| 15 | Cross-language | `check_cross_language.sh --strict` | A wrapper suite (Python, JavaScript, Rust or Go) that fails or cannot run; a skipped suite fails under `--strict` |
| 16 | ISO 3166 snapshot reproduction | `gen_iso3166_snapshot.py --check` | A committed snapshot that differs byte for byte from the one its pinned upstream tag produces |
| 17 | Exchange Calendar snapshot reproduction | `gen_exchange_calendar_snapshot.py --check` | Same, for the Exchange Calendar snapshot |
| 18 | Release manifest | `gen_registry_release.py --check --version "$VERSION"` | A `registry_release.json` that is stale against the tree, invalid against its schema, or missing |

### The six layers of `validate.py`

| Layer | What it checks |
|-------|----------------|
| **Schema** | JSON Schema draft-07; `additionalProperties: false` at every level; closed enums for `mic_type`, `status` and `market_category`; the 10 required keys |
| **Integrity** | MIC pattern `^[A-Z0-9]{4}$`, country pattern `^[A-Z]{2}$`, ISO 8601 dates, non-empty strings |
| **Business** | MIC uniqueness; operating MICs self-reference; segments do not; `EXPIRED` has an `expiration_date` |
| **Cross-reference** | Every segment chain terminates at an operating MIC (max 8 hops); every `country_code` except `ZZ` is in the ISO 3166 snapshot; every MIC in the Exchange Calendar snapshot is in the registry |
| **Ground truth** | Spot checks: `XNYS` (OPERATING, US), `XLON` (OPERATING, GB), `XTKS` (SEGMENT, JP), `XPAR` (FR) |
| **Coverage** | Operating >= 1,500, segment >= 1,000, total >= 2,500 |

### Checks that run outside the release gate

| Check | Where | What it catches |
|-------|-------|-----------------|
| Raw-to-curated parse | `fetch_swift_mic.py` (the refresh) | Unknown type or status values, bad self-reference, malformed dates, missing or unexpected columns, broken chains with `--strict` |
| Refresh diff | `refresh_diff.py` (the refresh) | NEW / EXPIRED / CHANGED / REMOVED counts between two registry files (CHANGED watches six fields); a REMOVED count above 0 exits 1 and opens the refresh PR as a draft |
| Python wrapper suite | `pytest wrappers/python/tests -q`, in `check-wrappers` and inside gate 15 | The 31 Python wrapper tests |
| SWIFT source health | `check-sources.yml`, weekly | SWIFT's file failing to download, or under 100,000 bytes (it opens an issue) |

There is no ISO 4217 check: ISO 10383 has no currency field and no ISO 4217 snapshot. The inactive tool that once stood in for one was removed in v1.0.5.

### Cross-registry checks are blocking

Cross-registry validation has been blocking by default since v1.0.1 (D6, D17): an unexpected gap is an error, and `--advisory` reverts to the v1.0.0 behaviour. The allowlist `tools/validate.py::KNOWN_EXCHANGE_CALENDAR_GAPS` is **empty**. Its three former entries (`XBEK`, `XNBO`, `XQSE`) were renamed upstream at Exchange Calendar v2.4.2 to `XBEY`, `XNAI` and `DSMD`, all present in this registry. The mechanism stays, and adding a MIC to the allowlist requires an ADR amendment ([ADR 0007](./docs/decisions/0007-cross-registry-allowlist.md)).

### Release claims

[`tools/release_claims.json`](./tools/release_claims.json) holds machine-checkable claims, each of the form `{file, contains}` or `{file, absent}`, in one list per released version plus a `doc-facts` list. `check_release_claims.py <version>` verifies the `doc-facts` set plus that version's set and exits non-zero on the first false one. The counts of each set are in `registry_release.json` (`counts.claims`), not in this prose. It runs in the `validate-json` CI job and in the release gate. The claims exist to stop classes of drift from coming back: a version string or count that disagrees with the tree, a tool name that no longer exists, mojibake, an unclosed code fence, a snapshot that disagrees with its meta, and the stale phrases a past audit removed (for example a wrong dialect label for the generic SQL file). Claims describe state, not intent ([`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) rule 6c).

### Tests

| Suite | Command | Tests |
|-------|---------|------:|
| Root (Python) | `python3 -m pytest tests/ -q` | 147 |
| Python wrapper | `python3 -m pytest wrappers/python/tests -q` | 31 |
| JavaScript | `(cd wrappers/javascript && node --test)` | 29 as `node --test` reports them (28 `test()` definitions plus the fixture-anchor module) |
| Rust | `(cd wrappers/rust && cargo test --quiet)` | 27 |
| Go | `(cd wrappers/go && go test ./... -count=1)` | 31 |
| **Total** | | **265** |

The Tests badge above reads 265, the sum of this table. The root suite is spread over seventeen files in `tests/`: `test_check_mojibake.py` (17), `test_cli.py` (18), `test_checks.py` (18), `test_export_sql.py` (12), `test_fetch_swift_mic.py` (2), `test_iso10383_codes.py` (11), `test_export_parquet.py` (9), `test_validate_schema.py` (10), `test_export_csv.py` (7), `test_wrappers.py` (7), `test_self_reference.py` (5), `test_fixture.py` (3), `test_scripts.py` (3), `test_pip_pins.py` (7), `test_generators.py` (6), `test_check_release_claims.py` (6), `test_check_registry_freshness.py` (6).

---

## 14. Continuous integration

Three workflows in [`.github/workflows`](./.github/workflows):

| Workflow | Runs on | Jobs | Protects against |
|----------|---------|------|------------------|
| **`validate.yml`** | push to `main`, pull requests to `main`, manual dispatch | seven, below | A stale derived file, a failing validator, a drifting wrapper, a snapshot that no longer reproduces, a corrupted text file |
| **`refresh.yml`** | 00:00 UTC on the 15th of every month, manual dispatch | one: download, parse, diff, regenerate, validate, open a pull request | A registry that silently falls behind SWIFT |
| **`check-sources.yml`** | 06:00 UTC every Monday, manual dispatch | one: fetch SWIFT's file; on failure open an issue | SWIFT's file moving, vanishing or shrinking between refreshes |

`check-sources.yml` is not a per-push workflow: it does not run on push and is not part of the release poll. It fetches the file with `urllib.request.urlopen`; if the download fails or the response is under 100,000 bytes it opens a GitHub issue, or comments on the one already open.

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

### Refreshing the data

SWIFT publishes the MIC file on the **second Monday of each month**; modifications become effective on the fourth Monday. `tools/check_registry_freshness.py` fails CI when `meta.source_snapshot` is more than **60 days** old, two missed publication cycles, which signals that the update process broke rather than that the source is late.

#### The monthly process

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

#### Audit

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

## 15. Release pipeline

Releases are cut by [`scripts/release.sh`](./scripts/release.sh):

```bash
bash scripts/release.sh <version> --dry-run   # print every step; changes nothing
bash scripts/release.sh <version>             # release
```

The script conforms to [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md), the pattern shared across the registry family, and its header names two divergences: one per-push workflow is polled today, and the tag-move procedure is recovery-only ([ADR 0005](./docs/decisions/0005-tag-discipline.md) § Scope). In order:

1. **Preconditions.** An orphan-variable check, `git fetch origin main`, branch is `main`, `HEAD` equals `origin/main`, clean working tree, tag `v<version>` free locally and on `origin`, a `## [<version>]` section in `CHANGELOG.md`, `gh` installed, and `VERSION` differs from the target. Any failure exits 1.
2. **Version sites.** Writes `VERSION`, `iso10383.json` `meta.version`, the Python `pyproject.toml` and `__init__.py`, `package.json`, `Cargo.toml` and the README badge. The changelog heading is written by hand beforehand, and the Parquet footer follows from regeneration, which makes nine sites.
3. **Regenerate** the exports and the bundles, in layer order, then `registry_release.json`.
4. **Version consistency** (`check_version_consistency.py`) after regeneration, so a site the bump missed fails here.
5. **Gate.** Eighteen `gate` calls, in this order; each records its exit code in `GATE_LOG` and stops the release on a non-zero exit:

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
   18. `python3 tools/gen_registry_release.py --check --version "$VERSION"`

6. **Commit and push** (`Release v<version>`), then **poll every workflow run for the release SHA** every 15 seconds for up to 600 seconds. It continues only when every run has completed with success; a failure or a timeout exits 1 before the tag exists.
7. **Tag** only on green: the message is the `CHANGELOG.md` section (first line `Release v<version>`), checked for a header, a body and placeholders, then `git tag -a -F ... --cleanup=verbatim`. The recorded message is read back with `git for-each-ref` and compared with the file; on a mismatch the local tag is deleted and nothing is pushed. Then `git push origin "v<version>"`.
8. **Verification document.** Writes `docs/v<version>-verification.md` with the commit SHA, the tag object SHA, and the exit code of every gate from `GATE_LOG`, so a gate added to the script cannot be missing from the document.

Tags are immutable ([ADR 0005](./docs/decisions/0005-tag-discipline.md)). A verification document exists per release: [`v1.0.0`](./docs/v1.0.0-verification.md), [`v1.0.1`](./docs/v1.0.1-verification.md), [`v1.0.2`](./docs/v1.0.2-verification.md), [`v1.0.3`](./docs/v1.0.3-verification.md), [`v1.0.4`](./docs/v1.0.4-verification.md), [`v1.0.5`](./docs/v1.0.5-verification.md), [`v1.1.0`](./docs/v1.1.0-verification.md). The gate's `pyarrow` and toolchain requirements are the ones in [Flat exports](#comparison-semantics-and-the-build-pin).

---

### The release manifest

[`registry_release.json`](./registry_release.json) is the release's self-description. [`tools/gen_registry_release.py`](./tools/gen_registry_release.py) generates it and [`registry_release.schema.json`](./registry_release.schema.json) is its contract. It lists every artifact a consumer might load, with size and SHA-256 (the registry, the schema, the nine flat exports and the four bundled copies), the source file the registry was derived from, the counts this README quotes, and the two vendored snapshots with their pinned versions and `review_by` dates. A project that pins registries by manifest (QLF is the first) reads this file; it does not parse this README.

`commit` and `tag_object` are `null` in the committed file, by design: the file ships inside the release commit and cannot contain that commit's SHA, and the tag object does not exist yet. Both are recorded in `docs/v<version>-verification.md` and in the git tag. `distribution` is `source-only`: no wrapper is published.

A consumer checking which tag a manifest describes, and that a file on disk is the file it lists:

```bash
python3 -c "import json; m=json.load(open('registry_release.json')); print(m['tag'], m['commit'])"
# v<version> None   (the commit comes from: git rev-parse "<tag>^{commit}")

python3 -c "import hashlib, json; m=json.load(open('registry_release.json')); f=next(x for x in m['files'] if x['path']=='iso10383.json'); print(hashlib.sha256(open('iso10383.json','rb').read()).hexdigest()==f['sha256'])"
# True
```

`make registry-release` regenerates the file. `release.sh` regenerates it after the version bump and runs `gen_registry_release.py --check` as gate 18, so a release cannot ship a stale manifest. The number of tests the manifest reports is read from `tests/test_counts.json`; when that file is absent the field is `null`.

---

## 16. Versioning

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

## 17. Project structure

```text
iso10383/
├── VERSION                              # Registry version, source of truth
├── iso10383.json                        # Layer 1: the registry (2,893 MICs)
├── schema.json                          # JSON Schema draft-07 contract, version 1.0.0
├── registry_release.json                # Generated: this release's files, hashes, counts, vendored snapshots
├── registry_release.schema.json         # JSON Schema draft-07 for registry_release.json
├── README.md                            # This file
├── CHANGELOG.md                         # Release history, [Unreleased] on top
├── SECURITY.md                          # How to report a vulnerability; the two data-integrity mechanisms
├── CONTRIBUTING.md                      # The four rules, source discipline, change workflows
├── LICENSE                              # Apache 2.0
├── constraints.txt                      # Output-affecting pins (pyarrow==25.0.1)
├── requirements-dev.txt                 # jsonschema, pyarrow, pytest, pyyaml; applies constraints.txt
├── .gitattributes                       # LF endings for text exports; parquet is binary
├── .gitignore                           # raw/, caches, .venv, rust target and lockfile
├── Makefile                             # package, build-wheel, test, registry-release
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
│   ├── refresh_diff.py                  # NEW / EXPIRED / CHANGED / REMOVED between two registry files
│   ├── validate.py                      # Six-layer validator
│   ├── export_columns.py                # Canonical column order for every exporter
│   ├── export_sql.py                    # SQL generator, 4 dialects (--check)
│   ├── export_csv.py                    # CSV/TSV generator, 4 files (--check)
│   ├── export_parquet.py                # Parquet generator, byte-stable (--check)
│   ├── sync_wrappers.py                 # Layer 3: bundled-copy sync (--check)
│   ├── gen_registry_release.py          # registry_release.json generator (--check)
│   ├── iso10383_cli.py                  # The command-line interface
│   ├── gen_iso3166_snapshot.py          # Layer 4: ISO 3166 snapshot from its pinned tag (--check)
│   ├── gen_exchange_calendar_snapshot.py  # Layer 4: Exchange Calendar snapshot from its pinned tag (--check)
│   ├── iso3166_snapshot.json            # Layer 4: 252 alpha-2 codes
│   ├── iso3166_snapshot.meta.json       # Vendoring metadata and review_by
│   ├── exchange_calendar_snapshot.json  # Layer 4: 74 MICs
│   ├── exchange_calendar_snapshot.meta.json  # Vendoring metadata and review_by
│   ├── check_version_consistency.py     # The nine version sites, plus the schema badge
│   ├── check_registry_freshness.py      # meta.source_snapshot within 60 days
│   ├── check_snapshot_freshness.py      # Vendored snapshots within review_by
│   ├── check_release_claims.py          # Verifies the claims manifest
│   ├── release_claims.json              # {file, contains|absent} claims, one list per release plus doc-facts
│   ├── check_mojibake.py                # Encoding corruption and unclosed fences
│   ├── check_iso3166_current.py         # Snapshot vs live ISO 3166 (--strict)
│   ├── check_exchange_calendar_current.py  # Snapshot vs live Exchange Calendar (--strict)
│   └── check_cross_language.sh          # The four wrapper suites plus sync (--strict)
│
├── scripts/
│   └── release.sh                       # The release pipeline
│
├── examples/
│   └── orders-5k/
│       ├── README.md                    # What is real and what is synthetic; how to read the output
│       ├── generate_facts.py            # 5,000 fictional orders across 50 real venues
│       ├── analyze.py                   # Copy-versus-join storage, join equivalence, simulated registry change
│       └── requirements.txt             # pyarrow==25.0.1
│
├── tests/
│   ├── cross_language_consistency.json  # Shared fixture for all four wrappers
│   ├── conftest.py                      # Shared pytest setup
│   ├── test_check_mojibake.py           # Mojibake checker, each class at runtime
│   ├── test_check_registry_freshness.py # check_registry_freshness.py --today, exit codes
│   ├── test_checks.py                   # The checking tools
│   ├── test_check_release_claims.py     # The release-claims checker: exit codes, manifest keys
│   ├── test_cli.py                      # CLI behaviour and exit codes
│   ├── test_export_csv.py               # CSV/TSV exporter
│   ├── test_export_parquet.py           # Parquet exporter
│   ├── test_export_sql.py               # SQL exporter
│   ├── test_fetch_swift_mic.py          # The fetcher rejects unexpected columns
│   ├── test_fixture.py                  # The shared fixture itself
│   ├── test_generators.py               # AST: no clock reads in the snapshot generators
│   ├── test_iso10383_codes.py           # Known-code ground truth
│   ├── test_pip_pins.py                 # Every pyarrow pip install line carries -c constraints.txt
│   ├── test_scripts.py                  # release.sh and verification-doc properties
│   ├── test_self_reference.py           # Operating self-reference, chain termination
│   ├── test_validate_schema.py          # Validator layers against bad fixtures
│   ├── test_wrappers.py                 # Wrapper copies and shims
│   └── fixtures/
│       ├── bad_cycle.csv                # Parser input: cyclic parent chain
│       ├── bad_missing_parent.csv       # Parser input: parent absent
│       ├── valid_three_level.csv        # Parser input: a valid three-level chain
│       ├── valid_seventeen_plus_one.csv # Parser input: the 17 columns plus one unexpected column (rejected)
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
│   │       └── test_registry.py         # 31 tests
│   ├── javascript/
│   │   ├── README.md                    # JavaScript API
│   │   ├── package.json                 # Package manifest (version site)
│   │   ├── src/index.js                 # MICRegistry
│   │   ├── src/data/iso10383.json       # Layer 3 copy
│   │   ├── test/fixture.js              # Fixture anchors
│   │   └── test/registry.test.js        # 29 tests as node --test reports them (28 test() definitions plus the fixture-anchor module)
│   ├── rust/
│   │   ├── README.md                    # Rust API
│   │   ├── Cargo.toml                   # Crate manifest (version site)
│   │   ├── src/lib.rs                   # Registry
│   │   ├── data/iso10383.json           # Layer 3 copy
│   │   ├── examples/smoke.rs            # End-to-end smoke example
│   │   └── tests/registry.rs            # 27 tests
│   └── go/
│       ├── README.md                    # Go API
│       ├── go.mod                       # Module path; carries no version
│       ├── registry.go                  # Registry (embeds data/)
│       ├── registry_test.go             # 31 tests
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
│   ├── README-AUDIT-NOTES.md            # Receipt: how each README number was measured
│   ├── AUDIT.md                         # Tool inventory: does each tool run, and where
│   ├── ENRICHMENT.md                    # Why each nullable field is null
│   ├── v1.0.0-verification.md          # Gate record for v1.0.0
│   ├── v1.0.1-verification.md          # Gate record for v1.0.1
│   ├── v1.0.2-verification.md          # Gate record for v1.0.2
│   ├── v1.0.3-verification.md          # Gate record for v1.0.3
│   ├── v1.0.4-verification.md          # Gate record for v1.0.4
│   ├── v1.0.5-verification.md          # Gate record for v1.0.5
│   ├── v1.1.0-verification.md          # Gate record for v1.1.0
│   └── decisions/
│       ├── README.md                    # Index of the twelve ADRs: question, status, amendments
│       ├── v1.0.0-decisions.md          # D1 to D17, each with a status
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
        ├── refresh.yml                  # Monthly refresh, opens a pull request
        └── check-sources.yml            # Weekly: fetch SWIFT's file, open an issue on failure
```

---

## 18. Documentation index

| Document | What does it answer? |
|----------|----------------------|
| [`docs/LAYERS.md`](./docs/LAYERS.md) | Which layer does a file belong to, how is it produced and validated, and what is irreplaceable? |
| [`docs/PROVENANCE.md`](./docs/PROVENANCE.md) | Where does each field come from, how often is it refreshed, how do I audit it, and what is not covered? |
| [`docs/JOINS.md`](./docs/JOINS.md) | Which registries reference `mic`, at what granularity, and what does this registry not answer? |
| [`docs/ENRICHMENT.md`](./docs/ENRICHMENT.md) | Why is a field null, and what can I do about it? |
| [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) | What invariants does every release refuse on, and what are the operator-hygiene rules? |
| [`docs/AUDIT.md`](./docs/AUDIT.md) | Which tools exist, does each one run, and where? |
| [`docs/README-AUDIT-NOTES.md`](./docs/README-AUDIT-NOTES.md) | How was each number in the 2026-10-18 README measured, and at what commit? (A historical receipt, not current documentation.) |
| [`docs/action_types.md`](./docs/action_types.md) | What do `OPERATING`, `SEGMENT` and each status mean, and which combinations occur? |
| [`docs/source_format.md`](./docs/source_format.md) | Exactly what does SWIFT's file contain (headers, value sets, dates)? |
| [`docs/mic_lei_source_format.md`](./docs/mic_lei_source_format.md) | What did the MIC to LEI reconnaissance find, and what would reopen it? |
| [`docs/mic_bic_source_format.md`](./docs/mic_bic_source_format.md) | Which sources were checked for a MIC to BIC mapping, and what would reopen it? |
| [`docs/exchange_calendar_mics.txt`](./docs/exchange_calendar_mics.txt) | Which 74 MICs does Exchange Calendar reference? |
| [`docs/decisions/README.md`](./docs/decisions/README.md) | Which ADR answers which question, and what is each one's status? |
| [`docs/decisions/v1.0.0-decisions.md`](./docs/decisions/v1.0.0-decisions.md) | Why was each v1.0.0 design choice (D1 to D17) made, and is it still active? |
| | [`docs/decisions/0001-source-format.md`](./docs/decisions/0001-source-format.md) | What is SWIFT's file, exactly? |
| | [`docs/decisions/0002-operating-segment-model.md`](./docs/decisions/0002-operating-segment-model.md) | How are operating MICs and segment MICs modelled? |
| | [`docs/decisions/0003-monthly-refresh.md`](./docs/decisions/0003-monthly-refresh.md) | How often does the registry refresh, and when is a snapshot too old? |
| | [`docs/decisions/0004-market-category-codes.md`](./docs/decisions/0004-market-category-codes.md) | Which market category codes are allowed? |
| | [`docs/decisions/0005-tag-discipline.md`](./docs/decisions/0005-tag-discipline.md) | When is a release tag created, and what does the verification document record? |
| | [`docs/decisions/0006-ci-toolchain-parity.md`](./docs/decisions/0006-ci-toolchain-parity.md) | How do the local gate and the CI gate agree on what "verified" means? |
| | [`docs/decisions/0007-cross-registry-allowlist.md`](./docs/decisions/0007-cross-registry-allowlist.md) | How is a known gap against Exchange Calendar tolerated? |
| | [`docs/decisions/0008-mic-lei-companion-declined.md`](./docs/decisions/0008-mic-lei-companion-declined.md) | Should there be a MIC→LEI companion file? |
| | [`docs/decisions/0009-mic-bic-companion-declined.md`](./docs/decisions/0009-mic-bic-companion-declined.md) | Should there be a MIC→BIC companion file? |
| | [`docs/decisions/0010-platform-charter.md`](./docs/decisions/0010-platform-charter.md) | What is the registry for, who consumes it, and what layers does it have? |
| | [`docs/decisions/0011-reprocessing.md`](./docs/decisions/0011-reprocessing.md) | What does the refresh do step by step, and is reprocessing a capability? |
| | [`docs/decisions/0012-agent-read-surface.md`](./docs/decisions/0012-agent-read-surface.md) | What may a future agent read, and what may it write? |
| `docs/v<version>-verification.md` | What did the release gate print when this version shipped? |
| [`examples/orders-5k/README.md`](./examples/orders-5k/README.md) | What does copying registry fields into a fact table cost, against a join on the MIC? |
| [`CHANGELOG.md`](./CHANGELOG.md) | What changed in each release, and what is queued under `[Unreleased]`? |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | What are the four rules, and how do I fix data, add a field, add an export or cut a release? |
| `wrappers/*/README.md` | What is the full API of each wrapper? |

---

## 19. Contributing

Open an issue before starting a large change. Data corrections go through a tool, never a hand edit of `iso10383.json`. The quick workflow, in the order the release script expects:

1. Set up (once): `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt && pip install -e wrappers/python`
2. Change the source or the tool. A data change means a new SWIFT file: `python3 tools/fetch_swift_mic.py --download --force --strict --version "$(cat VERSION)"`
3. Validate: `python3 tools/validate.py` (must exit 0)
4. Regenerate the derived files, Layer 2 then Layer 3 (`make package` runs the same four commands):
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

## 20. Known limitations

Stated plainly, because a canonical registry is a claim and a claim needs its edges drawn.

- **One source.** Everything traces to SWIFT's published `ISO10383_MIC.csv`. A MIC that appears in a national exchange's own publications but not in that file is not here.
- **Monthly lag.** SWIFT publishes on the second Monday of the month and the refresh runs on the 15th, so a venue that opens mid-month is absent until the next cycle. This is a property of the standard and of ADR 0011's batch shape, not a defect.
- **A snapshot, not a history.** `UPDATED` is transient: it means "changed since the last publication" and reverts to `ACTIVE` later. No file records what changed in a MIC or when beyond the four date fields. Replaying an earlier state means checking out an earlier tag; Layer 0 keeps only the current raw file.
- **No LEI, BIC or ISIN companion.** The `lei` field carries SWIFT's published LEI where there is one (2,264 of 2,893 entries; 629 are null). GLEIF's mapping was found to be a subset of that field and a companion file was declined ([ADR 0008](./docs/decisions/0008-mic-lei-companion-declined.md)). No MIC to BIC source file was found ([ADR 0009](./docs/decisions/0009-mic-bic-companion-declined.md)). MIC to ISIN is out of scope (D11).
- **No trading currency, operating hours or regulatory status.** Trading currency is not stored per MIC; the nearest derivation is `country_code` to ISO 4217, which cannot express a venue trading in a non-local currency. Operating hours belong to Exchange Calendar. Regulatory status is out of scope (D11).
- **Sparse optional fields.** 1,867 entries have no `acronym`, 1,494 no `legal_entity_name`, 1,324 no `note`, 163 no `website` and 1,896 no `last_validation_date`. A null is the source's silence, never a guess; [`docs/ENRICHMENT.md`](./docs/ENRICHMENT.md) goes field by field.
- **Three MICs have no fixed country.** `BILT`, `XOFF` and `XXXX` carry `ZZ`, ISO 10383's placeholder, which is not an ISO 3166 code; the validator skips it. `country_code` is never null.
- **Text is as published.** Names and websites are upper case, as SWIFT supplies them. The registry does not normalise.
- **The SQL export is a reference table.** It carries 11 of the 17 fields, and only the PostgreSQL and SQLite files declare the self-referencing foreign key.
- **Chains are capped at eight hops.** The deepest in this snapshot is three levels. A deeper chain is refused by the parser and the validator.
- **The cross-checks cover 74 MICs, not all of them.** Exchange Calendar references 74 MICs; the other 2,809 have no sibling that checks them.
- **Network-dependent gates.** `check_*_current.py` and `gen_*_snapshot.py --check` reach GitHub; offline, they cannot run.
- **Language packages are not published** to PyPI, npm, crates.io or a Go proxy. Install from a clone.
- **No aggregated layer.** One grain, one row per MIC: there is no count-by-country or count-by-category file. Aggregate from the Parquet or the CSV.
- **No XLSX or XML distribution.** SWIFT's original offers both; this registry publishes JSON, SQL, CSV, TSV and Parquet only.
- **Where the edges and the numbers are recorded.** The Known limitations and README-AUDIT-NOTES sections together serve the role a `STATE.md` plays in the sibling registries: this section states the edges, and the audit notes are the receipt of how the numbers in the 2026-10-18 README were measured. Numbers added since are pinned by the claims in `tools/release_claims.json`, not by the notes.

---

## 21. FAQ

**Why does every segment have a parent, and why does every operating MIC point to itself?**
So `operating_mic` is `NOT NULL` everywhere and a join never needs a special case. The root is reached by walking `operating_mic` until it equals `mic` ([ADR 0002](./docs/decisions/0002-operating-segment-model.md)).

**Why is there no `root_mic` column?**
It would be a second value to keep consistent with `operating_mic` when a parent changes. Eight chains have three levels, so the walk is short, and the [worked example](#10-worked-example-a-venue-tree-in-ten-commands) shows it in pandas.

**What does a null mean?**
The source file had no value, and the field stays null rather than carrying a guess ([`docs/ENRICHMENT.md`](./docs/ENRICHMENT.md) explains each nullable field). In JSON it is `null`, in CSV an empty field, in Parquet a null, in SQL `NULL`.

**What does `UPDATED` mean, and should I treat it as active?**
It means the entry changed since the last publication (21 entries in this snapshot). It is not expired. A consumer that wants "currently valid" should accept `ACTIVE` and `UPDATED` and exclude `EXPIRED`.

**Why does `validate.py` fail when Exchange Calendar references an unknown MIC?**
Cross-registry checks have been blocking since v1.0.1, and the allowlist of tolerated gaps is empty. Fix the sibling or the registry; adding an allowlist entry needs an ADR amendment ([ADR 0007](./docs/decisions/0007-cross-registry-allowlist.md)). `--advisory` downgrades the failure to a warning.

**Why does `check_cross_language.sh --strict` fail on my machine?**
A wrapper toolchain (`node`, `cargo` or `go`) is missing, and `--strict` refuses to pass with a skipped suite. Install the toolchain or run without `--strict`.

**Where is the trading currency, or the operating hours?**
Not in the registry: SWIFT's file does not carry them, and the registry reproduces SWIFT's file (see [Known limitations](#20-known-limitations)).

**Why does the SQL export lack `lei` and `website`?**
It is the foreign-key-ready minimum, 11 columns. The CSV, TSV and Parquet carry all 17.

**Why are the exports committed instead of built on demand?**
So a consumer can download one file and run nothing, and so drift between the JSON and a derived file fails CI instead of reaching users.

**How do I know which registry version produced a file I was handed?**
JSON: `meta.version`. Parquet: footer key `iso10383.version`. SQL: the `-- version:` comment on line 3.

**Why can't I `pip install iso10383-registry`?**
Publication is deferred until a consumer needs it (see [What's next](#24-whats-next)). Use `pip install -e wrappers/python` from a clone.

**Why does `iso10383` not exist as a command after installing the Python wrapper?**
The CLI is a repository artifact. Use `python3 tools/iso10383_cli.py` or `bin/iso10383` from a checkout.

---

## 22. Consumed by

ISO 10383 is the leaf of the MIC join graph: other registries reference `mic`; this one references none of them except for validation. [`docs/JOINS.md`](./docs/JOINS.md) names every edge. Each row gives the proof that exists in this repository, and says where the proof lives in a sibling repository that is not part of this tree.

| Project | Edge | Proof |
|---------|------|-------|
| [Exchange Calendar](https://github.com/slimissa/exchange-calendar) | `exchanges/*.json` carries `mic` (or `code`); JOINS records 74 entries | `tools/exchange_calendar_snapshot.json` (74 MICs) reproduced by `gen_exchange_calendar_snapshot.py --check`; `check_exchange_calendar_current.py --strict` compares it with the live sibling; `validate.py` fails if any of the 74 is missing here |
| [ISO 3166](https://github.com/slimissa/iso3166) | Reverse edge: this registry's `country_code` joins ISO 3166's alpha-2 codes | `tools/iso3166_snapshot.json` (252 codes), reproduced by `gen_iso3166_snapshot.py --check`; `validate.py` checks every `country_code` except `ZZ` against it |
| Asset Identifiers | `exchange` and `listings[].exchange` reference a MIC, "Either" granularity | Declared in that repository's `schema.json`, per `docs/JOINS.md`. JOINS records that the public repository holds only the schema and a fixture, so the edge is verified against a schema, not records. Not checkable from this tree. |
| Corporate Actions | `exchange` per action | `docs/JOINS.md` marks it planned and records that none of its 240 actions carries an `exchange` field as of 2026-10-11. Not checkable from this tree. |
| [Tempus](https://github.com/slimissa/Tempus) | Compile-time `@market_context` validation | None in this repository. Named as an intended consumer; it does not appear in `docs/JOINS.md`, and no artifact here depends on it. |
| [LAS_Shell](https://github.com/slimissa/Las_shell) | Market status and prompt display | None in this repository. Named as an intended consumer; it does not appear in `docs/JOINS.md`, and no artifact here depends on it. |

No external adopter is recorded. *Using this registry in your project? Open a pull request to add a row.*

---

## 23. License and author

Apache 2.0. See [`LICENSE`](./LICENSE). The MIC data is factual information sourced from SWIFT's published ISO 10383 file; the compilation, schema, tooling, wrappers and documentation are licensed works.

**Le P'tit**, [github.com/slimissa](https://github.com/slimissa)

---

## 24. What's next

The registry is complete for its charter; the deferred items below are extensions, not corrections, and each has a named trigger. Nothing is scheduled. D14 forbids a roadmap before the previous release has shipped, and v1.1.0 has; the next release follows the first trigger below that fires.

| Deferred item | Trigger to start | Where decided |
|---------------|------------------|---------------|
| **Wrapper publication** to PyPI, npm, crates.io and a Go proxy | A consumer tries to install a wrapper from a package registry, or needs one | README (this section), [ADR 0010](./docs/decisions/0010-platform-charter.md) reopening condition 2 |
| **MIC to LEI companion** | A MIC to LEI pair in GLEIF's file that `iso10383.json` does not carry, or a MIC whose LEI differs between SWIFT's field and GLEIF's file; checked by re-running the procedure in `docs/mic_lei_source_format.md` (no CI monitors it) | [ADR 0008](./docs/decisions/0008-mic-lei-companion-declined.md) |
| **MIC to BIC companion** | A source file appears with a named publication, redistributable terms and a counted reconnaissance | [ADR 0009](./docs/decisions/0009-mic-bic-companion-declined.md) |
| **A streaming or sub-monthly refresh** | SWIFT offers a push or change feed, a consumer needs freshness under a day, or a source changes continuously | [ADR 0011](./docs/decisions/0011-reprocessing.md) |
| **A feature outside the charter** (hours, regulatory status, trading currency, MIC to ISIN) | A consumer asks for it; it is then a new decision, not an extension | [ADR 0010](./docs/decisions/0010-platform-charter.md) |
| **An agent and its proposal schema** | An agent is built; the read-surface table and a freshness check for `docs/JOINS.md` drift are the prerequisites | [ADR 0012](./docs/decisions/0012-agent-read-surface.md) |
| **`check_workflows_covered` in `release.sh`** | A second per-push workflow is added; the poll cannot otherwise tell that an expected workflow has not started | `scripts/release.sh` header, [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) invariant 6 |
| **An ISO 4217 snapshot** | A field that references a currency is added to this registry | ADR 0010, amendment of 2026-10-18 |

See [`CHANGELOG.md`](./CHANGELOG.md) for release history and [`docs/decisions/`](./docs/decisions/) for locked decisions.
