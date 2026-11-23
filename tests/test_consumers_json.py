"""tools/consumers.json is well formed and agrees with schema.json, docs/JOINS.md and the README.

Mirrors iso3166's tests/test_consumers_json.py. The record fields are derived
from schema.json, not hard-coded.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONSUMERS = json.loads((ROOT / "tools" / "consumers.json").read_text(encoding="utf-8"))["consumers"]
JOINS = (ROOT / "docs" / "JOINS.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
SCHEMA = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
FIELDS = set(SCHEMA["properties"]["mics"]["items"]["properties"])


def test_every_consumer_has_the_required_keys():
    assert CONSUMERS
    for c in CONSUMERS:
        assert set(c) == {"name", "repo", "snapshot_path", "fields_read"}
        assert re.fullmatch(r"[\w.-]+/[\w.-]+", c["repo"])
        assert c["snapshot_path"].endswith("_snapshot.json")
        assert c["fields_read"] and set(c["fields_read"]) <= FIELDS, c["fields_read"]


def test_names_and_repos_are_unique():
    assert len({c["name"] for c in CONSUMERS}) == len(CONSUMERS)
    assert len({c["repo"] for c in CONSUMERS}) == len(CONSUMERS)


def test_every_field_read_is_in_that_consumers_joins_md_row():
    section = JOINS.split("## Registries that reference `mic`", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for m in re.finditer(r"^\| ([^|]+?) \|(.*)$", section, re.M):
        rows.setdefault(m.group(1), []).append(m.group(2))
    for c in CONSUMERS:
        assert c["name"] in rows, f"{c['name']} has no row in JOINS.md"
        for f in c["fields_read"]:
            assert any(f"`{f}`" in r for r in rows[c["name"]]), \
                f"{c['name']} reads {f} but its JOINS.md row does not say so"


def test_every_consumer_is_linked_in_readme_section_22():
    section = README.split("## 22. Consumed by", 1)[1].split("## 23.", 1)[0]
    for c in CONSUMERS:
        assert f"https://github.com/{c['repo']}" in section
