"""Fail if meta.source_snapshot is more than 60 days old."""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

MAX_DAYS = 60


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", type=Path, default=Path("iso10383.json"),
        help="Path to iso10383.json (default: iso10383.json).",
    )
    parser.add_argument(
        "--max-days", type=int, default=MAX_DAYS,
        help=f"Maximum age in days (default: {MAX_DAYS}).",
    )
    args = parser.parse_args()

    if not args.path.is_file():
        print(f"FAIL: {args.path} not found", file=sys.stderr)
        return 2

    data = json.loads(args.path.read_text(encoding="utf-8"))
    snapshot = datetime.strptime(
        data["meta"]["source_snapshot"], "%Y-%m-%d"
    ).date()
    age = (date.today() - snapshot).days

    if age > args.max_days:
        print(
            f"FAIL: source_snapshot is {age} days old (max {args.max_days})",
            file=sys.stderr,
        )
        return 1

    print(f"OK: source_snapshot is {age} days old (max {args.max_days})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
