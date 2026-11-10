"""RCP-21: every figure the README states about the data must match iso10383.json.
One test, all mismatches reported at once, so a stale README is diagnosed in one run."""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
C = collections.Counter


def _facts():
    d = json.loads((ROOT / "iso10383.json").read_text(encoding="utf-8"))
    return d["meta"], d["mics"]


def test_readme_figures_match_data():
    meta, mics = _facts()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    ix = {m["mic"]: m for m in mics}
    F = lambda n: f"{n:,}"
    total = len(mics)
    typ = C(m["mic_type"] for m in mics)
    st = C(m["status"] for m in mics)
    op, sg = typ["OPERATING"], typ["SEGMENT"]
    act, upd, exp = st["ACTIVE"], st["UPDATED"], st["EXPIRED"]
    by = {t: C(m["status"] for m in mics if m["mic_type"] == t) for t in ("OPERATING", "SEGMENT")}
    segs = [m for m in mics if m["mic_type"] == "SEGMENT"]
    so = sum(ix[m["operating_mic"]]["mic_type"] == "OPERATING" for m in segs)
    ss = sum(ix[m["operating_mic"]]["mic_type"] == "SEGMENT" for m in segs)
    parents = len({m["operating_mic"] for m in segs if ix[m["operating_mic"]]["mic_type"] == "OPERATING"})
    since = sum(1 for m in mics if m["status"] == "EXPIRED" and (m.get("expiration_date") or "") >= "2024-01-01")
    lei = sum(1 for m in mics if m.get("lei"))
    nodate = sum(1 for m in mics if not m.get("expiration_date"))
    problems = []

    # meta.counts must agree with the entries
    want = {"total": total, "operating": op, "segment": sg, "active": act, "updated": upd, "expired": exp}
    for k, v in want.items():
        if meta["counts"].get(k) != v:
            problems.append(f"meta.counts.{k} = {meta['counts'].get(k)}, entries give {v}")

    expected = [
        f"{F(total)} MICs ({F(op)} operating, {F(sg)} segment)",
        f"MICs-{total}-blue.svg",
        f"| **MICs** | {F(total)}: {F(op)} operating, {F(sg)} segment |",
        f"| **Status** | {F(act)} `ACTIVE`, {upd} `UPDATED`, {F(exp)} `EXPIRED`.",
        f"[('OPERATING', {op}), ('SEGMENT', {sg})]",
        f"[('ACTIVE', {act}), ('EXPIRED', {exp}), ('UPDATED', {upd})]",
        f"| Operating | {F(op)} ({F(by['OPERATING']['ACTIVE'])} active, {by['OPERATING']['EXPIRED']} expired, {by['OPERATING']['UPDATED']} updated) |",
        f"| Segment | {F(sg)} ({by['SEGMENT']['ACTIVE']} active, {by['SEGMENT']['EXPIRED']} expired, {by['SEGMENT']['UPDATED']} updated) |",
        f"| Total | {F(total)} |",
        f"| Active / Updated / Expired | {F(act)} / {upd} / {F(exp)} |",
        f"| `ACTIVE` | In force | {F(act)} |",
        f"| Expired on or after 2024-01-01 | {since} |",
        f"| Operating MICs | {F(op)} |",
        f"| Operating MICs that have at least one segment | {F(parents)} |",
        f"| Segments directly under an operating MIC (one hop to the root) | {F(so)} |",
        f"| Segments under another segment (two hops to the root) | {ss} |",
        f"{F(so)} segments sit directly under an operating MIC, {ss} sit under another segment",
        f"({F(lei)} of {F(total)} entries; {total - lei} are null)",
        f"| `expiration_date` | date or null | {F(nodate)} |",
        f"`OK: {total} MICs, {op} operating, {sg} segment, 0 broken chains`",
        f"prints `OK: {total} MICs validated`",
        f"| 11 (`mics`) | {F(total)} | `tools/export_sql.py` |",
        f"| 17 | {F(total)} | `tools/export_csv.py` |",
        f"| `iso10383.parquet` | 17 | {F(total)} | `tools/export_parquet.py` |",
        f"({F(total)} MICs)",
        f"{F(total)} data rows ({F(total + 1)} lines)",
    ]
    for s in expected:
        if s not in readme:
            problems.append(f"README does not contain: {s!r}")
    assert not problems, "README figures disagree with iso10383.json:\n  " + "\n  ".join(problems)
