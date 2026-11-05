#!/usr/bin/env python3
"""Compare two ways to give 5,000 orders their venue details.

  wide    copy the registry fields into every order row
  narrow  keep only the MIC on the order and join to iso10383.parquet

Run generate_facts.py first. Everything printed is measured on the files
it wrote and on the repository's iso10383.parquet; the orders are
synthetic, the registry rows are real. Part 3 SIMULATES a registry
change (the registry itself is not modified).

    python3 analyze.py [--data DIR] [--registry PATH]
"""

import argparse
import io
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
COPIED = ["market_name", "legal_entity_name", "acronym", "country_code",
          "city", "website", "status"]


def default_data() -> Path:
    return Path(tempfile.gettempdir()) / "iso10383-orders-5k"


def as_strings(table: pa.Table) -> pa.Table:
    """Decode dictionary columns so a table can be a join payload."""
    cols = []
    for name in table.column_names:
        col = table[name]
        if pa.types.is_dictionary(col.type):
            col = col.cast(col.type.value_type)
        cols.append(col)
    return pa.table(cols, names=table.column_names)


def csv_bytes(table: pa.Table) -> int:
    buf = io.BytesIO()
    pacsv.write_csv(table, buf)
    return buf.tell()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", type=Path, default=default_data(),
                   help="Directory generate_facts.py wrote to (default: %(default)s)")
    p.add_argument("--registry", type=Path, default=ROOT / "iso10383.parquet",
                   help="Registry Parquet (default: the repository's)")
    args = p.parse_args(argv)

    narrow_path = args.data / "orders_narrow.parquet"
    wide_path = args.data / "orders_wide.parquet"
    for path in (narrow_path, wide_path, args.registry):
        if not path.is_file():
            print(f"not found: {path} (run generate_facts.py first)", file=sys.stderr)
            return 2

    narrow = pq.read_table(narrow_path)
    wide = pq.read_table(wide_path)
    registry = pq.read_table(args.registry)
    snapshot = registry.schema.metadata[b"iso10383.source_snapshot"].decode()
    n = narrow.num_rows
    print(f"{n:,} synthetic orders, {pc.count_distinct(narrow['mic']).as_py()} "
          f"real venues, registry snapshot {snapshot}\n")

    # 1. What copying costs in storage --------------------------------------
    print("1. Storage")
    print(f"   {'':14}{'parquet':>10}{'in memory':>12}{'as CSV':>10}")
    for name, path, table in (("narrow", narrow_path, narrow),
                              ("wide", wide_path, wide)):
        print(f"   {name:14}{path.stat().st_size:>10,}{table.nbytes:>12,}"
              f"{csv_bytes(table):>10,}")
    extra_pq = wide_path.stat().st_size - narrow_path.stat().st_size
    extra_mem = wide.nbytes - narrow.nbytes
    print(f"   copying adds {extra_pq:,} bytes of Parquet and {extra_mem:,} "
          f"bytes in memory ({extra_mem // n} per order)")
    reg_size = args.registry.stat().st_size
    print(f"   the join's other side, {args.registry.name}, is "
          f"{reg_size:,} bytes, shared by every table")
    both = narrow_path.stat().st_size + reg_size
    verdict = "more" if both > wide_path.stat().st_size else "less"
    print(f"   narrow + the whole registry file: {both:,} bytes, {verdict} than "
          f"wide ({wide_path.stat().st_size:,}) in Parquet at this row count\n")

    # 2. What the join gives, on day one -------------------------------------
    print("2. Join on mic")
    reg = as_strings(registry.select(["mic"] + COPIED))
    joined = narrow.join(reg, keys="mic", join_type="left outer")
    unmatched = pc.sum(pc.is_null(joined["market_name"]).cast(pa.int64())).as_py()
    print(f"   {n - unmatched:,} of {n:,} orders found their MIC in the registry")
    wide_s = wide.sort_by("order_id")
    joined_s = joined.sort_by("order_id")
    same = all(wide_s[c].equals(joined_s[c]) for c in COPIED)
    print(f"   joined fields equal the copied fields: {same}")
    print("   on the day the copy is made, the two layouts agree\n")

    # 3. What happens when the registry changes (SIMULATED) -----------------
    print("3. A registry change (simulated; iso10383.parquet is not touched)")
    counts = pc.value_counts(narrow["mic"]).to_pylist()
    counts.sort(key=lambda d: (-d["counts"], d["values"]))
    renamed, expired = counts[0]["values"], counts[1]["values"]
    rows = reg.to_pylist()
    for r in rows:
        if r["mic"] == renamed:
            r["market_name"] = r["market_name"] + " (RENAMED)"
        if r["mic"] == expired:
            r["status"] = "EXPIRED"
    reg_after = pa.Table.from_pylist(rows, schema=reg.schema)
    joined_after = narrow.join(reg_after, keys="mic",
                               join_type="left outer").sort_by("order_id")
    stale = sum(
        1 for a, b in zip(wide_s["market_name"].to_pylist(),
                          joined_after["market_name"].to_pylist()) if a != b
    ) + sum(
        1 for a, b in zip(wide_s["status"].to_pylist(),
                          joined_after["status"].to_pylist()) if a != b)
    hit = sum(1 for m in narrow["mic"].to_pylist() if m in (renamed, expired))
    print(f"   {renamed}: market_name changes; {expired}: status becomes EXPIRED")
    print(f"   registry rows to change:        2")
    print(f"   order rows the join corrects:   {hit:,} of {n:,}, with no write to the orders")
    print(f"   order rows the copy leaves stale: {stale:,}")
    print("   to fix the copy, those rows must be found and rewritten\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
