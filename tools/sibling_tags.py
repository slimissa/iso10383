"""Latest release tag of a sibling registry, from `git ls-remote --tags`.

"Latest" is the highest SemVer among tags named exactly vX.Y.Z, compared as
integer tuples (v1.12.13 > v1.12.9). Peeled entries (`^{}`) and any tag that
is not strict SemVer (v1.0.0-rc1, 1.2.3, latest) are ignored. The sibling
drift checks and tools/revendor.py compare against this tag, never against
the sibling's main branch (docs/decisions/0013-sibling-drift-against-tags.md).
"""

import re
import subprocess

TAG_RE = re.compile(r"^refs/tags/v(\d+)\.(\d+)\.(\d+)$")


class NoReleaseTag(Exception):
    """The sibling was reached but has no tag matching ^vX.Y.Z$."""


def parse_semver_tags(ls_remote_output: str) -> list[tuple[int, int, int]]:
    """Versions of the strict-SemVer tags in `git ls-remote --tags` output.

    Pure, for offline tests. Each line is "<sha>\\t<ref>"; peeled lines end
    in ^{} and do not match TAG_RE, so they drop out.
    """
    out = set()
    for line in ls_remote_output.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        m = TAG_RE.match(parts[1].strip())
        if m:
            out.add(tuple(int(g) for g in m.groups()))
    return sorted(out)


def latest_from_output(ls_remote_output: str, repo_url: str = "") -> str:
    """Highest strict-SemVer tag name ("vX.Y.Z"); NoReleaseTag if none."""
    versions = parse_semver_tags(ls_remote_output)
    if not versions:
        raise NoReleaseTag(f"no release tag matching ^v<major>.<minor>.<patch>$ at {repo_url}")
    return "v%d.%d.%d" % versions[-1]


def latest_semver_tag(repo_url: str) -> str:
    """Latest release tag of repo_url ("vX.Y.Z").

    Raises subprocess.CalledProcessError / OSError when the sibling cannot be
    reached (the caller treats that as unreachable), NoReleaseTag when it was
    reached but has no release tag.
    """
    proc = subprocess.run(["git", "ls-remote", "--tags", repo_url],
                          check=True, capture_output=True, text=True, timeout=60)
    return latest_from_output(proc.stdout, repo_url)
