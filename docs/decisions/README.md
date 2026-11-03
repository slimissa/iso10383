# Architecture decision records

Twelve ADRs, `0001` to `0012`, plus the register of locked decisions made
before v1.0.0. Start here to find which one answers a question.

| ADR | Question it answers | Status | Amendments / Supersedes |
|-----|---------------------|--------|-------------------------|
| 0001 | [What is SWIFT's file, exactly?](./0001-source-format.md) | Accepted | none |
| 0002 | [How are operating MICs and segment MICs modelled?](./0002-operating-segment-model.md) | Accepted | none |
| 0003 | [How often does the registry refresh, and when is a snapshot too old?](./0003-monthly-refresh.md) | Accepted | Two amendments, both 2026-10-10: the `REMOVED > 0` guard did not fire; the guard's mechanism is a draft PR |
| 0004 | [Which market category codes are allowed?](./0004-market-category-codes.md) | Accepted | none |
| 0005 | [When is a release tag created, and what does the verification document record?](./0005-tag-discipline.md) | Accepted | none |
| 0006 | [How do the local gate and the CI gate agree on what "verified" means?](./0006-ci-toolchain-parity.md) | Accepted | none |
| 0007 | [How is a known gap against Exchange Calendar tolerated?](./0007-cross-registry-allowlist.md) | Accepted | Amendment 2026-10-10: the three allowlisted gaps closed, the allowlist is empty |
| 0008 | [Should there be a MIC→LEI companion file?](./0008-mic-lei-companion-declined.md) | Accepted (companion declined) | Supersedes D11's inclusion of "MIC→LEI" in the out-of-scope list |
| 0009 | [Should there be a MIC→BIC companion file?](./0009-mic-bic-companion-declined.md) | Accepted (companion declined) | Supersedes D11's inclusion of "MIC→BIC" in the out-of-scope list |
| 0010 | [What is the registry for, who consumes it, and what layers does it have?](./0010-platform-charter.md) | Accepted | Supersedes the undated draft `D18-platform-charter.md` (removed). Amendments: 2026-10-10; 2026-10-18 (two, on different claims) |
| 0011 | [What does the refresh do step by step, and is reprocessing a capability?](./0011-reprocessing.md) | Accepted | Amendments: 2026-10-10; 2026-10-18 |
| 0012 | [What may a future agent read, and what may it write?](./0012-agent-read-surface.md) | Accepted | none |

The Status column copies each ADR's own `**Status:**` header. No ADR is
superseded by another. "Amendments" lists the dated `## Amendment`
sections at the end of the ADR itself; read them with the body, because
an amendment corrects the text above it.

## The locked decisions D1 to D17

[`v1.0.0-decisions.md`](./v1.0.0-decisions.md) holds the seventeen
decisions locked before v1.0.0. Each carries a `**Status:**` line. The
ADRs above expand or amend several of them: D6 and D17 by ADR 0007, D9
and D10 by ADR 0003 (D10 also by ADR 0011), and D11 by ADRs 0008 and 0009.

## Keeping this index true

When an ADR is added, amended or superseded, update its row here in the
same commit. The table is not generated.
