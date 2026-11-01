# ABOUTME: Guards every ~/repos path this repo names: none sits under a retired group, and each
# ABOUTME: one exists on disk (#4). A dead path in AGENTS.md still reads as authoritative.
import os
import re
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT

# The three spellings the 2026-09-20/21 restructure recheck (#4) searched for.
REPOS_PATH = re.compile(r"(?:~|\$HOME|/home/michael)/repos/([A-Za-z0-9_./-]+)")

# Groups the restructure removed outright. `events/` split across talks/, conferences/,
# agenticburn/ and clients/; a path under it can never resolve again.
RETIRED_GROUPS = {"events"}

# Where the existence check looks. Defaults to the running user's ~/repos (Michael's on the VPS);
# set OCC_REPOS_ROOT when the suite runs as another user.
REPOS_ROOT = Path(os.environ.get("OCC_REPOS_ROOT", Path.home() / "repos"))


def _tracked_text_files():
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout
    for rel in out.split("\0"):
        # tests/ is left out: its paths are fixtures or assertions on the docs scanned here.
        if not rel or rel.startswith("tests/") or rel == "uv.lock":
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


def missing_paths(refs, root):
    """The entries of `refs` whose path does not exist under `root`."""
    return {path: where for path, where in refs.items() if not (root / path).exists()}


def _report(paths):
    return "\n".join(f"  ~/repos/{path}  ({', '.join(where)})" for path, where in sorted(paths.items()))


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


def test_missing_paths_reports_only_what_is_absent(tmp_path):
    (tmp_path / "talks" / "talks-knowledge").mkdir(parents=True)
    refs = {"talks/talks-knowledge": ["a.md:1"], "events/gone": ["b.md:2"]}
    assert missing_paths(refs, tmp_path) == {"events/gone": ["b.md:2"]}


def test_scanner_finds_the_documented_sibling_paths():
    refs = repo_path_refs(_tracked_text_files())
    assert "conferences/conference-knowledge" in refs, (
        "the ~/repos scanner no longer finds the conference-knowledge path AGENTS.md names; "
        "the existence check below would pass without checking anything"
    )


def test_no_path_under_a_retired_group():
    refs = repo_path_refs(_tracked_text_files())
    retired = {path: where for path, where in refs.items() if path.split("/")[0] in RETIRED_GROUPS}
    assert not retired, (
        "Paths under a group the ~/repos restructure retired; resolve each with "
        "`repo-management whereis <term>`:\n" + _report(retired)
    )


@pytest.mark.integration
def test_every_repos_path_exists():
    if not REPOS_ROOT.is_dir():
        pytest.fail(
            f"{REPOS_ROOT} is not a readable directory, so no ~/repos path can be checked. Run as "
            "the user who owns the tree, or set OCC_REPOS_ROOT to it."
        )
    gone = missing_paths(repo_path_refs(_tracked_text_files()), REPOS_ROOT)
    assert not gone, (
        f"Paths under {REPOS_ROOT} that no longer exist; resolve each with "
        "`repo-management whereis <term>`:\n" + _report(gone)
    )
