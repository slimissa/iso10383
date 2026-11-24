"""The sibling drift checks compare against the latest release tag, never main.

All offline: tag discovery, the iso3166 fetch and the exchange-calendar clone
are monkeypatched. See docs/decisions/0013-sibling-drift-against-tags.md.
"""
import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import check_exchange_calendar_current as ec  # noqa: E402
import check_iso3166_current as iso  # noqa: E402
import sibling_tags  # noqa: E402

ISO_CODES = json.loads(iso.SNAPSHOT.read_text(encoding="utf-8"))["alpha_2_set"]
ISO_VERSION = json.loads(iso.LOCAL_META.read_text(encoding="utf-8"))["source_version"]
EC_MICS = json.loads(ec.SNAPSHOT.read_text(encoding="utf-8"))["mics"]
EC_VERSION = json.loads(ec.LOCAL_META.read_text(encoding="utf-8"))["source_version"]

LS_REMOTE = "\n".join([
    "aaa\trefs/tags/v1.12.9",
    "bbb\trefs/tags/v1.12.13",
    "ccc\trefs/tags/v1.12.13^{}",       # peeled: ignored
    "ddd\trefs/tags/v1.13.0-rc1",       # pre-release: not strict SemVer
    "eee\trefs/tags/v2.0",              # two parts: not strict SemVer
    "fff\trefs/tags/1.99.0",            # no v prefix
    "ggg\trefs/tags/latest",
    "hhh\trefs/tags/v9.9.9^{}",         # peeled only, no plain ref: ignored
])


# --- tag parsing ----------------------------------------------------------

def test_parse_ignores_peeled_and_non_semver_tags():
    assert sibling_tags.parse_semver_tags(LS_REMOTE) == [(1, 12, 9), (1, 12, 13)]


def test_latest_compares_integers_not_strings():
    assert sibling_tags.latest_from_output(LS_REMOTE) == "v1.12.13"
    out = "a\trefs/tags/v2.9.9\nb\trefs/tags/v2.10.0\nc\trefs/tags/v10.0.0\n"
    assert sibling_tags.latest_from_output(out) == "v10.0.0"


def test_no_release_tag_raises():
    with pytest.raises(sibling_tags.NoReleaseTag):
        sibling_tags.latest_from_output("x\trefs/tags/v1.0.0-rc1\ny\trefs/heads/main\n")
    with pytest.raises(sibling_tags.NoReleaseTag):
        sibling_tags.latest_from_output("")


def test_latest_semver_tag_runs_ls_remote_tags(monkeypatch):
    seen = []

    class P:
        stdout = LS_REMOTE

    def fake_run(cmd, **kwargs):
        seen.append(cmd)
        return P()

    monkeypatch.setattr(sibling_tags.subprocess, "run", fake_run)
    assert sibling_tags.latest_semver_tag("https://x/y.git") == "v1.12.13"
    assert seen == [["git", "ls-remote", "--tags", "https://x/y.git"]]


@pytest.mark.parametrize("mod", [iso, ec], ids=["iso3166", "exchange_calendar"])
def test_no_release_tag_fails_even_with_advisory(mod, monkeypatch, capsys):
    def none(url):
        raise sibling_tags.NoReleaseTag(f"no release tag at {url}")
    monkeypatch.setattr(mod.sibling_tags, "latest_semver_tag", none)
    assert mod.main(["--strict", "--advisory"]) == 1
    assert "FAIL: no release tag" in capsys.readouterr().err


# --- fakes ----------------------------------------------------------------

class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _iso_doc(codes=ISO_CODES, version=ISO_VERSION):
    return {"countries": {"active": [{"alpha_2": c} for c in codes]},
            "meta": {"version": version}}


def _fake_iso(monkeypatch, tag_version, body_for_url):
    """Tag discovery says v<tag_version>; urlopen serves body_for_url(url)."""
    urls = []
    monkeypatch.setattr(iso.sibling_tags, "latest_semver_tag",
                        lambda url: f"v{tag_version}")

    def fake_urlopen(url, **kwargs):
        urls.append(url)
        body = body_for_url(url)
        if isinstance(body, Exception):
            raise body
        return _Resp(body if isinstance(body, bytes) else json.dumps(body).encode())

    monkeypatch.setattr(iso.urllib.request, "urlopen", fake_urlopen)
    return urls


def _write_ec_tree(td, mics=EC_MICS, version=EC_VERSION, exchanges=True,
                   calendar=True, key="mic"):
    td = Path(td)
    if exchanges:
        (td / "exchanges").mkdir(parents=True, exist_ok=True)
        for m in mics:
            (td / "exchanges" / f"{m}.json").write_text(
                json.dumps({key: m}), encoding="utf-8")
    if calendar is True:
        (td / "calendar.json").write_text(
            json.dumps({"meta": {"version": version}}), encoding="utf-8")
    elif isinstance(calendar, dict):
        (td / "calendar.json").write_text(json.dumps(calendar), encoding="utf-8")


def _fake_ec(monkeypatch, tag_version, tree_for_cmd):
    """Tag discovery says v<tag_version>; `git clone` writes tree_for_cmd(cmd)."""
    cmds = []
    monkeypatch.setattr(ec.sibling_tags, "latest_semver_tag",
                        lambda url: f"v{tag_version}")

    def fake_run(cmd, **kwargs):
        cmds.append(cmd)
        _write_ec_tree(cmd[-1], **tree_for_cmd(cmd))

    monkeypatch.setattr(ec.subprocess, "run", fake_run)
    return cmds


# --- the checks read the tag, not main -------------------------------------

