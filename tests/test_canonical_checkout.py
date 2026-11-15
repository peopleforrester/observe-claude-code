# ABOUTME: Checks the canonical netcup checkout is on staging at or after f1462b1, and that
# ABOUTME: capture-session.sh runs there against the live Collector to the end (#24, #37).
import os
import subprocess
from pathlib import Path

import pytest

from conftest import COMPOSE_BASE, MOVED_HOST_PORTS

pytestmark = pytest.mark.integration

# The checkout the talk is demoed from. OCC_CANONICAL_CHECKOUT points elsewhere for another host.
CANONICAL_CHECKOUT = Path(os.environ.get(
    "OCC_CANONICAL_CHECKOUT", "~/repos/talks/Value_with_Agents_Observability_in_action",
)).expanduser()
# The commit that made capture-session.sh save the transcript beside the OTLP (#16).
TRANSCRIPT_CAPTURE_COMMIT = "f1462b1"
# A real `claude -p` session plus the script's own waits; minutes, not seconds.
CAPTURE_TIMEOUT = float(os.environ.get("OCC_CAPTURE_TIMEOUT", "1200"))


@pytest.fixture(scope="module")
def canonical():
    """The canonical checkout, failing loudly when this host or user does not have it."""
    assert (CANONICAL_CHECKOUT / ".git").exists(), (
        f"no git checkout at {CANONICAL_CHECKOUT}: run this on netcup as the checkout's owner, "
        "or point OCC_CANONICAL_CHECKOUT at the canonical checkout"
    )
    return CANONICAL_CHECKOUT


def _git(checkout, *args):
    # safe.directory lets a run as another user read the checkout instead of refusing it.
    return subprocess.run(
        ["git", "-c", f"safe.directory={checkout}", "-C", str(checkout), *args],
        capture_output=True, text=True, timeout=60,
    )


def _collector_running(checkout):
    ps = subprocess.run([*COMPOSE_BASE, "ps", "--status", "running", "-q", "collector"],
                        cwd=checkout, capture_output=True, text=True, timeout=120)
    assert ps.returncode == 0, f"`docker compose ps` failed in {checkout}:\n{ps.stderr}"
    return bool(ps.stdout.strip())


def _capture_pairs(checkout):
    raw = checkout / "demo/replay/raw"
    return {p.name for p in raw.glob("session-*.jsonl")}


def test_canonical_checkout_is_on_staging_at_or_after_f1462b1(canonical):
    branch = _git(canonical, "symbolic-ref", "--short", "HEAD")
    assert branch.returncode == 0, f"{canonical} has a detached HEAD: {branch.stderr}"
    assert branch.stdout.strip() == "staging", (
        f"{canonical} is on {branch.stdout.strip()!r}, not staging"
    )

    known = _git(canonical, "cat-file", "-e", f"{TRANSCRIPT_CAPTURE_COMMIT}^{{commit}}")
    assert known.returncode == 0, (
        f"{canonical} does not have {TRANSCRIPT_CAPTURE_COMMIT}; fetch and fast-forward staging"
    )
    ancestor = _git(canonical, "merge-base", "--is-ancestor", TRANSCRIPT_CAPTURE_COMMIT, "HEAD")
    head = _git(canonical, "rev-parse", "--short", "HEAD").stdout.strip()
    assert ancestor.returncode == 0, (
        f"{canonical} staging is at {head}, before {TRANSCRIPT_CAPTURE_COMMIT}; fast-forward it"
    )


def test_capture_session_runs_to_the_end_against_the_live_collector(canonical):
    """Runs the real capture-session.sh in the canonical checkout: a real session, real OTLP.

    The script recreates the live Collector as the checkout owner, runs the scripted session,
    and joins every captured tool span back to its prompt; it exits non-zero at any step that
    fails. The capture pair it writes is gitignored and stays in the checkout, as a manual run's.
    """
    assert _collector_running(canonical), (
        f"the Collector of the stack in {canonical} is not running; bring the stack up (make up)"
    )
    before = _capture_pairs(canonical)

    # The script must reach the stack as it is published: a host port this run moved for a stack
    # of its own, a Collector user, or a pinned session id from the caller are not the demo's.
    dropped = {"OCC_SESSION_ID", "OCC_UID", "OCC_GID", *MOVED_HOST_PORTS}
    env = {k: v for k, v in os.environ.items() if k not in dropped}
    result = subprocess.run(
        ["bash", "demo/replay/capture-session.sh"], cwd=canonical, env=env,
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=CAPTURE_TIMEOUT,
    )
    output = f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert result.returncode == 0, f"capture-session.sh failed in {canonical}\n{output}"
    assert result.stdout.rstrip().endswith("Do NOT commit it."), (
        f"capture-session.sh did not reach its last line\n{output}"
    )
    assert "-> prompt " in result.stdout, f"no tool span was joined to a prompt\n{output}"

    new = _capture_pairs(canonical) - before
    captures = [n for n in new if ".transcript." not in n]
    assert len(captures) == 1, f"expected one new OTLP capture, got {sorted(new)}"
    transcript = captures[0].replace(".jsonl", ".transcript.jsonl")
    assert transcript in new, f"the capture {captures[0]} has no transcript beside it"
    raw = canonical / "demo/replay/raw"
    assert (raw / captures[0]).stat().st_size > 0 and (raw / transcript).stat().st_size > 0

    assert _collector_running(canonical), "the Collector is not running after the capture"
