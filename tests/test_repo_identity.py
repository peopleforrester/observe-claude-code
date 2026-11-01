# ABOUTME: Checks the talk-repo identity files: README says who this repo is, AGENTS.md points at
# ABOUTME: talks-knowledge and conference-knowledge, and the state and decision files exist.
from conftest import REPO_ROOT

README = REPO_ROOT / "README.md"
AGENTS = REPO_ROOT / "AGENTS.md"
CLAUDE = REPO_ROOT / "CLAUDE.md"
TITLE = "What Does a Good Agent Look Like? Observing Claude Code in Production With OpenTelemetry"
SIBLING = "reading-agent-mcp-calls-through-otel"


def _section(text, heading):
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def test_readme_says_who_this_talk_is():
    talk = _section(README.read_text(), "## This talk")
    for row in ("Title", "Speakers", "Argument", "Event", "Status", "Built from", "Registered in"):
        assert f"| {row} |" in talk, f"README 'This talk' table lacks a {row} row"
    assert TITLE in talk
    assert "Michael Rishi Forrester" in talk


def test_readme_points_at_the_knowledge_repos_and_the_sibling():
    talk = _section(README.read_text(), "## This talk")
    assert "talks-knowledge" in talk and "talks/register.md" in talk
    assert "conference-knowledge" in talk
    assert SIBLING in talk


def test_claude_md_is_a_symlink_to_agents_md():
    assert CLAUDE.is_symlink()
    assert CLAUDE.resolve() == AGENTS.resolve()


def test_agents_md_says_where_things_live():
    where = _section(AGENTS.read_text(), "## Where things live")
    assert "talks-knowledge" in where and "talks/register.md" in where
    assert "conference-knowledge" in where
    assert SIBLING in where
    assert "decisions.md" in where


def test_project_state_and_decisions_exist():
    assert (REPO_ROOT / "PROJECT_STATE.md").is_file()
    decisions = (REPO_ROOT / "decisions.md").read_text()
    assert "Append-only" in decisions
