"""Export iso10383.json to CSV, TSV, Excel CSV, European CSV.

Four files at repo root:
  iso10383.csv           RFC 4180, UTF-8
  iso10383.excel.csv     UTF-8 with BOM for Windows Excel
  iso10383.european.csv  semicolon-delimited for FR/DE/ES/IT locales
  iso10383.tsv           tab-separated

No comment header. The first row is column names. LF line endings.
`--check` verifies the committed files are byte-identical to a fresh
build; CI uses it to fail on drift.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from export_columns import CSV_COLUMNS


def scalar(v):
    """JSON value -> string. None -> empty. Lists -> space-joined."""
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


def rows(data: dict):
    for m in data["mics"]:
        yield {c: scalar(m.get(c)) for c in CSV_COLUMNS}


def render_csv(data: dict, delimiter: str, bom: bool) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(
        buf,
        fieldnames=list(CSV_COLUMNS),
        delimiter=delimiter,
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    writer.writeheader()
    for r in rows(data):
        writer.writerow(r)
    text = buf.getvalue()
    if bom:
        return b"\xef\xbb\xbf" + text.encode("utf-8")
    return text.encode("utf-8")


OUTPUTS = {
    "iso10383.csv":          (",", False),
    "iso10383.excel.csv":    (",", True),
    "iso10383.european.csv": (";", False),
    "iso10383.tsv":          ("\t", False),
}


def build_all(data: dict) -> dict[str, bytes]:
    return {name: render_csv(data, *args) for name, args in OUTPUTS.items()}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", type=Path, default=Path("iso10383.json"))
    p.add_argument("--check", action="store_true",
                   help="Verify committed files match a fresh build.")
    args = p.parse_args()

    data = json.loads(args.json.read_text(encoding="utf-8"))
    artifacts = build_all(data)

    if args.check:
        drift = []
        for name, content in artifacts.items():
            path = Path(name)
            if not path.is_file():
                drift.append(f"missing: {name}")
                continue
            if path.read_bytes() != content:
                drift.append(f"stale:   {name}")
        if drift:
            for d in drift:
                print(d, file=sys.stderr)
            print(f"FAIL: {len(drift)} artifact(s) out of sync", file=sys.stderr)
            return 1
        print(f"OK: {len(artifacts)} CSV/TSV artifacts in sync")
        return 0

    for name, content in artifacts.items():
        Path(name).write_bytes(content)
        print(f"Wrote {name} ({len(content):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
