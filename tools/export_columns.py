"""Canonical column order for every exported artifact.

Single source of truth. If a column is added, removed, or reordered,
edit here and every exporter follows.

SQL_COLUMNS is the FK-ready minimum: the columns a downstream consumer
needs to join against. CSV_COLUMNS starts with SQL_COLUMNS and appends
the fields intended for human analysis. Parquet uses CSV_COLUMNS.
"""

SQL_COLUMNS: tuple[str, ...] = (
    "mic",
    "mic_type",
    "status",
    "operating_mic",
    "market_name",
    "country_code",
    "market_category",
    "creation_date",
    "last_update_date",
    "last_validation_date",
    "expiration_date",
)

CSV_COLUMNS: tuple[str, ...] = SQL_COLUMNS + (
    "legal_entity_name",
    "acronym",
    "lei",
    "city",
    "website",
    "note",
)

assert CSV_COLUMNS[: len(SQL_COLUMNS)] == SQL_COLUMNS, (
    "CSV_COLUMNS must start with SQL_COLUMNS"
)
