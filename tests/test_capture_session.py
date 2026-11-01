# ABOUTME: Offline tests for capture-session.sh — it must save the session transcript beside the OTLP.
# ABOUTME: Runs the real script in a scratch copy of the repo with docker, sleep and claude stubbed.
import json
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

from conftest import REPO_ROOT

# The files capture-session.sh touches, copied into a scratch repo so nothing lands in this one.
SCRIPT_FILES = [
    "demo/replay/capture-session.sh",
    "demo/replay/join.py",
    "demo/run-session.sh",
    "env/claude-code.env",
]

# Stands in for `claude -p`: logs its argv, writes the session transcript where Claude Code
# would, and writes the OTLP the Collector's file exporter would have captured.
FAKE_CLAUDE = textwrap.dedent("""\
    import json, os, pathlib, sys
    argv = sys.argv[1:]
    pathlib.Path(os.environ["FAKE_CLAUDE_ARGV"]).write_text(json.dumps(argv))
    mode = os.environ.get("FAKE_CLAUDE_MODE", "ok")
    sid = argv[argv.index("--session-id") + 1]
    span_sid = "33333333-3333-4333-8333-333333333333" if mode == "wrong-session" else sid
    raw = pathlib.Path("demo/replay/raw")
    raw.mkdir(parents=True, exist_ok=True)
    attrs = [{"key": k, "value": {"stringValue": v}} for k, v in
             {"session.id": span_sid, "tool_name": "Edit", "tool_use_id": "toolu_cap"}.items()]
    span = {"traceId": "ab" * 16, "spanId": "cd" * 8, "name": "claude_code.tool",
            "startTimeUnixNano": "1", "endTimeUnixNano": "2", "attributes": attrs}
    (raw / "otlp-capture.jsonl").write_text(
        json.dumps({"resourceSpans": [{"scopeSpans": [{"spans": [span]}]}]}) + "\\n")
    if mode == "no-transcript":
        sys.exit(0)
    project = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / "-scratch-repo"
    project.mkdir(parents=True, exist_ok=True)
    entries = [
        {"type": "user", "uuid": "p1", "parentUuid": None, "sessionId": sid,
         "message": {"role": "user", "content": "captured prompt"}},
        {"type": "assistant", "uuid": "a1", "parentUuid": "p1", "sessionId": sid,
         "message": {"role": "assistant",
                     "content": [{"type": "tool_use", "id": "toolu_cap", "name": "Edit"}]}},
    ]
    (project / f"{sid}.jsonl").write_text("\\n".join(json.dumps(e) for e in entries) + "\\n")
""")


def _stub(bin_dir, name, body):
    path = bin_dir / name
    path.write_text(body)
    path.chmod(0o755)


@pytest.fixture
def scratch(tmp_path):
    """A scratch repo holding the capture scripts, plus a PATH of stubs and a Claude config dir."""
    repo = tmp_path / "repo"
    for rel in SCRIPT_FILES:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel, repo / rel)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(bin_dir, "docker", "#!/bin/sh\nexit 0\n")
    _stub(bin_dir, "sleep", "#!/bin/sh\nexit 0\n")
    _stub(bin_dir, "claude", f"#!{sys.executable}\n{FAKE_CLAUDE}")
    (bin_dir / "python3").symlink_to(sys.executable)

    config = tmp_path / "claude-config"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "CLAUDE_CONFIG_DIR": str(config),
        "FAKE_CLAUDE_ARGV": str(tmp_path / "claude-argv.json"),
    }
    return repo, env, tmp_path / "claude-argv.json"


def _run(repo, env, **extra):
    return subprocess.run(
        ["bash", str(repo / "demo/replay/capture-session.sh")],
        env={**env, **extra}, capture_output=True, text=True, timeout=60,
    )


def _snapshots(repo):
    raw = repo / "demo/replay/raw"
    captures = sorted(p for p in raw.glob("session-*.jsonl") if ".transcript." not in p.name)
    transcripts = sorted(raw.glob("session-*.transcript.jsonl"))
    return captures, transcripts


def test_capture_saves_the_session_transcript_beside_the_otlp_snapshot(scratch):
    repo, env, argv_file = scratch
    result = _run(repo, env)
    assert result.returncode == 0, result.stderr + result.stdout

    captures, transcripts = _snapshots(repo)
    assert len(captures) == 1 and len(transcripts) == 1
    assert transcripts[0].name == captures[0].name.replace(".jsonl", ".transcript.jsonl"), (
        "the transcript must be named after its capture so join.py pairs them"
    )

    sid = json.loads(argv_file.read_text())
    sid = sid[sid.index("--session-id") + 1]
    entries = [json.loads(ln) for ln in transcripts[0].read_text().splitlines()]
    assert {e["sessionId"] for e in entries} == {sid}, "the copied transcript is the pinned session's"

    assert "-> prompt p1" in result.stdout and "captured prompt" in result.stdout, (
        "the capture should end by showing the trace joining back to its prompt"
    )


def test_run_session_keeps_its_flags_and_adds_the_pinned_session_id(scratch):
    repo, env, argv_file = scratch
    assert _run(repo, env).returncode == 0
    argv = json.loads(argv_file.read_text())
    assert argv[0] == "-p"
    assert "--strict-mcp-config" in argv and "--allowedTools" in argv
    sid = argv[argv.index("--session-id") + 1]
    assert len(sid) == 36 and sid.count("-") == 4, f"not a UUID: {sid}"


def test_capture_fails_loudly_when_no_transcript_was_written(scratch):
    repo, env, _ = scratch
    result = _run(repo, env, FAKE_CLAUDE_MODE="no-transcript")
    assert result.returncode != 0
    assert "no transcript for session" in result.stderr
    captures, transcripts = _snapshots(repo)
    assert len(captures) == 1 and transcripts == []


def test_capture_fails_loudly_when_otlp_and_transcript_disagree_on_session(scratch):
    repo, env, _ = scratch
    result = _run(repo, env, FAKE_CLAUDE_MODE="wrong-session")
    assert result.returncode != 0
    assert "is not the transcript's sessionId" in result.stderr


def test_run_session_without_a_pinned_id_passes_no_session_flag(scratch):
    repo, env, argv_file = scratch
    stub = repo.parent / "bin" / "claude"
    stub.write_text(f"#!{sys.executable}\nimport json, os, sys\n"
                    "open(os.environ['FAKE_CLAUDE_ARGV'], 'w').write(json.dumps(sys.argv[1:]))\n")
    result = subprocess.run(["bash", str(repo / "demo/run-session.sh")],
                            env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert "--session-id" not in json.loads(argv_file.read_text())
