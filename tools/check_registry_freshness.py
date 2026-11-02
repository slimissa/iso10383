"""Fail if meta.source_snapshot is more than 60 days old.

Registry freshness (this tool) answers "is the source publication
current?" Snapshot freshness (check_snapshot_freshness.py) answers
"have the vendored snapshots been reviewed?" Two mechanisms, two
questions. See docs/RELEASE_PATTERN.md section "Registry freshness
vs. snapshot freshness".

Exit codes:
  0  source_snapshot is within --max-days of today
  1  source_snapshot is older than --max-days
  2  file not found, or invalid --today
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

MAX_DAYS = 60


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", type=Path, default=Path("iso10383.json"),
        help="Path to iso10383.json (default: iso10383.json).",
    )
    parser.add_argument(
        "--max-days", type=int, default=MAX_DAYS,
        help=f"Maximum age in days (default: {MAX_DAYS}).",
    )
    parser.add_argument(
        "--today", default=date.today().isoformat(),
        help="Override today's date (YYYY-MM-DD). For tests.",
    )
    args = parser.parse_args(argv)

    try:
        today = datetime.strptime(args.today, "%Y-%m-%d").date()
    except ValueError:
        print(f"invalid --today: {args.today!r}", file=sys.stderr)
        return 2

    if not args.path.is_file():
        print(f"FAIL: {args.path} not found", file=sys.stderr)
        return 2

    data = json.loads(args.path.read_text(encoding="utf-8"))
    snapshot = datetime.strptime(
        data["meta"]["source_snapshot"], "%Y-%m-%d"
    ).date()
    age = (today - snapshot).days

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
