[![Validate](https://github.com/slimissa/iso10383/actions/workflows/validate.yml/badge.svg)](https://github.com/slimissa/iso10383/actions/workflows/validate.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Registry](https://img.shields.io/badge/registry-0.1.0-orange.svg)](./CHANGELOG.md)

# ISO 10383 MIC Registry

**A canonical, versioned, machine-readable registry of ISO 10383 Market Identifier Codes.**

v0.1.0 — work in progress. Phase 0: foundation and locked decisions.

See [`docs/decisions/v1.0.0-decisions.md`](docs/decisions/v1.0.0-decisions.md) for the locked architectural decisions.

---

## Wrappers

Four idiomatic wrappers, one shared contract. Every wrapper reads
`tests/cross_language_consistency.json` and ships a byte-identical
copy of `iso10383.json`.

| Language   | Package                    | Import                                                |
|------------|----------------------------|-------------------------------------------------------|
| Python     | `iso10383-registry`        | `from iso10383 import MICRegistry`                    |
| JavaScript | `iso10383-registry`        | `const { MICRegistry } = require("iso10383-registry")`|
| Rust       | `iso10383-registry`        | `use iso10383_registry::Registry;`                    |
| Go         | `github.com/slimissa/iso10383/wrappers/go` | `import iso10383 "..."`              |

### Consistent API

| Operation        | Python                   | JavaScript               | Rust                       | Go                       |
|------------------|--------------------------|--------------------------|----------------------------|--------------------------|
| Load             | `MICRegistry()`          | `new MICRegistry()`      | `Registry::load()`         | `LoadRegistry()`         |
| Lookup           | `.by_mic("XNYS")`        | `.byMic("XNYS")`         | `.by_mic("XNYS")`          | `.ByMIC("XNYS")`         |
| Segments         | `.segments("XJPX")`      | `.segments("XJPX")`      | `.segments("XJPX")`        | `.Segments("XJPX")`      |
| Parent           | `.operating_mic("XTKS")` | `.operatingMic("XTKS")`  | `.operating_mic("XTKS")`   | `.OperatingMIC("XTKS")`  |
| Expired since    | `.expired(since="...")`  | `.expired("...")`        | `.expired(Some("..."))`    | `.Expired("...")`        |
| Validate         | `.validate([...])`       | `.validate([...])`       | `.validate([...])`         | `.Validate([]string{...})`|

### Verify all four agree

```bash
bash tools/check_cross_language.sh

