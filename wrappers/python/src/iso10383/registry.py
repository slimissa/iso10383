"""MICRegistry - read-only access to an iso10383 snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Iterable


def _bundled_path() -> Path:
    return Path(str(files("iso10383").joinpath("data/iso10383.json")))


@dataclass(frozen=True)
class MIC:
    mic: str
    mic_type: str
    status: str
    operating_mic: str
    market_name: str | None = None
    legal_entity_name: str | None = None
    lei: str | None = None
    market_category: str | None = None
    acronym: str | None = None
    country_code: str | None = None
    city: str | None = None
    website: str | None = None
    creation_date: str | None = None
    last_update_date: str | None = None
    last_validation_date: str | None = None
    expiration_date: str | None = None
    note: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MIC":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


class MICRegistry:
    """Load iso10383.json and answer MIC queries.

    Passing no source loads the bundled snapshot. Passing a path reads
    that file. Passing a parsed dict is also accepted.
    """

    def __init__(self, source: str | Path | dict | None = None):
        if source is None:
            data = json.loads(_bundled_path().read_text(encoding="utf-8"))
        elif isinstance(source, dict):
            data = source
        else:
            data = json.loads(Path(source).read_text(encoding="utf-8"))

        self._meta: dict[str, Any] = data["meta"]
        self._mics: list[dict[str, Any]] = data["mics"]
        self._by_mic: dict[str, dict[str, Any]] = {
            m["mic"]: m for m in self._mics
        }

    # --- metadata ---

    @property
    def version(self) -> str:
        return self._meta["version"]

    @property
    def updated(self) -> str:
        return self._meta["updated"]

    @property
    def source_snapshot(self) -> str:
        return self._meta["source_snapshot"]

    @property
    def source_hash(self) -> str:
        return self._meta["source_hash"]

    @property
    def counts(self) -> dict[str, int]:
        return dict(self._meta["counts"])

    @property
    def broken_chains(self) -> list[dict[str, Any]]:
        return list(self._meta.get("broken_chains", []))

    # --- queries ---

    def __len__(self) -> int:
        return len(self._mics)

    def all(self) -> list[MIC]:
        return [MIC.from_dict(m) for m in self._mics]

    def by_mic(self, mic: str) -> MIC | None:
        m = self._by_mic.get(mic.upper())
        return MIC.from_dict(m) if m else None

    def segments(self, mic: str) -> list[MIC]:
        """Direct children of an operating MIC.

        A grandchild whose parent is another segment is not listed
        here. Walk with `operating_mic` for multi-level chains.
        """
        u = mic.upper()
        return [MIC.from_dict(m) for m in self._mics
                if m["mic_type"] == "SEGMENT" and m["operating_mic"] == u]

    def operating_mic(self, mic: str) -> str | None:
        m = self._by_mic.get(mic.upper())
        return m["operating_mic"] if m else None

    def expired(self, since: str | None = None) -> list[MIC]:
        rows = [m for m in self._mics if m["status"] == "EXPIRED"]
        if since:
            rows = [m for m in rows
                    if (m.get("expiration_date") or "") >= since]
        rows.sort(key=lambda m: m.get("expiration_date") or "")
        return [MIC.from_dict(m) for m in rows]

    def by_country(self, code: str) -> list[MIC]:
        u = code.upper()
        return [MIC.from_dict(m) for m in self._mics
                if m.get("country_code") == u]

    def by_status(self, status: str) -> list[MIC]:
        u = status.upper()
        return [MIC.from_dict(m) for m in self._mics if m["status"] == u]

    def by_mic_type(self, mic_type: str) -> list[MIC]:
        u = mic_type.upper()
        return [MIC.from_dict(m) for m in self._mics if m["mic_type"] == u]

    def by_category(self, category: str) -> list[MIC]:
        return [MIC.from_dict(m) for m in self._mics
                if m.get("market_category") == category]

    def search(self, query: str) -> list[MIC]:
        q = query.lower()
        return [MIC.from_dict(m) for m in self._mics
                if q in (m.get("market_name") or "").lower()
                or q in (m.get("acronym") or "").lower()]

    def validate(self, mics: Iterable[str]) -> tuple[bool, list[str]]:
        missing = [m for m in mics if m not in self._by_mic]
        return (not missing, missing)
