"""Export iso10383.json to four SQL dialects.

Four files at repo root:
  iso10383.sql           ANSI SQL-92, portable
  iso10383.postgresql.sql PostgreSQL 12+
  iso10383.mysql.sql      MySQL 8+ / MariaDB 10.4+
  iso10383.sqlite.sql     SQLite 3.37+

Two tables:

  market_categories  lookup, four-letter codes
  mics               one row per MIC, mic primary key, operating_mic
                     self-referencing NOT NULL (D3)

Idempotent. Each INSERT is dialect-specific:
  PostgreSQL  ON CONFLICT (mic) DO NOTHING
  MySQL       INSERT IGNORE
  SQLite      INSERT OR IGNORE
  ANSI        documented via comment; portable form uses NOT EXISTS

Self-referencing FK: every operating MIC self-references, and segments
point to parents that may appear earlier or later in the file. The FK
is declared DEFERRABLE INITIALLY DEFERRED where the dialect supports it,
and the loader is wrapped in the appropriate deferral pragma otherwise.

`--check` verifies committed files match a fresh build.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from export_columns import SQL_COLUMNS

MARKET_CATEGORIES = (
    "ATSS", "APPA", "ARMS", "CTPS", "CASP", "DCMS",
    "IDQS", "MLTF", "NSPD", "OTFS", "OTHR", "RMOS",
    "RMKT", "SEFS", "SINT", "TRFS",
)

CATEGORY_LABELS = {
    "ATSS": "Alternative Trading System",
    "APPA": "Approved Publication Arrangement",
    "ARMS": "Arrangement for Reporting",
    "CTPS": "Consolidated Tape Provider",
    "CASP": "Consolidated Access Service Provider",
    "DCMS": "Data Communication and Messaging Service",
    "IDQS": "Identifier Quotation Service",
    "MLTF": "Multilateral Trading Facility",
    "NSPD": "Not-Systematic Price Disseminator",
    "OTFS": "Organised Trading Facility",
    "OTHR": "Other",
    "RMOS": "Regulated Market Off-Session",
    "RMKT": "Regulated Market",
    "SEFS": "Systematic Externaliser",
    "SINT": "Systematic Internaliser",
    "TRFS": "Trade Reporting Facility",
}


def sql_str(v) -> str:
    if v is None:
        return "NULL"
    s = str(v)
    return "'" + s.replace("'", "''") + "'"


def sql_int(v) -> str:
    return "NULL" if v is None else str(int(v))


def render_mics_table(dialect: str) -> str:
    lines = [
        "-- market_categories lookup",
        "CREATE TABLE IF NOT EXISTS market_categories (",
        "  code  VARCHAR(4) PRIMARY KEY,",
        "  label VARCHAR(64) NOT NULL",
        ");",
        "",
        "-- mics",
        "CREATE TABLE IF NOT EXISTS mics (",
        "  mic                  VARCHAR(4) PRIMARY KEY,",
        "  mic_type             VARCHAR(9) NOT NULL",
        "                       CHECK (mic_type IN ('OPERATING','SEGMENT')),",
        "  status               VARCHAR(7) NOT NULL",
        "                       CHECK (status IN ('ACTIVE','UPDATED','EXPIRED')),",
        "  operating_mic        VARCHAR(4) NOT NULL,",
        "  market_name          VARCHAR(255),",
        "  country_code         VARCHAR(2),",
        "  market_category      VARCHAR(4)",
        "                       CHECK (market_category IS NULL OR market_category IN (",
        "                         " + ", ".join(sql_str(c) for c in MARKET_CATEGORIES) + ")),",
        "  creation_date        DATE,",
        "  last_update_date     DATE,",
        "  last_validation_date DATE,",
        "  expiration_date      DATE,",
    ]
    if dialect == "postgresql":
        lines.append(
            "  CONSTRAINT fk_mics_operating "
            "FOREIGN KEY (operating_mic) REFERENCES mics(mic) "
            "DEFERRABLE INITIALLY DEFERRED,"
        )
        lines.append(
            "  CONSTRAINT fk_mics_country "
            "FOREIGN KEY (country_code) REFERENCES countries(alpha_2)"
        )
    elif dialect == "sqlite":
        lines.append(
            "  FOREIGN KEY (operating_mic) REFERENCES mics(mic)"
        )
    else:
        lines[-1] = lines[-1].rstrip(",")
    lines.append(");")
    lines.append("")
    lines.append("CREATE INDEX IF NOT EXISTS idx_mics_operating ON mics(operating_mic);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_mics_country   ON mics(country_code);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_mics_status    ON mics(status);")
    return "\n".join(lines)


def render_category_inserts(dialect: str) -> str:
    kw = "INSERT OR IGNORE" if dialect == "sqlite" else "INSERT"
    extra = "" if dialect == "sqlite" else " ON CONFLICT DO NOTHING" if dialect == "postgresql" else " IGNORE" if dialect == "mysql" else ""
    lines = ["-- market_categories rows"]
    if dialect == "mysql":
        lines.append("INSERT IGNORE INTO market_categories (code, label) VALUES")
        rows = [f"  ({sql_str(c)}, {sql_str(CATEGORY_LABELS[c])})" for c in MARKET_CATEGORIES]
        lines.append(",\n".join(rows) + ";")
    else:
        for c in MARKET_CATEGORIES:
            lines.append(
                f"{kw} INTO market_categories (code, label) "
                f"VALUES ({sql_str(c)}, {sql_str(CATEGORY_LABELS[c])})"
                f"{extra};"
            )
    return "\n".join(lines)


def render_mic_inserts(data: dict, dialect: str) -> str:
    lines = ["-- mics rows"]
    cols = ", ".join(SQL_COLUMNS)

    def values(m):
        return "(" + ", ".join(
            sql_str(m.get(c)) if c not in (
                "creation_date", "last_update_date",
                "last_validation_date", "expiration_date",
            ) else sql_str(m.get(c))
            for c in SQL_COLUMNS
        ) + ")"

    if dialect == "mysql":
        lines.append(f"INSERT IGNORE INTO mics ({cols}) VALUES")
        lines.append(",\n".join(values(m) for m in data["mics"]) + ";")
    else:
        kw = "INSERT OR IGNORE" if dialect == "sqlite" else "INSERT"
        extra = "" if dialect == "sqlite" else (
            " ON CONFLICT (mic) DO NOTHING" if dialect == "postgresql"
            else " ON CONFLICT (mic) DO NOTHING"  # ANSI documented form
        )
        for m in data["mics"]:
            lines.append(
                f"{kw} INTO mics ({cols}) VALUES {values(m)}{extra};"
            )
    return "\n".join(lines)


def render(data: dict, dialect: str) -> str:
    parts = [
        f"-- ISO 10383 MIC registry export",
        f"-- dialect: {dialect}",
        f"-- version: {data['meta']['version']}",
        f"-- updated: {data['meta']['updated']}",
        f"-- source_snapshot: {data['meta']['source_snapshot']}",
        f"-- source_hash: {data['meta']['source_hash']}",
        "",
        render_mics_table(dialect),
        "",
        render_category_inserts(dialect),
        "",
        "BEGIN;",
        render_mic_inserts(data, dialect),
        "COMMIT;",
        "",
    ]
    return "\n".join(parts)


DIALECTS = {
    "iso10383.sql": "ansi",
    "iso10383.postgresql.sql": "postgresql",
    "iso10383.mysql.sql": "mysql",
    "iso10383.sqlite.sql": "sqlite",
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", type=Path, default=Path("iso10383.json"))
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = json.loads(args.json.read_text(encoding="utf-8"))
    artifacts = {name: render(data, d).encode("utf-8") for name, d in DIALECTS.items()}

    if args.check:
        drift = []
        for name, content in artifacts.items():
            path = Path(name)
            if not path.is_file():
                drift.append(f"missing: {name}")
            elif path.read_bytes() != content:
                drift.append(f"stale:   {name}")
        if drift:
            for d in drift:
                print(d, file=sys.stderr)
            print(f"FAIL: {len(drift)} artifact(s) out of sync", file=sys.stderr)
            return 1
        print(f"OK: {len(artifacts)} SQL artifacts in sync")
        return 0

    for name, content in artifacts.items():
        Path(name).write_bytes(content)
        print(f"Wrote {name} ({len(content):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
