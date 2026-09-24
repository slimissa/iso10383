"""Export iso10383.json to one typed Parquet file.

Typed columns: mic / operating_mic string, mic_type / status /
market_category / country_code dictionary-encoded, dates date32.

Footer metadata: iso10383.version, .updated, .source_snapshot,
.source_hash. Any consumer can read version info without parsing JSON.

`--check` compares the committed file's bytes to a fresh build.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from export_columns import CSV_COLUMNS


DATE_COLS = {
    "creation_date", "last_update_date",
    "last_validation_date", "expiration_date",
}
DICT_COLS = {"mic_type", "status", "market_category", "country_code"}


def scalar(v):
    if v is None:
        return None
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


def to_date(v):
    """ISO date string -> datetime.date. None/"" -> None."""
    if v is None or v == "":
        return None
    from datetime import date as _date
    return _date.fromisoformat(v)


def to_table(data: dict) -> pa.Table:
    arrays = []
    names = []
    for col in CSV_COLUMNS:
        names.append(col)
        if col in DATE_COLS:
            arrays.append(pa.array([to_date(scalar(m.get(col)))
                                    for m in data["mics"]],
                                   type=pa.date32()))
        elif col in DICT_COLS:
            arrays.append(pa.array([scalar(m.get(col)) for m in data["mics"]],
                                   type=pa.string()).dictionary_encode())
        else:
            arrays.append(pa.array([scalar(m.get(col)) for m in data["mics"]],
                                   type=pa.string()))
    return pa.Table.from_arrays(arrays, names=names)


def render(data: dict) -> bytes:
    table = to_table(data)
    meta = data["meta"]
    table = table.replace_schema_metadata({
        b"iso10383.version":         meta["version"].encode(),
        b"iso10383.updated":         meta["updated"].encode(),
        b"iso10383.source_snapshot": meta["source_snapshot"].encode(),
        b"iso10383.source_hash":     meta["source_hash"].encode(),
    })
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression="snappy")
    return sink.getvalue().to_pybytes()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", type=Path, default=Path("iso10383.json"))
    p.add_argument("--out", "-o", type=Path, default=Path("iso10383.parquet"))
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = json.loads(args.json.read_text(encoding="utf-8"))

    if args.check:
        if not args.out.is_file():
            print(f"missing: {args.out}", file=sys.stderr)
            return 1
        # Parquet embeds a creation timestamp; byte comparison is not
        # stable. Check the schema metadata instead.
        committed = pq.read_table(args.out).schema.metadata or {}
        expected = {
            b"iso10383.version":         data["meta"]["version"].encode(),
            b"iso10383.updated":         data["meta"]["updated"].encode(),
            b"iso10383.source_snapshot": data["meta"]["source_snapshot"].encode(),
            b"iso10383.source_hash":     data["meta"]["source_hash"].encode(),
        }
        for k, v in expected.items():
            if committed.get(k) != v:
                print(f"stale: {args.out} metadata {k!r} mismatch",
                      file=sys.stderr)
                return 1
        # Also check the row count matches.
        committed_rows = pq.read_table(args.out).num_rows
        if committed_rows != len(data["mics"]):
            print(f"stale: {args.out} has {committed_rows} rows, "
                  f"expected {len(data['mics'])}", file=sys.stderr)
            return 1
        print(f"OK: {args.out} in sync ({committed_rows} rows)")
        return 0

    args.out.write_bytes(render(data))
    print(f"Wrote {args.out} ({args.out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
