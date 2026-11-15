# ABOUTME: Offline tests for capture-session.sh. It must save the session transcript beside the OTLP.
# ABOUTME: Runs the real script in a scratch copy of the repo with docker, sleep and claude stubbed.
import json
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

from conftest import REPO_ROOT

SCRIPTED_PROMPT = (REPO_ROOT / "demo/session-prompt.txt").read_text().strip()

# The files capture-session.sh touches, copied into a scratch repo so nothing lands in this one.
SCRIPT_FILES = [
    "demo/replay/capture-session.sh",
    "demo/replay/join.py",
    "demo/run-session.sh",
    "demo/session-prompt.txt",
    "env/claude-code.env",
]

# Stands in for `claude -p`: logs its argv, writes the session transcript where Claude Code
# would, and writes the OTLP the Collector's file exporter would have captured. Like a real
# scripted run it makes four tool calls under the prompt it was given; the PreToolUse hook denies
# the last one, the prod-api deploy, which still gets its own claude_code.tool span.
FAKE_CLAUDE = textwrap.dedent("""\
    import json, os, pathlib, sys
    argv = sys.argv[1:]
    pathlib.Path(os.environ["FAKE_CLAUDE_ARGV"]).write_text(json.dumps(argv))
    mode = os.environ.get("FAKE_CLAUDE_MODE", "ok")
    sid = argv[argv.index("--session-id") + 1]
    prompt = argv[argv.index("-p") + 1]
    span_sid = "33333333-3333-4333-8333-333333333333" if mode == "wrong-session" else sid
    calls = [("toolu_edit", "Edit"), ("toolu_bash", "Bash"),
             ("toolu_status", "mcp__prod-api__get_status"),
             ("toolu_deploy", "mcp__prod-api__deploy")]
    spans = []
    for i, (tool_use_id, tool_name) in enumerate(calls):
        if mode == "deploy-no-span" and tool_name == "mcp__prod-api__deploy":
            continue
        attrs = [{"key": k, "value": {"stringValue": v}} for k, v in
                 {"session.id": span_sid, "tool_name": tool_name,
                  "tool_use_id": tool_use_id}.items()]
        spans.append({"traceId": "ab" * 16, "spanId": f"{i + 1:016x}", "name": "claude_code.tool",
                      "startTimeUnixNano": "1", "endTimeUnixNano": "2", "attributes": attrs})
    raw = pathlib.Path("demo/replay/raw")
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "otlp-capture.jsonl").write_text(
        json.dumps({"resourceSpans": [{"scopeSpans": [{"spans": spans}]}]}) + "\\n")
    if mode == "no-transcript":
        sys.exit(0)
    project = pathlib.Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / "-scratch-repo"
    project.mkdir(parents=True, exist_ok=True)

    def entry(kind, uuid, parent, content):
        role = "assistant" if kind == "assistant" else "user"
        return {"type": kind, "uuid": uuid, "parentUuid": parent, "sessionId": sid,
                "message": {"role": role, "content": content}}

    entries = [entry("user", "p1", None, prompt)]
    parent = "p1"
    for n, (tool_use_id, tool_name) in enumerate(calls, start=1):
        if mode == "deploy-other-prompt" and tool_name == "mcp__prod-api__deploy":
            entries.append(entry("user", "p2", parent, "a prompt the script never sent"))
            parent = "p2"
        entries.append(entry("assistant", f"a{n}", parent,
                             [{"type": "tool_use", "id": tool_use_id, "name": tool_name}]))
        denied = tool_name == "mcp__prod-api__deploy"
        result = {"type": "tool_result", "tool_use_id": tool_use_id, "is_error": denied,
                  "content": ("Production deploys are blocked by policy in this demo."
                              if denied else "ok")}
        entries.append(entry("user", f"r{n}", f"a{n}", [result]))
        parent = f"r{n}"
    (project / f"{sid}.jsonl").write_text("\\n".join(json.dumps(e) for e in entries) + "\\n")
    if mode == "session-fails":
        # A real logged-out `claude -p` still exports OTLP and writes its transcript, then exits 1.
        print("Not logged in · Please run /login")
        sys.exit(1)
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
    # Logs each call with the Collector user it was given, so a test can read what was recreated.
    _stub(bin_dir, "docker",
          '#!/bin/sh\necho "OCC_UID=${OCC_UID:-} OCC_GID=${OCC_GID:-} $*" >>"$FAKE_DOCKER_LOG"\n')
    _stub(bin_dir, "sleep", "#!/bin/sh\nexit 0\n")
    _stub(bin_dir, "claude", f"#!{sys.executable}\n{FAKE_CLAUDE}")
    (bin_dir / "python3").symlink_to(sys.executable)

    config = tmp_path / "claude-config"
    # The scripted session exports OCC_SESSION_ID, and a test run inside one (a Stop hook) must
    # not hand it to run-session.sh, nor a caller's Collector user to capture-session.sh.
    inherited = {k: v for k, v in os.environ.items()
                 if k not in {"OCC_SESSION_ID", "OCC_UID", "OCC_GID"}}
    env = {
        **inherited,
        "FAKE_DOCKER_LOG": str(tmp_path / "docker.log"),
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

    assert "-> prompt p1" in result.stdout and SCRIPTED_PROMPT.splitlines()[0] in result.stdout, (
        "the capture should end by showing the trace joining back to its prompt"
    )


def test_capture_joins_the_hook_denied_deploy_span_to_the_scripted_prompt(scratch):
    """The denied deploy's claude_code.tool span joins back to the prompt run-session.sh sent (#38)."""
    repo, env, argv_file = scratch
    result = _run(repo, env)
    assert result.returncode == 0, result.stderr + result.stdout

    argv = json.loads(argv_file.read_text())
    assert argv[argv.index("-p") + 1] == SCRIPTED_PROMPT, "the session must run the scripted prompt"
    deploy = [ln for ln in result.stdout.splitlines() if "mcp__prod-api__deploy" in ln]
    assert len(deploy) == 1 and "toolu_deploy" in deploy[0], result.stdout
    assert deploy[0].rstrip().endswith("-> prompt p1"), deploy[0]
    printed = result.stdout.split("  prompt p1:\n", 1)[1]
    assert all(f"    {ln}" in printed for ln in SCRIPTED_PROMPT.splitlines()), (
        "p1, the prompt the deploy joins to, must be the scripted prompt"
    )


def test_capture_fails_loudly_when_the_denied_deploy_has_no_tool_span(scratch):
    repo, env, _ = scratch
    result = _run(repo, env, FAKE_CLAUDE_MODE="deploy-no-span")
    assert result.returncode != 0
    assert "no claude_code.tool span for mcp__prod-api__deploy" in result.stderr, result.stderr


def test_capture_fails_loudly_when_the_deploy_joins_to_another_prompt(scratch):
    repo, env, _ = scratch
    result = _run(repo, env, FAKE_CLAUDE_MODE="deploy-other-prompt")
    assert result.returncode != 0
    assert "mcp__prod-api__deploy span" in result.stderr, result.stderr
    assert "joins to prompt p2, not the scripted prompt" in result.stderr, result.stderr


def test_run_session_keeps_its_flags_and_adds_the_pinned_session_id(scratch):
    repo, env, argv_file = scratch
    assert _run(repo, env).returncode == 0
    argv = json.loads(argv_file.read_text())
    assert argv[0] == "-p"
    assert "--strict-mcp-config" in argv and "--allowedTools" in argv
    sid = argv[argv.index("--session-id") + 1]
    assert len(sid) == 36 and sid.count("-") == 4, f"not a UUID: {sid}"


def test_capture_recreates_the_collector_as_the_checkout_owner(scratch):
    """The Collector writes into this checkout's demo/replay/raw, so it must run as its owner.

    The image's own user (10001) cannot write a directory the checkout owner owns, and a restart
    would keep that user, so no OTLP was ever captured on netcup (#24).
    """
    repo, env, _ = scratch
    assert _run(repo, env).returncode == 0
    calls = (repo.parent / "docker.log").read_text().splitlines()
    recreate = [c for c in calls if " up " in f" {c} " and "collector" in c.split()]
    assert recreate, f"the Collector was not recreated: {calls}"
    assert recreate[0].startswith(f"OCC_UID={os.getuid()} OCC_GID={os.getgid()} "), recreate[0]
    assert "--force-recreate" in recreate[0].split(), "a plain `up` keeps a running container"
    assert not any(" restart " in f" {c} " for c in calls), "a restart keeps the old user"


def test_run_session_keeps_user_settings_out_and_closes_stdin(scratch):
    """A user-level Stop hook must not run inside the scripted session; stdin is closed."""
    repo, env, argv_file = scratch
    stub = repo.parent / "bin" / "claude"
    stub.write_text(f"#!{sys.executable}\nimport json, os, sys\n"
                    "open(os.environ['FAKE_CLAUDE_ARGV'], 'w').write(json.dumps(\n"
                    "    {'argv': sys.argv[1:], 'stdin': sys.stdin.read()}))\n")
    result = subprocess.run(["bash", str(repo / "demo/run-session.sh")],
                            env=env, input="piped text", capture_output=True, text=True,
                            timeout=60)
    assert result.returncode == 0, result.stderr
    seen = json.loads(argv_file.read_text())
    argv = seen["argv"]
    assert argv[argv.index("--setting-sources") + 1] == "project,local"
    assert seen["stdin"] == "", "claude -p should get no stdin"


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


def test_capture_fails_loudly_with_the_session_output_when_the_session_fails(scratch):
    repo, env, _ = scratch
    result = _run(repo, env, FAKE_CLAUDE_MODE="session-fails")
    assert result.returncode != 0
    assert "the scripted session failed" in result.stderr
    assert "Not logged in" in result.stderr, "the session's own error should be shown"
    logs = list((repo / "demo/replay/raw").glob("session-*.log"))
    assert len(logs) == 1 and "Not logged in" in logs[0].read_text()
    assert _snapshots(repo) == ([], []), "a failed session leaves no capture pair to replay"


def _git(cwd, *args):
    # A caller's GIT_DIR or GIT_INDEX_FILE (a git hook) must not point these at another repo.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        ["git", "-c", "user.name=capture-test", "-c", "user.email=capture-test@invalid", *args],
        cwd=cwd, env=env, check=True, capture_output=True, text=True,
    ).stdout


