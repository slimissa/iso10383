#!/usr/bin/env python3
"""iso10383 — command-line interface to the ISO 10383 MIC registry.

Eight subcommands:

  lookup MIC            all fields for one MIC
  list                  filter across the registry
  segments MIC          direct segment children of an operating MIC
  parent MIC            the operating_mic field of a segment
  expired --since DATE  expired MICs on or after DATE
  validate MIC...       exit 0 if all exist
  search QUERY          substring on market_name and acronym
  info                  registry metadata

Five output modes (mutually exclusive):

  --json   JSON object or array
  --jsonl  one JSON object per line
  --csv    columns match iso10383.csv
  --tsv    columns match iso10383.tsv
  --raw F  bare FIELD values, one per line

Exit codes: 0 OK, 1 not found, 2 usage, 3 registry missing.

Color: on when stdout is a TTY, off when piped. Override with
ISO10383_COLOR=never|auto|always or --color/--no-color. NO_COLOR is
respected unless --color=always is given.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import signal
import sys
from pathlib import Path
from typing import Any, Iterable

from export_columns import CSV_COLUMNS

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_USAGE = 2
EXIT_NO_REGISTRY = 3

DEFAULT_REGISTRY = Path("iso10383.json")
ENV_REGISTRY = "ISO10383_REGISTRY"
ENV_COLOR = "ISO10383_COLOR"

MIC_RE = re.compile(r"^[A-Z0-9]{4}$")

# ---------------------------------------------------------------- color

class C:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.reset = "\033[0m" if enabled else ""
        self.bold  = "\033[1m"  if enabled else ""
        self.dim   = "\033[2m"  if enabled else ""
        self.red   = "\033[31m" if enabled else ""
        self.green = "\033[32m" if enabled else ""
        self.cyan  = "\033[36m" if enabled else ""


def _install_sigpipe() -> None:
    """Match Unix conventions: die silently when stdout's pipe closes."""
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass


def color_decision(args: argparse.Namespace) -> bool:
    if getattr(args, "no_color", False):
        return False
    if getattr(args, "color", None) == "always":
        return True
    if getattr(args, "color", None) == "never":
        return False
    env = os.environ.get(ENV_COLOR, "auto").lower()
    if env == "always":
        return True
    if env == "never":
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()

# ---------------------------------------------------------------- registry

def load_registry(path: Path) -> dict:
    if not path.is_file():
        print(f"registry not found: {path}", file=sys.stderr)
        sys.exit(EXIT_NO_REGISTRY)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"registry unreadable: {e}", file=sys.stderr)
        sys.exit(EXIT_NO_REGISTRY)
    if "mics" not in data or "meta" not in data:
        print(f"registry missing 'mics' or 'meta': {path}", file=sys.stderr)
        sys.exit(EXIT_NO_REGISTRY)
    return data


def index_by_mic(data: dict) -> dict[str, dict]:
    return {m["mic"]: m for m in data["mics"]}

# ---------------------------------------------------------------- output

