# ISO 10383 MIC Registry

**A canonical, versioned, machine-readable registry of ISO 10383 Market Identifier Codes.**

One JSON file. Six-layer validation. Nine distribution artifacts. Four language wrappers. Zero runtime dependencies.

[![Validate](https://github.com/slimissa/iso10383/actions/workflows/validate.yml/badge.svg)](https://github.com/slimissa/iso10383/actions/workflows/validate.yml)
[![Refresh](https://github.com/slimissa/iso10383/actions/workflows/refresh.yml/badge.svg)](https://github.com/slimissa/iso10383/actions/workflows/refresh.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Schema](https://img.shields.io/badge/schema-1.0.0-green.svg)](./schema.json)
[![Registry](https://img.shields.io/badge/registry-1.0.1-orange.svg)](./CHANGELOG.md)
[![MICs](https://img.shields.io/badge/MICs-2883-blue.svg)](./iso10383.json)
[![Wrappers](https://img.shields.io/badge/wrappers-4-purple.svg)](./wrappers/)
[![Tests](https://img.shields.io/badge/tests-145-success.svg)](./tests/)

---

## Why?

Every trading system, quant library, and fintech app maintains its own MIC list. They drift. Some include expired codes, some do not. Some handle the operating-versus-segment hierarchy, some flatten it. Some know that the parent of a segment can itself be a segment; some assume every segment hangs directly off an operating MIC.

One versioned, schema-validated JSON file, guarded by CI, replaces all of that.

**MIC is the join key every financial data standard uses to say "where."** An instrument trades on an MIC. A quote comes from an MIC. A regulatory filing references an MIC. An exchange's primary identifier is its MIC.

- **Tempus** uses it for `@market_context` type-level validation
- **LAS_Shell** uses it for market status detection and prompt display
- **Exchange Calendar** cross-references it for every exchange file
- **Python quant libraries** use it for venue lookups
- **Go trading systems** use it for order routing
- **Rust finance crates** use it for compile-time venue verification
- **JavaScript fintech apps** use it for market hours display

The registry is language-agnostic by design. The JSON is the contract. The nine exports and four wrappers are thirteen ways to consume it without writing a parser.

---

## Quick start

### Direct download

```bash
curl -O https://raw.githubusercontent.com/slimissa/iso10383/main/iso10383.json
```

### Python

```bash
pip install -e wrappers/python
```

```python
from iso10383 import MICRegistry

reg = MICRegistry()                        # bundled snapshot
xnys = reg.by_mic("XNYS")
print(xnys.mic_type, xnys.country_code)    # OPERATING US

for seg in reg.segments("XJPX"):
    print(seg.mic, seg.market_name)

print(reg.operating_mic("XTKS"))           # XJPX
print(len(reg.expired(since="2024-01-01")))  # 82
```

### JavaScript

```bash
npm install ./wrappers/javascript
```

```javascript
const { MICRegistry } = require("iso10383-registry");

const reg = new MICRegistry();
const xnys = reg.byMic("XNYS");
console.log(xnys.mic_type, xnys.country_code);  // OPERATING US

for (const seg of reg.segments("XJPX")) {
  console.log(seg.mic, seg.market_name);
}

console.log(reg.operatingMic("XTKS"));          // XJPX
```

### Rust

```bash
cd wrappers/rust && cargo build
```

```rust
use iso10383_registry::Registry;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let reg = Registry::load()?;
    let xnys = reg.by_mic("XNYS").unwrap();
    println!("{} {}", xnys.mic_type, xnys.country_code.as_deref().unwrap_or(""));
    // OPERATING US

    for seg in reg.segments("XJPX") {
        println!("{}", seg.mic);
    }

    println!("{:?}", reg.operating_mic("XTKS"));  // Some("XJPX")
    Ok(())
}
```

### Go

```bash
go get github.com/slimissa/iso10383/wrappers/go
```

```go
import (
    "fmt"
    iso10383 "github.com/slimissa/iso10383/wrappers/go"
)

reg, _ := iso10383.LoadRegistry()
xnys := reg.ByMIC("XNYS")
fmt.Println(xnys.MICType, *xnys.CountryCode)  // OPERATING US

for _, seg := range reg.Segments("XJPX") {
    fmt.Println(seg.MIC)
}

fmt.Println(reg.OperatingMIC("XTKS"))  // XJPX
```

### SQL

Four self-contained dialects. Idempotent — safe to run twice.

| File | Target |
|------|--------|
| [`iso10383.sql`](./iso10383.sql) | ANSI SQL-92 — portable default |
| [`iso10383.postgresql.sql`](./iso10383.postgresql.sql) | PostgreSQL 12+ |
| [`iso10383.mysql.sql`](./iso10383.mysql.sql) | MySQL 8+ / MariaDB 10.4+ |
| [`iso10383.sqlite.sql`](./iso10383.sqlite.sql) | SQLite 3.37+ |

```bash
psql -f iso10383.postgresql.sql              # PostgreSQL
mysql < iso10383.mysql.sql                   # MySQL / MariaDB
sqlite3 registry.db < iso10383.sqlite.sql    # SQLite
psql -f iso10383.sql                         # any SQL-92 engine
```

Two tables: `mics` and `market_categories`. `mic` is the primary key. `operating_mic` is a self-referencing foreign key with a **non-null constraint** — every MIC has a parent MIC. Operating MICs point to themselves.

```sql
-- Every venue under the Japan Exchange Group.
SELECT mic, market_name
FROM mics
WHERE operating_mic = 'XJPX';

-- Every exchange in Germany that is still active.
SELECT mic, market_name
FROM mics
WHERE country_code = 'DE' AND status = 'ACTIVE';
```

### CSV / TSV

Four files. LF line endings. Headers always present.

| File | Audience |
|------|----------|
| [`iso10383.csv`](./iso10383.csv) | RFC 4180 — every CSV parser |
| [`iso10383.excel.csv`](./iso10383.excel.csv) | Excel on Windows (UTF-8 BOM) |
| [`iso10383.european.csv`](./iso10383.european.csv) | European Excel (semicolon-delimited) |
| [`iso10383.tsv`](./iso10383.tsv) | Terminal, Google Sheets, SQL clients |

```python
import pandas as pd
df = pd.read_csv("iso10383.csv")
```

No comment header. The first row is column names.

### Parquet

```python
import pyarrow.parquet as pq
df = pq.read_table("iso10383.parquet").to_pandas()
```

Typed columns: `mic_type`, `status`, `country_code`, `market_category` are dictionary-encoded; the four date fields are `date32`. The Parquet footer carries `iso10383.version`, `iso10383.updated`, `iso10383.source_snapshot`, and `iso10383.source_hash` — any consumer can read version info without opening the JSON.

### Command line

```bash
iso10383 lookup XNYS
iso10383 list --country US --mic-type OPERATING
iso10383 segments XJPX
iso10383 parent XTKS
iso10383 expired --since 2024-01-01
iso10383 search nasdaq
iso10383 validate XNYS XLON XTKS
iso10383 info
iso10383 check
```

Every command supports five machine-readable modes: `--json`, `--jsonl`, `--csv`, `--tsv`, `--raw FIELD`.

---

## Registry contents

| Category | Count |
|----------|-------|
| Operating MICs | 1,594 |
| Segment MICs | 1,289 |
| **Total** | **2,883** |
| — Active | 2,296 |
| — Updated (since last publication) | 21 |
| — Expired | 566 |
| Broken parent chains | 0 |

### The hierarchy

ISO 10383 has two MIC types. An **operating MIC** identifies an entity that operates an exchange, trading platform, or trade reporting facility. A **segment MIC** identifies a section of an entity specialising in specific instruments or regulated differently.

Every MIC has a parent:
- An operating MIC self-references: `operating_mic == mic`.
- A segment MIC points to its parent. The parent may itself be a segment. The chain terminates at an operating MIC.

The 2026-09-23 snapshot contains eight three-level chains. Example: `XEAS → XEQT → XBER`. The schema models this directly. It does not assume a two-level tree.

### Market categories

Sixteen closed-enum codes from the ISO 10383 Release 2.0 factsheet. The 2026-09-23 snapshot uses 14 of them; `ARMS` and `CTPS` are defined but currently unassigned.

| Code | Meaning |
|------|---------|
| `ATSS` | Alternative Trading System |
| `APPA` | Approved Publication Arrangement |
| `ARMS` | Arrangement for Reporting |
| `CTPS` | Consolidated Tape Provider |
| `CASP` | Consolidated Access Service Provider |
| `DCMS` | Data Communication and Messaging Service |
| `IDQS` | Identifier Quotation Service |
| `MLTF` | Multilateral Trading Facility |
| `NSPD` | Not-Systematic Price Disseminator |
| `OTFS` | Organised Trading Facility |
| `OTHR` | Other |
| `RMOS` | Regulated Market Off-Session |
| `RMKT` | Regulated Market |
| `SEFS` | Systematic Externaliser |
| `SINT` | Systematic Internaliser |
| `TRFS` | Trade Reporting Facility |

### Countries

Every MIC carries an ISO 3166-1 alpha-2 country code. `ZZ` is ISO 10383's placeholder for "no fixed country" and is not an ISO 3166 code; the validator skips it.

---

## Data model

Seventeen fields per entry. Five are always present; the rest may be `null`.

| Field | Type | Notes |
|-------|------|-------|
| `mic` | string | Primary key. `^[A-Z0-9]{4}$`. |
| `mic_type` | string | `OPERATING` or `SEGMENT`. |
| `status` | string | `ACTIVE`, `UPDATED`, or `EXPIRED`. |
| `operating_mic` | string | Parent MIC. Non-null for every entry. |
| `market_name` | string\|null | Name as published by SWIFT. |
| `legal_entity_name` | string\|null | Registered legal name. |
| `lei` | string\|null | Legal Entity Identifier. |
| `market_category` | string\|null | One of the 16 ISO codes. |
| `acronym` | string\|null | Short name. |
| `country_code` | string\|null | ISO 3166-1 alpha-2, or `ZZ`. |
| `city` | string\|null | City of operation. |
| `website` | string\|null | Operator's website. |
| `creation_date` | string\|null | ISO 8601 date. |
| `last_update_date` | string\|null | ISO 8601 date. |
| `last_validation_date` | string\|null | ISO 8601 date. |
| `expiration_date` | string\|null | ISO 8601 date for expired entries. |
| `note` | string\|null | Free text from the source. |

### The JSON shape

```json
{
  "meta": {
    "version": "0.1.0",
    "updated": "2026-09-23",
    "source_snapshot": "2026-09-23",
    "source_url": "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv",
    "source_hash": "sha256:79de0f77...",
    "counts": {
      "operating": 1594, "segment": 1289,
      "active": 2296, "updated": 21, "expired": 566,
      "total": 2883
    },
    "broken_chains": []
  },
  "mics": [
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
  ]
}
```

`mics` is sorted by `mic`. Output is deterministic: `json.dumps(..., sort_keys=True)`, LF line endings, trailing newline. Two runs on the same source file produce byte-identical JSON.

---

## Wrappers

Four idiomatic wrappers, one shared contract. Every wrapper reads [`tests/cross_language_consistency.json`](./tests/cross_language_consistency.json) and ships a byte-identical copy of `iso10383.json`.

| Language | Package | Import |
|----------|---------|--------|
| Python | `iso10383-registry` | `from iso10383 import MICRegistry` |
| JavaScript | `iso10383-registry` | `const { MICRegistry } = require("iso10383-registry")` |
| Rust | `iso10383-registry` | `use iso10383_registry::Registry;` |
| Go | `github.com/slimissa/iso10383/wrappers/go` | `import iso10383 "..."` |

### Consistent API

| Operation | Python | JavaScript | Rust | Go |
|-----------|--------|------------|------|-----|
| Load | `MICRegistry()` | `new MICRegistry()` | `Registry::load()` | `LoadRegistry()` |
| Lookup | `.by_mic("XNYS")` | `.byMic("XNYS")` | `.by_mic("XNYS")` | `.ByMIC("XNYS")` |
| Segments | `.segments("XJPX")` | `.segments("XJPX")` | `.segments("XJPX")` | `.Segments("XJPX")` |
| Parent | `.operating_mic("XTKS")` | `.operatingMic("XTKS")` | `.operating_mic("XTKS")` | `.OperatingMIC("XTKS")` |
| Expired | `.expired(since="...")` | `.expired("...")` | `.expired(Some("..."))` | `.Expired("...")` |
| By country | `.by_country("US")` | `.byCountry("US")` | `.by_country("US")` | `.ByCountry("US")` |
| By status | `.by_status("ACTIVE")` | `.byStatus("ACTIVE")` | `.by_status("ACTIVE")` | `.ByStatus("ACTIVE")` |
| By type | `.by_mic_type("SEGMENT")` | `.byMicType("SEGMENT")` | `.by_mic_type("SEGMENT")` | `.ByMICType("SEGMENT")` |
| Search | `.search("nasdaq")` | `.search("nasdaq")` | `.search("nasdaq")` | `.Search("nasdaq")` |
| Validate | `.validate([...])` | `.validate([...])` | `.validate([...])` | `.Validate([]string{...})` |

Every lookup returns a fresh copy in Python and JavaScript; every lookup returns a borrowed reference in Rust and Go, where the language's ownership model prevents mutation. Handlers are the same in all four.

### Verify every wrapper agrees

```bash
bash tools/check_cross_language.sh
```

Runs all four test suites and exits 0 only when every wrapper produces the same answers for the same fixture cases.

---

## Command-line interface

The `iso10383` command is installed by the Python wrapper. Nine subcommands:

| Subcommand | Purpose |
|------------|---------|
| `lookup MIC` | All fields for one MIC |
| `list` | Filter across the registry |
| `segments MIC` | Direct children of a parent MIC |
| `parent MIC` | The `operating_mic` of a MIC |
| `expired --since DATE` | Expired MICs on or after DATE |
| `validate MIC...` | Exit 0 if every MIC exists |
| `search QUERY` | Substring on `market_name` and `acronym` |
| `info` | Registry metadata |
| `check` | Built-in smoke test |

`list` accepts `--country CC`, `--category CODE`, `--status STATE`, `--mic-type TYPE`.

Five output modes, mutually exclusive: `--json`, `--jsonl`, `--csv`, `--tsv`, `--raw FIELD`. `--csv` and `--tsv` columns match `iso10383.csv` and `iso10383.tsv` byte for byte.

**Exit codes:** 0 success, 1 code not found, 2 usage error, 3 registry missing or invalid.

**Color:** on when stdout is a TTY, off when piped. Override with `ISO10383_COLOR=never|auto|always`, `--color`, `--no-color`, or `NO_COLOR`.

### Examples

```bash
# Every operating MIC in the US.
iso10383 list --country US --mic-type OPERATING

# Just the MIC codes.
iso10383 list --country JP --raw mic

# The full venue tree under Japan Exchange Group.
iso10383 segments XJPX

# Where does XTKS sit?
iso10383 parent XTKS
# XTKS -> XJPX

# Validate a list before an order-routing call.
iso10383 validate XNYS XLON XTKS XPAR || echo "unknown MIC"

# Machine-readable registry metadata.
iso10383 info --json
```

Pipe-friendly by design:

```bash
iso10383 list --country DE --raw mic | xargs -I{} iso10383 lookup {}
```

---

## Validation

Six independent layers, each runnable in isolation.

```bash
python3 tools/validate.py
python3 tools/validate.py --only coverage
python3 tools/validate.py --skip cross-reference
python3 tools/validate.py --strict
```

| Layer | What it checks |
|-------|----------------|
| **Schema** | JSON Schema draft-07. `additionalProperties: false` at every object level. Closed enums for `mic_type`, `status`, `market_category`. |
| **Integrity** | MIC patterns (`^[A-Z0-9]{4}$`), country patterns (`^[A-Z]{2}$`), ISO 8601 date format, non-empty strings where required. |
| **Business** | MIC uniqueness. Operating MICs self-reference; segments do not. Expired entries have an `expiration_date`. |
| **Cross-reference** | Every segment's parent chain terminates at an operating MIC. Every `country_code` exists in the ISO 3166 snapshot (advisory in v1.0.0). |
| **Ground truth** | `XNYS`, `XLON`, `XTKS`, `XPAR` spot checks. |
| **Coverage** | Operating ≥ 1500, segment ≥ 1000, total ≥ 2500. |

Exit codes: 0 pass (warnings allowed), 1 data error, 2 usage error, 3 schema violation or malformed JSON.

### Cross-registry snapshots

Two committed snapshots provide the cross-reference data:

- `tools/iso3166_snapshot.json` — 252 alpha-2 codes from the ISO 3166 registry.
- `tools/exchange_calendar_snapshot.json` — 74 MICs referenced by the Exchange Calendar registry.

Both are regenerated by scripts (`tools/gen_iso3166_snapshot.py`, `tools/gen_exchange_calendar_snapshot.py`), committed, and verified in CI. No runtime dependency on either repository.

---

## Refreshing

SWIFT publishes the MIC file on the **second Monday of each month**. Modifications become effective on the fourth Monday.

CI fails if `meta.source_snapshot` is more than **60 days old** (`tools/check_snapshot_freshness.py`). Sixty days is one full missed cycle — a signal that the update process broke, not that the source is late.

### The monthly process

Automated: `.github/workflows/refresh.yml` runs on the 15th of every month. It downloads the current file, parses it, diffs against the committed registry, regenerates every artifact, and opens a pull request.

Manual, if needed:

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

**A refresh with `REMOVED > 0` fails the PR** until a human confirms the removal is intentional. A removed MIC is the change class most likely to break downstream consumers.

### Audit

Every `iso10383.json` carries `meta.source_hash` — a `sha256:` digest of the raw file the JSON was derived from. To verify a JSON against a raw file:

```bash
python3 -c "
import hashlib, json
from pathlib import Path
d = json.load(open('iso10383.json'))
h = 'sha256:' + hashlib.sha256(Path('raw/MIC_YYYYMMDD.csv').read_bytes()).hexdigest()
print('match' if h == d['meta']['source_hash'] else 'MISMATCH')
"
```

Two runs on the same raw file produce byte-identical JSON.

---

## Project structure

```
iso10383/
├── iso10383.json                 # The registry (2,883 MICs)
├── schema.json                   # JSON Schema draft-07 contract
├── VERSION                       # Single source of version truth
├── CHANGELOG.md
├── LICENSE                       # Apache 2.0
├── README.md                     # This file
├── CONTRIBUTING.md
├── requirements-dev.txt
├── .gitattributes
├── .gitignore
│
├── docs/
│   ├── PROVENANCE.md             # Sources, refresh cadence, known gaps
│   ├── source_format.md          # Verbatim source-file ground truth
│   ├── exchange_calendar_mics.txt
│   └── decisions/
│       └── v1.0.0-decisions.md   # D1–D16
│
├── iso10383.sql                  # ANSI SQL-92
├── iso10383.postgresql.sql       # PostgreSQL 12+
├── iso10383.mysql.sql            # MySQL 8+ / MariaDB 10.4+
├── iso10383.sqlite.sql           # SQLite 3.37+
├── iso10383.csv                  # RFC 4180
├── iso10383.excel.csv            # UTF-8 BOM
├── iso10383.european.csv         # Semicolon-delimited
├── iso10383.tsv                  # Tab-separated
├── iso10383.parquet              # Typed, columnar
│
├── tools/
│   ├── fetch_swift_mic.py        # Download and parse
│   ├── validate.py               # Six-layer validator
│   ├── export_sql.py             # SQL exporter (--check)
│   ├── export_csv.py             # CSV/TSV exporter (--check)
│   ├── export_parquet.py         # Parquet exporter (--check)
│   ├── export_columns.py         # Canonical column order
│   ├── sync_wrappers.py          # Bundle sync (--check)
│   ├── refresh_diff.py           # Monthly diff summary
│   ├── check_version_consistency.py
│   ├── check_snapshot_freshness.py
│   ├── check_cross_language.sh   # Four-wrapper agreement
│   ├── gen_iso3166_snapshot.py
│   ├── gen_exchange_calendar_snapshot.py
│   ├── iso10383_cli.py           # CLI
│   ├── iso3166_snapshot.json
│   └── exchange_calendar_snapshot.json
│
├── scripts/
│   └── release.sh                # Deterministic release pipeline
│
├── wrappers/
│   ├── python/                   # iso10383-registry
│   ├── javascript/               # iso10383-registry
│   ├── rust/                     # iso10383-registry
│   └── go/                       # github.com/slimissa/iso10383/wrappers/go
│
├── tests/
│   ├── cross_language_consistency.json    # Shared contract fixture
│   ├── fixtures/                          # Adversarial fixtures
│   ├── test_iso10383_codes.py
│   ├── test_validate_schema.py
│   ├── test_self_reference.py
│   ├── test_export_csv.py
│   ├── test_export_sql.py
│   ├── test_export_parquet.py
│   ├── test_cli.py
│   └── test_wrappers.py
│
└── .github/workflows/
    ├── validate.yml              # Five jobs on every push
    └── refresh.yml               # Monthly refresh, opens PR
```

---

## Testing

| Suite | Tests |
|-------|-------|
| Python (root) | 66 |
| Python (wrapper) | 19 |
| JavaScript | 21 |
| Rust | 19 |
| Go | 20 |
| **Total** | **145** |

```bash
python3 -m pytest tests/ -q                    # root
python3 -m pytest wrappers/python/tests -q     # Python wrapper
(cd wrappers/javascript && node --test)        # JavaScript
(cd wrappers/rust && cargo test --quiet)       # Rust
(cd wrappers/go && go test ./...)              # Go
bash tools/check_cross_language.sh             # all four together
```

### The fixture-anchor rule

Tests must not hardcode fixture values. Every assertion reads its expected value from the shared contract file at [`tests/cross_language_consistency.json`](./tests/cross_language_consistency.json) — via a per-language anchor module derived at load time. If the fixture changes, the anchors change with it, and the tests stay correct without editing. A missing anchor fails loudly at startup, not silently.

---

## Versioning

One version number, eight sites, all enforced by `tools/check_version_consistency.py`:

- `VERSION` (text file, the source of truth)
- `CHANGELOG.md` top released heading
- `iso10383.json` → `meta.version`
- `iso10383.parquet` footer → `iso10383.version`
- `wrappers/python/pyproject.toml`
- `wrappers/javascript/package.json`
- `wrappers/rust/Cargo.toml`
- `README.md` badge

CI fails if any disagree.

The registry follows [Semantic Versioning](https://semver.org/):

- **Major** — breaking schema changes.
- **Minor** — new MICs, new optional fields, new tooling.
- **Patch** — data corrections.

Wrapper package versions track the registry version.

---

## Releasing

Releases are cut by `scripts/release.sh <version>`. The script:

1. Verifies preconditions (clean tree, on `main`, `CHANGELOG` section present, tag free)
2. Bumps the eight version sites
3. Regenerates all nine artifacts
4. Runs the full gate (validate, freshness, three export `--check`s, sync, root tests, cross-language)
5. Commits, pushes, polls CI
6. Tags with a message derived from `CHANGELOG.md`
7. Writes `docs/v<version>-verification.md`

The script refuses on a dirty tree, wrong branch, missing CHANGELOG section, gate failure, or CI failure. Test with `--dry-run` before use.

---

## Consumed by

| Project | How it uses this registry |
|---------|---------------------------|
| [Exchange Calendar](https://github.com/slimissa/exchange-calendar) | Every exchange JSON carries a MIC; validated against this registry |
| [ISO 3166](https://github.com/slimissa/iso3166) | Country codes cross-referenced for `country_code` |
| [Tempus](https://github.com/slimissa/Tempus) | Planned compile-time `@market_context` validation |
| [LAS_Shell](https://github.com/slimissa/Las_shell) | Planned market status detection and prompt display |

*Using this registry in your project? Open a PR to add your name here.*

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). The short version:

1. Open an issue before starting large changes.
2. Data corrections go through a tool, not hand-edits.
3. Run `python3 tools/validate.py` — must exit 0.
4. Run `python3 -m pytest tests/ -q` — must pass.
5. Run `bash tools/check_cross_language.sh` — must pass.
6. Submit a PR. CI runs five jobs.

**Source discipline.** SWIFT's published MIC file is the only accepted source. No third-party lists, no mirrors, no Wikipedia, no aggregators. If a value cannot be traced to the published file, the field stays `null`.

**Four rules for scripts.**

1. No heredocs for patch scripts. Write `/tmp/script.py`, run it standalone, check its exit code.
2. `set -euo pipefail` at the top of every shell script.
3. Adversarial tests on `/tmp` copies, never on the working tree.
4. File-first. Write a script to a file, run the file, read the output.

---

## License

Apache 2.0. See [`LICENSE`](./LICENSE).

The MIC data in this registry is factual information sourced from SWIFT's published ISO 10383 file. The compilation, schema, tooling, wrappers, and documentation are licensed works.

---

## Author

**Le P'tit** — [github.com/slimissa](https://github.com/slimissa)

---

## What's next

- **ISO 4217 mirror** — add `tools/iso10383_snapshot.json` and a matching check job to the ISO 4217 sibling. Closes the cross-registry loop in both directions.
- **`release.sh` port** — apply the release pipeline to Exchange Calendar, Corporate Actions, and Asset Identifiers. Proves the pattern is portable.
- **MIC→LEI companion** — a v1.1.0 file mapping each operating MIC to the LEI of its legal operator.
- **MIC→BIC companion** — a v1.2.0 file mapping each MIC to its settlement or clearing institution.

See [`CHANGELOG.md`](./CHANGELOG.md) for release history and [`docs/decisions/`](./docs/decisions/) for locked architectural decisions.