def test_capture_pair_stays_in_the_gitignored_raw_dir_and_nothing_is_staged(scratch):
    """A capture adds nothing `git add -A` would commit: the pair and its log are ignored (#24).

    The scratch repo is committed with this repo's real .gitignore first, so any file the capture
    writes that the ignore rules miss, in demo/replay/raw or anywhere else, shows up as staged.
    """
    repo, env, _ = scratch
    shutil.copy2(REPO_ROOT / ".gitignore", repo / ".gitignore")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "scratch")

    result = _run(repo, env)
    assert result.returncode == 0, result.stderr + result.stdout

    captures, transcripts = _snapshots(repo)
    assert len(captures) == 1 and len(transcripts) == 1, "the capture wrote no pair to check"
    written = sorted(p for p in (repo / "demo/replay/raw").iterdir())
    rels = [str(p.relative_to(repo)) for p in written]
    for pair_file in (captures[0], transcripts[0]):
        assert str(pair_file.relative_to(repo)) in rels

    ignored = _git(repo, "check-ignore", "--no-index", *rels).splitlines()
    assert sorted(ignored) == sorted(rels), (
        f"capture files not ignored by .gitignore: {sorted(set(rels) - set(ignored))}"
    )

    _git(repo, "add", "-A")
    staged = _git(repo, "diff", "--cached", "--name-only").splitlines()
    assert staged == [], f"a capture left files `git add -A` would commit: {staged}"


def test_this_repo_tracks_nothing_under_demo_replay_raw():
    """No capture or transcript was ever committed: real ones carry account ids and prompt text."""
    tracked = _git(REPO_ROOT, "ls-files", "--", "demo/replay/raw").splitlines()
    assert tracked == [], f"files under demo/replay/raw are committed: {tracked}"
    probe = "demo/replay/raw/session-20260101-000000.transcript.jsonl"
    assert _git(REPO_ROOT, "check-ignore", "--no-index", probe).strip() == probe, (
        "this repo's .gitignore no longer ignores demo/replay/raw/"
    )


def test_run_session_without_a_pinned_id_passes_no_session_flag(scratch):
    repo, env, argv_file = scratch
    stub = repo.parent / "bin" / "claude"
    stub.write_text(f"#!{sys.executable}\nimport json, os, sys\n"
                    "open(os.environ['FAKE_CLAUDE_ARGV'], 'w').write(json.dumps(sys.argv[1:]))\n")
    result = subprocess.run(["bash", str(repo / "demo/run-session.sh")],
                            env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert "--session-id" not in json.loads(argv_file.read_text())
