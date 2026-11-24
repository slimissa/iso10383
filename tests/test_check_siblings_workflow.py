""".github/workflows/check-siblings.yml is scheduled only and runs both drift checks.

release.sh polls the per-push workflows for the release SHA and assumes there
is one (scripts/release.sh, "poll scope"); a push trigger here would need
check_workflows_covered first. See docs/decisions/0013-sibling-drift-against-tags.md.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
WF_PATH = WORKFLOWS / "check-siblings.yml"
WF_TEXT = WF_PATH.read_text(encoding="utf-8")
WF = yaml.safe_load(WF_TEXT)


def _triggers(doc):
    # YAML 1.1 reads the bare key `on` as the boolean True.
    on = doc.get("on", doc.get(True))
    return {on: None} if isinstance(on, str) else dict(on or {})


def test_no_push_or_pull_request_trigger():
    t = _triggers(WF)
    assert "push" not in t and "pull_request" not in t, t


def test_schedule_weekly_monday_0630_and_manual_dispatch():
    t = _triggers(WF)
    assert set(t) == {"schedule", "workflow_dispatch"}
    assert [s["cron"] for s in t["schedule"]] == ["30 6 * * 1"]


def test_permissions_are_exactly_contents_read_and_issues_write():
    assert WF["permissions"] == {"contents": "read", "issues": "write"}
    for job in WF["jobs"].values():
        assert "permissions" not in job


def test_runs_both_checks_strict_without_version_drift_failure():
    (job,) = WF["jobs"].values()
    siblings = job["strategy"]["matrix"]["sibling"]
    assert sorted(siblings) == ["exchange_calendar", "iso3166"]
    for s in siblings:
        assert (ROOT / "tools" / f"check_{s}_current.py").is_file()
    runs = [step.get("run", "") for step in job["steps"]]
    (check,) = [s["run"] for s in job["steps"] if s.get("id") == "check"]
    assert 'python3 "tools/check_${SIBLING}_current.py" --strict' in check
    assert not any("--fail-on-version-drift" in r for r in runs)


def test_opens_or_comments_on_one_issue_per_sibling():
    (job,) = WF["jobs"].values()
    issue = [s for s in job["steps"] if "gh issue" in s.get("run", "")]
    assert len(issue) == 1
    run = issue[0]["run"]
    assert 'title="Sibling drift: $SIBLING"' in run
    for cmd in ('gh issue list --state open --search "\\"$title\\" in:title"',
                "gh issue comment", "gh issue create"):
        assert cmd in run, cmd
    assert "RUN_URL" in issue[0]["env"] and "$RUN_URL" in run


def test_release_poll_still_sees_one_per_push_workflow():
    per_push = sorted(p.name for p in WORKFLOWS.glob("*.yml")
                      if "push" in _triggers(yaml.safe_load(p.read_text(encoding="utf-8"))))
    assert per_push == ["validate.yml"]