def _scalar(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


def emit_csv(rows: list[dict], delimiter: str) -> None:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(
        buf, fieldnames=list(CSV_COLUMNS), delimiter=delimiter,
        quoting=csv.QUOTE_MINIMAL, lineterminator="\n",
    )
    w.writeheader()
    for r in rows:
        w.writerow({c: _scalar(r.get(c)) for c in CSV_COLUMNS})
    sys.stdout.write(buf.getvalue())


def emit_json(obj: Any) -> None:
    sys.stdout.write(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )


def emit_jsonl(rows: Iterable[dict]) -> None:
    for r in rows:
        sys.stdout.write(
            json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n"
        )


def emit_raw(rows: Iterable[dict], field: str) -> None:
    for r in rows:
        v = r.get(field)
        if v is None:
            continue
        if isinstance(v, list):
            for x in v:
                sys.stdout.write(f"{x}\n")
        else:
            sys.stdout.write(f"{v}\n")


def emit_table(rows: list[dict], fields: list[str], c: C) -> None:
    if not rows:
        return
    widths = {f: max(len(f), max(len(_scalar(r.get(f))) for r in rows))
              for f in fields}
    header = "  ".join(f"{c.bold}{f.upper():<{widths[f]}}{c.reset}"
                       for f in fields)
    print(header)
    for r in rows:
        print("  ".join(f"{_scalar(r.get(f)):<{widths[f]}}" for f in fields))


def emit_kv(entry: dict, c: C) -> None:
    width = max(len(k) for k in entry)
    for k in sorted(entry):
        v = entry[k]
        if v is None:
            v = ""
        print(f"{c.bold}{k:<{width}}{c.reset}  {v}")


def dispatch(rows: list[dict], args: argparse.Namespace, c: C,
             human: bool = True, human_fields: list[str] | None = None) -> None:
    """Route to the requested output mode. `human` is the fallback when
    no mode is set."""
    if args.json:
        emit_json(rows if len(rows) != 1 else rows[0])
    elif args.jsonl:
        emit_jsonl(rows)
    elif args.csv:
        emit_csv(rows, ",")
    elif args.tsv:
        emit_csv(rows, "\t")
    elif args.raw:
        emit_raw(rows, args.raw)
    elif human:
        if len(rows) == 1:
            emit_kv(rows[0], c)
        else:
            emit_table(rows, human_fields or list(CSV_COLUMNS), c)

# ---------------------------------------------------------------- commands

def cmd_lookup(data: dict, mic: str, args, c) -> int:
    if not MIC_RE.fullmatch(mic):
        print(f"invalid MIC: {mic!r}", file=sys.stderr)
        return EXIT_USAGE
    by = index_by_mic(data)
    entry = by.get(mic)
    if entry is None:
        print(f"not found: {mic}", file=sys.stderr)
        return EXIT_NOT_FOUND
    dispatch([entry], args, c)
    return EXIT_OK


def cmd_list(data: dict, args, c) -> int:
    rows = data["mics"]
    if args.country:
        rows = [m for m in rows if m.get("country_code") == args.country]
    if args.category:
        rows = [m for m in rows if m.get("market_category") == args.category]
    if args.status:
        rows = [m for m in rows if m.get("status") == args.status]
    if args.mic_type:
        rows = [m for m in rows if m.get("mic_type") == args.mic_type]
    dispatch(rows, args, c,
             human_fields=["mic", "mic_type", "status",
                           "country_code", "market_category", "market_name"])
    return EXIT_OK


def cmd_segments(data: dict, mic: str, args, c) -> int:
    if not MIC_RE.fullmatch(mic):
        print(f"invalid MIC: {mic!r}", file=sys.stderr)
        return EXIT_USAGE
    by = index_by_mic(data)
    if mic not in by:
        print(f"not found: {mic}", file=sys.stderr)
        return EXIT_NOT_FOUND
    # Direct children only. A grandchild whose parent is another segment
    # is not listed here; use `parent` to walk one hop at a time.
    rows = [m for m in data["mics"]
            if m["mic_type"] == "SEGMENT" and m["operating_mic"] == mic]
    dispatch(rows, args, c,
             human_fields=["mic", "mic_type", "status",
                           "country_code", "market_category", "market_name"])
    return EXIT_OK


def cmd_parent(data: dict, mic: str, args, c) -> int:
    if not MIC_RE.fullmatch(mic):
        print(f"invalid MIC: {mic!r}", file=sys.stderr)
        return EXIT_USAGE
    by = index_by_mic(data)
    entry = by.get(mic)
    if entry is None:
        print(f"not found: {mic}", file=sys.stderr)
        return EXIT_NOT_FOUND
    parent = entry["operating_mic"]
    if args.raw:
        print(parent)
        return EXIT_OK
    if args.json:
        emit_json({"mic": mic, "operating_mic": parent,
                   "is_self": parent == mic})
        return EXIT_OK
    # Human
    if parent == mic:
        print(f"{c.dim}{mic} is an operating MIC (self-referencing){c.reset}")
    else:
        print(f"{mic} -> {parent}")
    return EXIT_OK


def cmd_expired(data: dict, since: str, args, c) -> int:
    if since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        print(f"invalid --since (want YYYY-MM-DD): {since!r}", file=sys.stderr)
        return EXIT_USAGE
    rows = [m for m in data["mics"] if m["status"] == "EXPIRED"]
    if since:
        rows = [m for m in rows
                if (m.get("expiration_date") or "") >= since]
    rows.sort(key=lambda m: m.get("expiration_date") or "")
    dispatch(rows, args, c,
             human_fields=["mic", "expiration_date",
                           "country_code", "market_name"])
    return EXIT_OK


def cmd_validate(data: dict, mics: list[str], args, c) -> int:
    by = index_by_mic(data)
    missing = [m for m in mics if m not in by]
    if missing:
        for m in missing:
            print(f"not found: {m}", file=sys.stderr)
        return EXIT_NOT_FOUND
    if not args.quiet:
        print(f"{c.green}OK{c.reset}: {len(mics)} MIC(s) validated")
    return EXIT_OK


def cmd_search(data: dict, query: str, args, c) -> int:
    q = query.lower()
    rows = [m for m in data["mics"]
            if q in (m.get("market_name") or "").lower()
            or q in (m.get("acronym") or "").lower()]
    dispatch(rows, args, c,
             human_fields=["mic", "mic_type", "status",
                           "acronym", "market_name"])
    return EXIT_OK


def cmd_info(data: dict, args, c) -> int:
    meta = data["meta"]
    if args.json:
        emit_json(meta)
        return EXIT_OK
    emit_kv({k: meta[k] for k in ("version", "updated", "source_snapshot",
                                  "source_url", "source_hash")}, c)
    counts = meta["counts"]
    print()
    print(f"{c.bold}counts{c.reset}")
    for k in ("operating", "segment", "active", "updated", "expired", "total"):
        print(f"  {k:<10}  {counts[k]}")
    broken = len(meta.get("broken_chains", []))
    print(f"  {'broken':<10}  {broken}")
    return EXIT_OK


def cmd_check(data: dict, args, c) -> int:
    """Built-in smoke test. Loads the registry and asserts invariants."""
    by = index_by_mic(data)
    failures: list[str] = []

    def expect(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    ground_truth = {
        "XNYS": {"mic_type": "OPERATING", "country_code": "US"},
        "XLON": {"mic_type": "OPERATING", "country_code": "GB"},
        "XTKS": {"mic_type": "SEGMENT",   "country_code": "JP"},
        "XPAR": {"country_code": "FR"},
    }
    for mic, want in ground_truth.items():
        e = by.get(mic)
        if e is None:
            failures.append(f"{mic} missing")
            continue
        for field, expected in want.items():
            expect(e.get(field) == expected,
                   f"{mic}.{field} = {e.get(field)!r}, want {expected!r}")

    for m in data["mics"]:
        if m["mic_type"] == "OPERATING" and m["operating_mic"] != m["mic"]:
            failures.append(f"{m['mic']}: operating not self-referencing")
            break

    expect(len(data["meta"].get("broken_chains", [])) == 0,
           "broken_chains not empty")
    expect(data["meta"]["counts"]["operating"] >= 1500,
           "operating count below 1500")
    expect(data["meta"]["counts"]["segment"] >= 1000,
           "segment count below 1000")
    expect(data["meta"]["counts"]["total"] >= 2500,
           "total count below 2500")

    if failures:
        for f in failures:
            print(f"{c.red}FAIL{c.reset}: {f}", file=sys.stderr)
        return EXIT_NOT_FOUND

    if not args.quiet:
        c_meta = data["meta"]["counts"]
        print(f"{c.green}OK{c.reset}: {len(data['mics'])} MICs, "
              f"{c_meta['operating']} operating, "
              f"{c_meta['segment']} segment, 0 broken chains")
    return EXIT_OK

# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="iso10383",
        description="Query the ISO 10383 MIC registry.",
    )
    p.add_argument("--registry", type=Path,
                   default=Path(os.environ.get(ENV_REGISTRY,
                                               str(DEFAULT_REGISTRY))),
                   help=f"Path to iso10383.json (default: $"
                        f"{ENV_REGISTRY} or ./{DEFAULT_REGISTRY})")
    # Output flags live on every subparser so they may be given after
    # the subcommand, e.g. `iso10383 lookup XNYS --json`.
    output = argparse.ArgumentParser(add_help=False)
    output.add_argument("--color", choices=["never", "auto", "always"],
                        default=None)
    output.add_argument("--no-color", action="store_true")
    output.add_argument("--quiet", action="store_true")
    out = output.add_mutually_exclusive_group()
    out.add_argument("--json", action="store_true")
    out.add_argument("--jsonl", action="store_true")
    out.add_argument("--csv", action="store_true")
    out.add_argument("--tsv", action="store_true")
    out.add_argument("--raw", metavar="FIELD")

    sub = p.add_subparsers(dest="cmd", required=True, metavar="SUBCOMMAND")

    sp = sub.add_parser("lookup", help="all fields for one MIC",
                        parents=[output])
    sp.add_argument("mic")

    sp = sub.add_parser("list", help="filter across the registry",
                        parents=[output])
    sp.add_argument("--country", metavar="CC")
    sp.add_argument("--category", metavar="CODE")
    sp.add_argument("--status", choices=["ACTIVE", "UPDATED", "EXPIRED"])
    sp.add_argument("--mic-type", choices=["OPERATING", "SEGMENT"])

    sp = sub.add_parser("segments", help="direct segments of a parent MIC",
                        parents=[output])
    sp.add_argument("mic")

    sp = sub.add_parser("parent", help="the operating_mic of a MIC",
                        parents=[output])
    sp.add_argument("mic")

    sp = sub.add_parser("expired", help="expired MICs",
                        parents=[output])
    sp.add_argument("--since", metavar="YYYY-MM-DD", default="")

    sp = sub.add_parser("validate", help="exit 0 if every MIC exists",
                        parents=[output])
    sp.add_argument("mics", nargs="+")

    sp = sub.add_parser("search", help="substring on market_name and acronym",
                        parents=[output])
    sp.add_argument("query")

    sub.add_parser("info", help="registry metadata",
                   parents=[output])
    sub.add_parser("check", help="built-in smoke test",
                   parents=[output])

    return p


def main(argv: list[str] | None = None) -> int:
    _install_sigpipe()
    args = build_parser().parse_args(argv)
    c = C(color_decision(args))
    data = load_registry(args.registry)

    try:
        if args.cmd == "lookup":
            return cmd_lookup(data, args.mic, args, c)
        if args.cmd == "list":
            return cmd_list(data, args, c)
        if args.cmd == "segments":
            return cmd_segments(data, args.mic, args, c)
        if args.cmd == "parent":
            return cmd_parent(data, args.mic, args, c)
        if args.cmd == "expired":
            return cmd_expired(data, args.since, args, c)
        if args.cmd == "validate":
            return cmd_validate(data, args.mics, args, c)
        if args.cmd == "search":
            return cmd_search(data, args.query, args, c)
        if args.cmd == "info":
            return cmd_info(data, args, c)
        if args.cmd == "check":
            return cmd_check(data, args, c)
    except BrokenPipeError:
        # Consumer closed the pipe (e.g. `| head`). Not an error.
        try:
            sys.stdout.close()
        finally:
            return EXIT_OK

    print(f"unknown subcommand: {args.cmd}", file=sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
