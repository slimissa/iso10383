"""tools/revendor.py, offline: generator fetch, upstream bytes and tag discovery faked.

Each test runs on a scratch copy of the files revendor.py reads and of the
files it must never touch (iso10383.json, an export, CHANGELOG.md, the claims).
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gen_exchange_calendar_snapshot as gen_ec  # noqa: E402
import gen_iso3166_snapshot as gen_iso  # noqa: E402
import revendor  # noqa: E402

STEMS = ("iso3166", "exchange_calendar")
UNTOUCHABLE = ["iso10383.json", "iso10383.csv", "CHANGELOG.md", "tools/release_claims.json"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _fake_bytes(url: str) -> bytes:
    return f"upstream file at {url}".encode()


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """Scratch root: both snapshots + metas, and the files revendor must not touch.

    The scratch metas' upstream_sha256 is set to what the fake upstream
    returns for their current tag, so "already current" is representable.
    """
    (tmp_path / "tools").mkdir()
    for s in STEMS:
        for suffix in (".json", ".meta.json"):
            shutil.copy(TOOLS / f"{s}_snapshot{suffix}", tmp_path / "tools" / f"{s}_snapshot{suffix}")
        mp = tmp_path / "tools" / f"{s}_snapshot.meta.json"
        meta = json.loads(mp.read_text(encoding="utf-8"))
        meta["upstream_sha256"] = hashlib.sha256(_fake_bytes(
            revendor.SIBLINGS[s]["upstream_url"].format(v=meta["source_version"]))).hexdigest()
        mp.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for f in UNTOUCHABLE:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / f, tmp_path / f)
    monkeypatch.setattr(revendor, "ROOT", tmp_path)
    monkeypatch.setattr(revendor, "today_utc", lambda: "2026-12-01")

    calls = {"fetch": [], "bytes": []}
    codes = json.loads((TOOLS / "iso3166_snapshot.json").read_text(encoding="utf-8"))["alpha_2_set"]
    mics = json.loads((TOOLS / "exchange_calendar_snapshot.json").read_text(encoding="utf-8"))["mics"]
    sets = {"iso3166": list(codes), "exchange_calendar": list(mics)}

    def fetch_iso(version):
        calls["fetch"].append(("iso3166", version))
        return sorted(sets["iso3166"])

    def fetch_ec(version):
        calls["fetch"].append(("exchange_calendar", version))
        return sorted(sets["exchange_calendar"])

    def fetch_bytes(url):
        calls["bytes"].append(url)
        return _fake_bytes(url)

    monkeypatch.setattr(gen_iso, "fetch_alpha2", fetch_iso)
    monkeypatch.setattr(gen_ec, "fetch_mics", fetch_ec)
    monkeypatch.setattr(revendor, "fetch_bytes", fetch_bytes)
    tags = {"https://github.com/slimissa/iso3166.git": "v1.12.13",
            "https://github.com/slimissa/exchange-calendar.git": "v2.34.0"}
    monkeypatch.setattr(revendor.sibling_tags, "latest_semver_tag", lambda repo: tags[repo])
    return {"root": tmp_path, "calls": calls, "sets": sets, "tags": tags}


def _meta(root, s):
    return json.loads((root / "tools" / f"{s}_snapshot.meta.json").read_text(encoding="utf-8"))


def _all_hashes(root):
    return {str(p.relative_to(root)): _sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def _untouchable(root):
    return {f: _sha(root / f) for f in UNTOUCHABLE}


# --- (b)-(g): every field written, both copies equal ----------------------

@pytest.mark.parametrize("stem, version, cad_period_end, upstream_file", [
    ("iso3166", "1.12.14", "2027-11-30", "/v1.12.14/iso3166.json"),           # yearly
    ("exchange_calendar", "2.35.0", "2027-02-28", "/v2.35.0/checksums.json"),  # quarterly, clamped
])
def test_to_writes_every_field(tree, stem, version, cad_period_end, upstream_file):
    root = tree["root"]
    before = _untouchable(root)
    other = [s for s in STEMS if s != stem][0]
    other_files = [root / "tools" / f"{other}_snapshot{x}" for x in (".json", ".meta.json")]
    other_before = [_sha(f) for f in other_files]
    assert revendor.main([stem, "--to", version, "--date", "2026-11-30"]) == 0
    m = _meta(root, stem)
    snap_path = root / "tools" / f"{stem}_snapshot.json"
    # (c) the generator's render, at the target version
    assert tree["calls"]["fetch"] == [(stem, version)]
    gen = gen_iso if stem == "iso3166" else gen_ec
    assert snap_path.read_text(encoding="utf-8") == gen.render(
        gen.build_snapshot(version, sorted(tree["sets"][stem])))
    # (b), (g) source_version and the other copies, equal at both levels
    for k in ("source", "source_version", "vendored_at"):
        assert m[k] == m["meta"][k], k
    assert m["source_version"] == version
    assert m["vendored_at"] == "2026-11-30"
    # (d) upstream_sha256 from the file at the tag
    (url,) = tree["calls"]["bytes"]
    assert url.endswith(upstream_file)
    assert m["upstream_sha256"] == hashlib.sha256(_fake_bytes(url)).hexdigest()
    # (e) snapshot_sha256 and vendored_from
    assert m["snapshot_sha256"] == _sha(snap_path)
    assert f"/blob/v{version}/" in m["vendored_from"]
    # (f) the cadence rule, cadence kept
    assert m["meta"]["review_by"] == cad_period_end
    assert m["meta"]["refresh_cadence"] == _meta_at_head(stem)["meta"]["refresh_cadence"]
    # the other sibling and the human-step files are untouched
    assert [_sha(f) for f in other_files] == other_before
    assert _untouchable(root) == before


def _meta_at_head(stem):
    return json.loads((TOOLS / f"{stem}_snapshot.meta.json").read_text(encoding="utf-8"))


def test_month_end_clamp_follows_the_cadence(tree):
    root = tree["root"]
    assert revendor.main(["exchange_calendar", "--to", "2.35.0", "--date", "2027-11-30"]) == 0
    assert _meta(root, "exchange_calendar")["meta"]["review_by"] == "2028-02-29"


def test_latest_resolves_the_highest_tag_for_each_sibling(tree):
    tree["tags"]["https://github.com/slimissa/iso3166.git"] = "v1.13.0"
    tree["tags"]["https://github.com/slimissa/exchange-calendar.git"] = "v2.40.1"
    assert revendor.main(["all", "--latest"]) == 0
    assert sorted(tree["calls"]["fetch"]) == [("exchange_calendar", "2.40.1"), ("iso3166", "1.13.0")]
    assert _meta(tree["root"], "iso3166")["source_version"] == "1.13.0"
    assert _meta(tree["root"], "exchange_calendar")["source_version"] == "2.40.1"


def test_default_is_latest_and_today_utc(tree):
    tree["tags"]["https://github.com/slimissa/iso3166.git"] = "v1.13.0"
    assert revendor.main(["iso3166"]) == 0
    m = _meta(tree["root"], "iso3166")
    assert (m["source_version"], m["vendored_at"], m["meta"]["vendored_at"]) == ("1.13.0", "2026-12-01", "2026-12-01")


def test_summary_reports_the_set_change(tree, capsys):
    tree["sets"]["iso3166"].append("QZ")
    tree["sets"]["iso3166"].remove("FR")
    assert revendor.main(["iso3166", "--to", "1.12.14"]) == 0
    out = capsys.readouterr().out
    assert "1.12.13 -> 1.12.14" in out
    assert "added ['QZ'], removed ['FR']" in out
    assert "Still manual" in out and "CHANGELOG.md" in out


# --- --check writes nothing -------------------------------------------------

def test_check_exits_1_when_behind_and_writes_nothing(tree, capsys):
    root = tree["root"]
    tree["tags"]["https://github.com/slimissa/exchange-calendar.git"] = "v2.35.0"
    before = _all_hashes(root)
    assert revendor.main(["all", "--check"]) == 1
    assert _all_hashes(root) == before
    out = capsys.readouterr().out
    assert "exchange_calendar: would change" in out and "iso3166: current" in out


def test_check_exits_0_when_current_and_writes_nothing(tree, capsys):
    root = tree["root"]
    before = _all_hashes(root)
    assert revendor.main(["all", "--check"]) == 0
    assert _all_hashes(root) == before
    out = capsys.readouterr().out
    assert "iso3166: current" in out and "exchange_calendar: current" in out


def test_check_with_date_compares_the_dates(tree):
    m = _meta(tree["root"], "iso3166")
    assert revendor.main(["iso3166", "--check", "--date", m["vendored_at"]]) == 0
    assert revendor.main(["iso3166", "--check", "--date", "2030-01-01"]) == 1


# --- usage errors exit 2 ----------------------------------------------------

@pytest.mark.parametrize("argv", [
    ["iso4217"],                                  # unknown sibling
    ["all", "--to", "1.2.3"],                     # --to needs one sibling
    ["iso3166", "--to", "1.2"],                   # not X.Y.Z
    ["iso3166", "--date", "2026-02-30"],          # not a date
    ["iso3166", "--to", "1.2.3", "--latest"],     # mutually exclusive
], ids=["unknown-sibling", "to-with-all", "bad-version", "bad-date", "to-and-latest"])
def test_usage_errors_exit_2(tree, argv):
    before = _all_hashes(tree["root"])
    with pytest.raises(SystemExit) as e:
        revendor.main(argv)
    assert e.value.code == 2
    assert _all_hashes(tree["root"]) == before


# --- the Makefile target ----------------------------------------------------

def _make_targets():
    """{target: recipe lines} from the Makefile."""
    targets, cur = {}, None
    for line in (REPO / "Makefile").read_text(encoding="utf-8").splitlines():
        if line and not line[0].isspace() and ":" in line and not line.startswith(("#", ".")) \
                and "?=" not in line and "=" not in line.split(":", 1)[0]:
            cur = line.split(":", 1)[0].strip()
            targets[cur] = [line.split(":", 1)[1].strip()]
        elif line.startswith("\t") and cur:
            targets[cur].append(line.strip())
        elif not line.strip():
            cur = None
    return targets


def test_make_revendor_target_exists_and_is_not_in_package_or_test():
    t = _make_targets()
    assert t["revendor"][1:] == ["$(PYTHON) tools/revendor.py $(SIBLING) $(ARGS)"]
    for name in ("package", "test"):
        assert not any("revendor" in line for line in t[name]), name
    assert "revendor" in (REPO / "Makefile").read_text(encoding="utf-8").split(".PHONY:", 1)[1].splitlines()[0]
