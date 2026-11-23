# ABOUTME: Guards every ~/repos path the docs name after the ~/repos restructure (#4): none sits
# ABOUTME: under a retired group or names a moved repo, and each lies inside a git checkout on disk.
import os
import re
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT

# The three spellings the issue's own verification loop searches for.
REPOS_PATH = re.compile(r"(?:~|\$HOME|/home/michael)/repos/([A-Za-z0-9_./-]+)")

# Groups the 2026-09-20/21 restructure removed outright. `events/` split across talks/,
# conferences/, agenticburn/ and clients/; a path under it can never resolve again.
RETIRED_GROUPS = {"events"}

# Repos that moved to a new path whose old path may still exist as a folder, so an existence check
# alone passes. The Toronto standby repo moved down a level and was renamed on 2026-11-16, leaving
# its old path as the talk folder that now holds it (talks-knowledge,
# sister-repos/reading-agent-mcp-calls-through-otel-talk.md).
MOVED = {
    "talks/reading-agent-mcp-calls-through-otel":
        "talks/reading-agent-mcp-calls-through-otel/reading-agent-mcp-calls-through-otel-talk",
}

# decisions.md is append-only: its old entries record paths as they were and are never edited, so
# a later move could not be fixed there. tests/ holds fixtures and the assertions on these docs.
NOT_SCANNED = ("decisions.md", "uv.lock")

# Where the existence check looks. Defaults to the running user's ~/repos (Michael's on netcup);
# set OCC_REPOS_ROOT when the suite runs as another user.
REPOS_ROOT = Path(os.environ.get("OCC_REPOS_ROOT", Path.home() / "repos"))


def _tracked_text_files():
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout
    for rel in out.split("\0"):
        if not rel or rel.startswith("tests/") or rel in NOT_SCANNED:
            continue
        path = REPO_ROOT / rel
        if path.is_symlink() or not path.is_file():
            continue  # CLAUDE.md is a symlink to AGENTS.md
        try:
            yield rel, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary asset (PNG banners)


def repo_path_refs(files):
    """Map each path under ~/repos named in `files` to the `file:line` places that name it.

    Args:
        files: Iterable of (relative file name, text) pairs.

    Returns:
        Dict of path relative to ~/repos (trailing `.` and `/` dropped) to a list of locations.
    """
    refs = {}
    for rel, text in files:
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in REPOS_PATH.finditer(line):
                path = match.group(1).rstrip("./")
                if path:
                    refs.setdefault(path, []).append(f"{rel}:{lineno}")
    return refs


def stale_paths(refs):
    """The entries of `refs` under a retired group or naming a repo's old path."""
    return {
        path: where for path, where in refs.items()
        if path.split("/")[0] in RETIRED_GROUPS or path in MOVED
    }


def outside_checkouts(refs, root):
    """The entries of `refs` that are missing under `root` or lie in no git checkout below it.

    A group folder (`talks/`, or a talk folder holding one repo per job) has no `.git`, so a
    path that resolves only because its repo moved down a level is reported too.
    """
    def in_checkout(path):
        parts = Path(path).parts
        return (root / path).exists() and any(
            (root.joinpath(*parts[:n]) / ".git").exists() for n in range(1, len(parts) + 1)
        )

    return {path: where for path, where in refs.items() if not in_checkout(path)}


def _report(paths):
    lines = []
    for path, where in sorted(paths.items()):
        hint = f" -> now ~/repos/{MOVED[path]}" if path in MOVED else ""
        lines.append(f"  ~/repos/{path}{hint}  ({', '.join(where)})")
    return "\n".join(lines)


def test_scanner_reads_every_spelling_and_drops_trailing_punctuation():
    refs = repo_path_refs(
        [
            ("a.md", "see `~/repos/talks/talks-knowledge`."),
            ("b.sh", 'cd "$HOME/repos/conferences/conference-knowledge/"'),
            ("c.yaml", "path: /home/michael/repos/mrf/MRF_Obsidian_Repo."),
            ("d.md", "~/repos/talks/talks-knowledge: talks/register.md"),
        ]
    )
    assert refs == {
        "talks/talks-knowledge": ["a.md:1", "d.md:1"],
        "conferences/conference-knowledge": ["b.sh:1"],
        "mrf/MRF_Obsidian_Repo": ["c.yaml:1"],
    }


def test_stale_paths_flags_retired_groups_and_moved_repos_only():
    refs = {
        "events/cfp": ["a.md:1"],
        "talks/reading-agent-mcp-calls-through-otel": ["b.md:2"],
        MOVED["talks/reading-agent-mcp-calls-through-otel"]: ["c.md:3"],
        "talks/talks-knowledge": ["d.md:4"],
    }
    assert stale_paths(refs) == {
        "events/cfp": ["a.md:1"],
        "talks/reading-agent-mcp-calls-through-otel": ["b.md:2"],
    }


def test_outside_checkouts_reports_missing_paths_and_bare_group_folders(tmp_path):
    (tmp_path / "talks" / "talks-knowledge" / ".git").mkdir(parents=True)
    (tmp_path / "talks" / "talks-knowledge" / "talks").mkdir()
    (tmp_path / "talks" / "toronto" / "toronto-talk" / ".git").mkdir(parents=True)
    refs = {
        "talks/talks-knowledge": ["a.md:1"],
        "talks/talks-knowledge/talks": ["a.md:2"],
        "talks/toronto/toronto-talk": ["b.md:1"],
        "talks/toronto": ["b.md:2"],
        "events/gone": ["c.md:1"],
    }
    assert outside_checkouts(refs, tmp_path) == {
        "talks/toronto": ["b.md:2"],
        "events/gone": ["c.md:1"],
    }


def test_scanner_finds_the_documented_sibling_paths():
    refs = repo_path_refs(_tracked_text_files())
    for path in (
        "conferences/conference-knowledge",
        "talks/talks-knowledge",
        "talks/reading-agent-mcp-calls-through-otel/reading-agent-mcp-calls-through-otel-talk",
    ):
        assert path in refs, (
            f"the ~/repos scanner no longer finds ~/repos/{path}, which AGENTS.md names; the "
            "checks below would pass without checking it"
        )


def test_no_documented_path_is_retired_or_moved():
    stale = stale_paths(repo_path_refs(_tracked_text_files()))
    assert not stale, (
        "Paths the ~/repos restructure retired or moved; resolve each with "
        "`repo-management whereis <term>`:\n" + _report(stale)
    )


@pytest.mark.integration
def test_every_documented_path_is_in_a_checkout():
    assert REPOS_ROOT.is_dir(), (
        f"{REPOS_ROOT} is not a readable directory, so no ~/repos path can be checked. Run as "
        "the user who owns the tree, or set OCC_REPOS_ROOT to it."
    )
    gone = outside_checkouts(repo_path_refs(_tracked_text_files()), REPOS_ROOT)
    assert not gone, (
        f"Paths under {REPOS_ROOT} that are missing or in no git checkout; resolve each with "
        "`repo-management whereis <term>`:\n" + _report(gone)
    )
