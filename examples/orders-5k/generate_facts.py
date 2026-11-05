#!/usr/bin/env python3
"""Generate 5,000 fictional orders across 50 real venues.

REAL:      the 50 MICs, and every registry field copied next to them
           (market name, country, city, status ...), read from
           iso10383.json at the repository root.
SYNTHETIC: every order. Ids, sides, quantities, prices and timestamps
           come from a seeded random generator. None of it is trading
           data and none of it says anything about the venues.

Writes two Parquet files, in one directory:

  orders_narrow.parquet  order_id, mic, side, quantity, price, ts
  orders_wide.parquet    the same rows, plus registry fields copied in

The output goes outside the repository by default (the system temp
directory) so a run leaves the checkout clean.

    python3 generate_facts.py [--out DIR] [--registry PATH]
"""

import argparse
import datetime as dt
import json
import random
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
SEED = 10383
N_ORDERS = 5000
N_VENUES = 50

# Registry fields a team might copy into its order table.
COPIED = ["market_name", "legal_entity_name", "acronym", "country_code",
          "city", "website", "status"]


def default_out() -> Path:
    return Path(tempfile.gettempdir()) / "iso10383-orders-5k"


def pick_venues(mics: list[dict], rng: random.Random) -> list[dict]:
    """50 active operating MICs with a country, chosen with a fixed seed."""
    pool = sorted(
        (m for m in mics
         if m["mic_type"] == "OPERATING" and m["status"] == "ACTIVE"
         and m.get("country_code")),
        key=lambda m: m["mic"])
    return sorted(rng.sample(pool, N_VENUES), key=lambda m: m["mic"])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=default_out(),
                   help="Output directory (default: %(default)s)")
    p.add_argument("--registry", type=Path, default=ROOT / "iso10383.json",
                   help="Registry JSON (default: the repository's)")
    args = p.parse_args(argv)

    if not args.registry.is_file():
        print(f"not found: {args.registry}", file=sys.stderr)
        return 2
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    venues = pick_venues(registry["mics"], rng)

    # Uneven volume: venue i gets weight 1/(i+1), so a few venues dominate.
    weights = [1.0 / (i + 1) for i in range(len(venues))]
    start = dt.datetime(2026, 1, 5, 9, 0, 0)
    rows = []
    for n in range(N_ORDERS):
        v = rng.choices(venues, weights)[0]
        rows.append({
            "order_id": f"O{n + 1:06d}",
            "mic": v["mic"],
            "side": rng.choice(["BUY", "SELL"]),
            "quantity": rng.randint(1, 100) * 100,
            "price": round(rng.uniform(1.0, 500.0), 2),
            "ts": start + dt.timedelta(seconds=7 * n + rng.randint(0, 6)),
        })

    narrow = pa.table({
        "order_id": pa.array([r["order_id"] for r in rows], pa.string()),
        "mic": pa.array([r["mic"] for r in rows], pa.string()),
        "side": pa.array([r["side"] for r in rows], pa.string()),
        "quantity": pa.array([r["quantity"] for r in rows], pa.int32()),
        "price": pa.array([r["price"] for r in rows], pa.float64()),
        "ts": pa.array([r["ts"] for r in rows], pa.timestamp("s")),
    })

    by_mic = {v["mic"]: v for v in venues}
    wide = narrow
    for field in COPIED:
        col = pa.array([by_mic[r["mic"]].get(field) for r in rows], pa.string())
        wide = wide.append_column(field, col)

    args.out.mkdir(parents=True, exist_ok=True)
    pq.write_table(narrow, args.out / "orders_narrow.parquet")
    pq.write_table(wide, args.out / "orders_wide.parquet")
    print(f"{N_ORDERS:,} orders across {len(venues)} venues "
          f"(seed {SEED}) written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
