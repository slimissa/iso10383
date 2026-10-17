"""Python wrapper tests. Every expected value reads from anchors.py."""

from pathlib import Path

from iso10383 import MICRegistry

from anchors import CASES, REG, XNYS, XTKS


# --- shape of the bundled snapshot ---

def test_load_bundled():
    r = MICRegistry()
    assert len(r) > 0
    assert r.version == REG.version
    assert r.source_snapshot == REG.source_snapshot
    assert r.source_hash.startswith("sha256:")


def test_load_from_explicit_path():
    p = Path(__file__).resolve().parents[3] / "iso10383.json"
    r = MICRegistry(p)
    assert len(r) == len(REG)


def test_counts_add_up():
    c = REG.counts
    assert c["operating"] + c["segment"] == c["total"]
    assert c["active"] + c["updated"] + c["expired"] == c["total"]


# --- contract fixture cases ---

def test_contract_lookup_xnys():
    c = CASES["lookup_xnys"]
    m = REG.by_mic(c["args"][0])
    assert m is not None
    for k, v in c["expect"].items():
        assert getattr(m, k) == v, f"{k}: {getattr(m, k)!r} != {v!r}"


def test_contract_lookup_xtks():
    c = CASES["lookup_xtks"]
    m = REG.by_mic(c["args"][0])
    assert m is not None
    for k, v in c["expect"].items():
        assert getattr(m, k) == v


def test_contract_lookup_missing():
    c = CASES["lookup_missing"]
    assert REG.by_mic(c["args"][0]) is None


def test_contract_segments_contains_xtks():
    c = CASES["segments_xjpx_contains_xtks"]
    segs = REG.segments(c["args"][0])
    want = c["expect_contains"]
    assert any(
        all(getattr(s, k) == v for k, v in want.items())
        for s in segs
    )


def test_contract_segments_xjpx_not_empty():
    assert len(REG.segments("XJPX")) > 0


def test_contract_parent_xtks():
    c = CASES["parent_xtks"]
    assert REG.operating_mic(c["args"][0]) == c["expect"]


def test_contract_parent_of_operating_is_self():
    c = CASES["parent_of_operating_is_self"]
    assert REG.operating_mic(c["args"][0]) == c["expect"]


def test_contract_expired_since_2024():
    c = CASES["expired_since_2024"]
    rows = REG.expired(since=c["args"][0])
    assert len(rows) >= c["expect_count_min"]
    for r in rows:
        assert r.status == c["expect_all_status"]
        assert (r.expiration_date or "") >= c["expect_all_expiration_ge"]


def test_contract_search_nasdaq():
    c = CASES["search_nasdaq_count"]
    assert len(REG.search(c["args"][0])) >= c["expect_count_min"]


def test_contract_by_country_us():
    c = CASES["list_by_country_us"]
    rows = REG.by_country(c["args"][0])
    assert len(rows) >= c["expect_count_min"]
    for r in rows:
        for k, v in c["expect_all_field"].items():
            assert getattr(r, k) == v


def test_contract_by_status_active():
    c = CASES["list_by_status_active"]
    rows = REG.by_status(c["args"][0])
    assert len(rows) >= c["expect_count_min"]
    for r in rows:
        for k, v in c["expect_all_field"].items():
            assert getattr(r, k) == v


def test_contract_by_mic_type_segment():
    c = CASES["list_by_mic_type_segment"]
    rows = REG.by_mic_type(c["args"][0])
    assert len(rows) >= c["expect_count_min"]
    for r in rows:
        for k, v in c["expect_all_field"].items():
            assert getattr(r, k) == v


def test_contract_expired_tie_order_stable():
    c = CASES["expired_tie_order_stable"]
    field = c["expect_order_by"]
    position = {m.mic: i for i, m in enumerate(REG.all())}
    rows = REG.expired(since=c["args"][0])
    keys = [(getattr(m, field) or "", position[m.mic]) for m in rows]
    # Ascending by the field; equal values keep registry order.
    assert keys == sorted(keys)


def test_contract_lookup_lowercase():
    c = CASES["lookup_lowercase"]
    m = REG.by_mic(c["args"][0])
    assert m is not None
    for k, v in c["expect"].items():
        assert getattr(m, k) == v


def test_contract_segments_lowercase():
    c = CASES["segments_lowercase"]
    segs = REG.segments(c["args"][0])
    want = c["expect_contains"]
    assert any(
        all(getattr(s, k) == v for k, v in want.items())
        for s in segs
    )


def test_contract_by_status_lowercase():
    c = CASES["by_status_lowercase"]
    rows = REG.by_status(c["args"][0])
    assert len(rows) >= c["expect_count_min"]
    for r in rows:
        for k, v in c["expect_all_field"].items():
            assert getattr(r, k) == v


def test_contract_validate_lowercase_input():
    c = CASES["validate_lowercase_input"]
    ok, missing = REG.validate(c["args"][0])
    assert ok is c["expect_ok"]
    assert missing == []


def test_validate_is_case_insensitive():
    r = MICRegistry()
    assert r.validate(["xnys"]) == (True, [])
    assert r.validate(["XNYS"]) == (True, [])
    # Misses are reported as the caller spelled them.
    assert r.validate(["xnys", "zzzz"]) == (False, ["zzzz"])


def test_pipe_annotations_require_future_import():
    # requires-python is >=3.9. There, `X | None` in an annotation is
    # evaluated when the function is defined and raises TypeError,
    # unless annotations are deferred with the __future__ import.
    import ast

    src = Path(__file__).resolve().parents[1] / "src" / "iso10383"
    for path in sorted(src.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        deferred = any(
            isinstance(n, ast.ImportFrom)
            and n.module == "__future__"
            and any(a.name == "annotations" for a in n.names)
            for n in tree.body
        )
        uses_pipe = False
        for node in ast.walk(tree):
            anns = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                anns = [node.returns] + [
                    a.annotation
                    for a in args.posonlyargs + args.args + args.kwonlyargs
                ]
            elif isinstance(node, ast.AnnAssign):
                anns = [node.annotation]
            for ann in anns:
                if ann is not None and any(
                    isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr)
                    for n in ast.walk(ann)
                ):
                    uses_pipe = True
        assert deferred or not uses_pipe, (
            f"{path.name} uses X | Y annotations without "
            "from __future__ import annotations"
        )


def test_package_version_matches_version_file():
    import iso10383

    version_file = Path(__file__).resolve().parents[3] / "VERSION"
    assert iso10383.__version__ == version_file.read_text(encoding="utf-8").strip()


def test_contract_validate_all_present():
    c = CASES["validate_all_present"]
    ok, missing = REG.validate(c["args"][0])
    assert ok is c["expect_ok"]
    assert missing == []


def test_contract_validate_missing():
    c = CASES["validate_missing_returns_false"]
    ok, missing = REG.validate(c["args"][0])
    assert ok is c["expect_ok"]
    assert set(missing) == set(c["expect_missing"])


# --- copy semantics ---

def test_lookup_returns_fresh_object():
    a = REG.by_mic("XNYS")
    b = REG.by_mic("XNYS")
    assert a is not None and b is not None
    assert a == b and a is not b


def test_all_is_defensive_copy():
    rows = REG.all()
    n = len(rows)
    rows.append(rows[0])
    assert len(REG.all()) == n
