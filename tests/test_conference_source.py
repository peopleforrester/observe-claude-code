# ABOUTME: Guards that conference-knowledge stays the source of truth for conference information.
# ABOUTME: Fails if event dates, venue, CFP deadlines or submission status are copied back into this repo.
import re
import subprocess

import pytest

from conftest import REPO_ROOT

POINTER = "conference-knowledge"

# Conference facts that live in conference-knowledge, not here. Each pattern is matched
# case-insensitively against every tracked text file outside tests/.
COPIED_FACTS = {
    "event date": r"\boct(ober)?\b\.?\s*\d|\bbefore october\b|2026-10-2[23]",
    "venue": r"\bsan jose\b|\bmcenery\b",
    "CFP form URL": r"sessionize\.com",
    "CFP deadline or notification date": r"\bcfp closes\b|\bjun\.? 8\b|\bjul\.? (17|21)\b",
    "submission or booking status": (
        r"\bacceptance\b|\baccepted for\b|\bno booked venue\b"
        r"|\b(talk|submission|session|proposal)s? (was|were|is|are|has been|got) "
        r"(accepted|declined|rejected|waitlisted|booked)\b"
    ),
}

# Copies #7 and #22 removed, plus a status line conference-knowledge holds. Each must still
# trip a pattern, so the guard keeps biting.
REMOVED_COPIES = [
    "Conference demo for AGNTCon + MCPCon NA 2026 (Oct 22–23, San Jose)",
    "**Event:** AGNTCon + MCPCon North America 2026 (AAIF), San Jose McEnery Convention Center, Oct 22–23.",
    "**Submit via:** sessionize.com/agntcon-mcpcon-na-2026",
    "**CFP closes:** Sun Jun 7, 11:59 PM PDT = **Mon Jun 8, 1:59 AM Austin**. Notifications Jul 17. Schedule Jul 21.",
    "The talk has no booked venue at present; the demo stands on its own.",
    "## Pinned versions (verified 2026-06-15, re-verify week of Oct 2026)",
    "both moving; **re-verify the week of Oct 22, 2026** before the recording goes final.",
    "waiting to hear on **KubeCon NA acceptance first**. Michael has one talk",
    "attribute names can change before October.",
    "All five submissions were declined on 2026-07-20.",
]

# Docs whose copies #7 replaced; each must keep pointing at conference-knowledge.
POINTER_DOCS = ["AGENTS.md", "README.md", "PROJECT_STATE.md", "docs/abstract.md", "docs/spec.md"]


def _tracked_text_files():
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout
    for rel in out.split("\0"):
        if not rel or rel.startswith("tests/") or rel == "uv.lock":
            continue
        path = REPO_ROOT / rel
        if path.is_symlink() or not path.is_file():
            continue
        try:
            yield rel, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary asset (PNG banners)


def _matches(text):
    return [label for label, pattern in COPIED_FACTS.items() if re.search(pattern, text, re.I)]


@pytest.mark.parametrize("line", REMOVED_COPIES)
def test_patterns_catch_the_copies_issue_7_removed(line):
    assert _matches(line), f"no COPIED_FACTS pattern catches a line #7 removed: {line!r}"


def test_no_conference_facts_copied_into_repo():
    files = list(_tracked_text_files())
    assert any(rel == "AGENTS.md" for rel, _ in files), "git ls-files found no AGENTS.md"
    hits = []
    for rel, text in files:
        for lineno, line in enumerate(text.splitlines(), 1):
            for label in _matches(line):
                hits.append(f"{rel}:{lineno}: {label}: {line.strip()[:120]}")
    assert not hits, (
        "Conference facts copied into this repo; replace them with a pointer to "
        "conference-knowledge (events/cfp_pipeline.yaml, events/registry.yaml):\n"
        + "\n".join(hits)
    )


def test_agents_md_says_where_conference_information_lives():
    text = (REPO_ROOT / "AGENTS.md").read_text()
    section = re.search(r"^## Where things live\n(.*?)(?=^## )", text, re.M | re.S)
    assert section, "AGENTS.md lost its 'Where things live' section"
    body = section.group(1)
    for expected in (
        "~/repos/conferences/conference-knowledge",
        "events/cfp_pipeline.yaml",
        "events/registry.yaml",
        "peopleforrester/conference-knowledge",
    ):
        assert expected in body, f"AGENTS.md 'Where things live' no longer names {expected}"


def test_claude_md_carries_the_same_pointer():
    assert (REPO_ROOT / "CLAUDE.md").read_text() == (REPO_ROOT / "AGENTS.md").read_text()


@pytest.mark.parametrize("rel", POINTER_DOCS)
def test_doc_points_at_conference_knowledge(rel):
    assert POINTER in (REPO_ROOT / rel).read_text(), f"{rel} no longer points at {POINTER}"
