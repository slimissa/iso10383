# Security policy

## Reporting a vulnerability

Do not open a public issue for a security vulnerability. Use GitHub's
private vulnerability reporting:

    https://github.com/slimissa/iso10383/security/advisories/new

We acknowledge a report within 72 hours and aim to fix it, or to publish a
remediation plan, within 30 days. Fixes land on `main` and ship in the next
tagged release; tags are never moved (ADR 0005).

## In scope

The registry is a data file and the tools that make and read it. Three
areas, plus the release machinery:

- **The downloader and parser** (`tools/fetch_swift_mic.py`): a downloaded
  file that gets past the parser's invariants (MIC patterns, closed enums,
  the expected column set, parent-chain resolution) and changes the output.
- **The CLI** (`tools/iso10383_cli.py`): path traversal or command injection
  through `--registry` or `ISO10383_REGISTRY`.
- **The wrappers** (Python, JavaScript, Rust, Go): a caller-supplied path or
  object that makes a wrapper read a file it should not, or return data from
  a different registry; a result a caller can mutate to change the registry
  for later callers.
- **The release and refresh machinery** (`scripts/release.sh`, the
  workflows): a path by which a release or a refresh could publish
  something other than what was verified.

## Out of scope

- **The content of the data.** A wrong or missing MIC is a data issue, not
  a security issue. It is fixed at the source, SWIFT's published ISO 10383
  file; open an ordinary issue as described in `CONTRIBUTING.md`, under
  "Reporting a bug".
- **Package registries.** The wrappers are source-only; nothing is published
  to PyPI, npm, crates.io or a Go proxy, so there is no listing to report.
- **Third-party dependencies** (`serde`, `serde_json`, `pyarrow`): report
  upstream; tell us if our pin leaves us affected.

## Data integrity

Two mechanisms let a consumer check what they hold:

1. [`docs/PROVENANCE.md`](./docs/PROVENANCE.md) records where each field
   comes from and how to audit it. `meta.source_hash` in `iso10383.json` is
   the SHA-256 of the SWIFT file the registry was derived from.
2. [`registry_release.json`](./registry_release.json) lists the SHA-256 and
   size of every released artifact (the registry, the schema, the exports,
   the bundled copies) and the pinned version of each vendored snapshot.

Their limits: `registry_release.json` detects a change to a released file
after the release; it cannot detect an error in SWIFT's file or an edit made
before the release. The control for that is review of the refresh pull
request, which shows the NEW, EXPIRED, CHANGED and REMOVED MICs
(`tools/refresh_diff.py`).