def test_iso3166_reads_the_tag_url_not_main(monkeypatch, capsys):
    urls = _fake_iso(monkeypatch, ISO_VERSION, lambda url: _iso_doc())
    assert iso.main(["--strict", "--fail-on-version-drift"]) == 0
    assert urls == [f"https://raw.githubusercontent.com/slimissa/iso3166/v{ISO_VERSION}/iso3166.json"]
    assert all("/main/" not in u for u in urls)
    assert f"upstream version: v{ISO_VERSION}" in capsys.readouterr().out


def test_exchange_calendar_clones_the_tag_not_main(monkeypatch, capsys):
    cmds = _fake_ec(monkeypatch, EC_VERSION, lambda cmd: {})
    assert ec.main(["--strict", "--fail-on-version-drift"]) == 0
    (clone,) = cmds
    assert clone[:2] == ["git", "clone"]
    assert clone[clone.index("--branch") + 1] == f"v{EC_VERSION}"
    assert f"upstream version: v{EC_VERSION}" in capsys.readouterr().out


def test_iso3166_main_behind_latest_tag_still_passes(monkeypatch):
    """The sibling's main says an older version (a reverted release); the tag rules."""
    def body(url):
        if "/main/" in url:
            return _iso_doc(version="1.0.0")
        return _iso_doc()
    _fake_iso(monkeypatch, ISO_VERSION, body)
    assert iso.main(["--strict", "--fail-on-version-drift"]) == 0


def test_exchange_calendar_main_behind_latest_tag_still_passes(monkeypatch):
    """The 2026-11-24 case: exchange-calendar main reverted to 2.33.0 while
    tag v2.34.0 stays. A clone of main would report version drift."""
    def tree(cmd):
        if "--branch" in cmd:
            return {}
        return {"version": "2.33.0"}
    _fake_ec(monkeypatch, EC_VERSION, tree)
    assert ec.main(["--strict", "--fail-on-version-drift"]) == 0


# --- the tag and the file must agree ---------------------------------------

def test_iso3166_tag_and_meta_version_mismatch_fails(monkeypatch, capsys):
    _fake_iso(monkeypatch, ISO_VERSION, lambda url: _iso_doc(version="9.9.9"))
    assert iso.main([]) == 1
    err = capsys.readouterr().err
    assert f"tag v{ISO_VERSION}" in err and "'9.9.9'" in err


def test_exchange_calendar_tag_and_meta_version_mismatch_fails(monkeypatch, capsys):
    _fake_ec(monkeypatch, EC_VERSION, lambda cmd: {"version": "9.9.9"})
    assert ec.main([]) == 1
    err = capsys.readouterr().err
    assert f"tag v{EC_VERSION}" in err and "'9.9.9'" in err


# --- an unreadable layout is "upstream format changed", never stale or pass -

NOT_FOUND = urllib.error.HTTPError("u", 404, "Not Found", {}, None)


@pytest.mark.parametrize("body, what", [
    (NOT_FOUND, "iso3166.json not found at the tag"),
    ({"meta": {"version": ISO_VERSION}}, "key countries.active is missing"),
    ({"countries": {"active": [{"code": "FR"}]}, "meta": {"version": ISO_VERSION}},
     "an entry of countries.active has no alpha_2"),
    (_iso_doc(codes=[]), "countries.active yields an empty alpha-2 set"),
    ({"countries": {"active": [{"alpha_2": "FR"}]}}, "key meta.version is missing"),
    (b"<html>", "iso3166.json is not valid JSON"),
], ids=["missing-file", "missing-key", "missing-entry-key", "empty-set",
        "missing-version", "not-json"])
def test_iso3166_format_change_fails_clearly(monkeypatch, capsys, body, what):
    _fake_iso(monkeypatch, ISO_VERSION, lambda url: body)
    assert iso.main(["--advisory"]) == 1
    captured = capsys.readouterr()
    assert f"FAIL: upstream format changed at v{ISO_VERSION}: {what}" in captured.err
    assert "stale" not in captured.out + captured.err


@pytest.mark.parametrize("tree, what", [
    ({"exchanges": False}, "directory exchanges/ is missing"),
    ({"calendar": False}, "calendar.json is missing"),
    ({"calendar": {"meta": {}}}, "key meta.version is missing from calendar.json"),
    ({"key": "name"}, "exchanges/*.json yields an empty MIC set"),
    ({"mics": []}, "exchanges/*.json yields an empty MIC set"),
], ids=["missing-dir", "missing-file", "missing-key", "no-mic-key", "empty-set"])
def test_exchange_calendar_format_change_fails_clearly(monkeypatch, capsys, tree, what):
    _fake_ec(monkeypatch, EC_VERSION, lambda cmd: tree)
    assert ec.main(["--advisory"]) == 1
    captured = capsys.readouterr()
    assert f"FAIL: upstream format changed at v{EC_VERSION}: {what}" in captured.err
    assert "stale" not in captured.out + captured.err


# --- content drift: --strict fails, the advisory path still exits 0 --------

def test_iso3166_content_drift(monkeypatch, capsys):
    _fake_iso(monkeypatch, ISO_VERSION, lambda url: _iso_doc(codes=ISO_CODES + ["QZ"]))
    assert iso.main(["--strict"]) == 1
    assert "FAIL: snapshot is stale" in capsys.readouterr().err
    assert iso.main([]) == 0
    out = capsys.readouterr().out
    assert "+ QZ" in out and "(advisory: rerun with --strict to fail)" in out


def test_exchange_calendar_content_drift(monkeypatch, capsys):
    _fake_ec(monkeypatch, EC_VERSION, lambda cmd: {"mics": EC_MICS[1:]})
    assert ec.main(["--strict"]) == 1
    assert "FAIL: snapshot is stale" in capsys.readouterr().err
    assert ec.main([]) == 0
    out = capsys.readouterr().out
    assert f"- {EC_MICS[0]}" in out and "(advisory: rerun with --strict to fail)" in out
