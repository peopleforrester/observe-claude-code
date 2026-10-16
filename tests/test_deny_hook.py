# ABOUTME: Runs the PreToolUse deny hook and checks the decision it hands back to Claude Code.
# ABOUTME: The hook's deny is what turns a deploy attempt into a visible tool_decision=reject event.
import json
import subprocess

from conftest import REPO_ROOT

DENY_HOOK = REPO_ROOT / ".claude" / "hooks" / "deny-prod-deploy.sh"

# Shape of the PreToolUse payload Claude Code pipes to the hook on stdin.
DEPLOY_CALL = {
    "hook_event_name": "PreToolUse",
    "tool_name": "mcp__prod-api__deploy",
    "tool_input": {"service": "checkout", "version": "2.0.0"},
}


def _run_hook():
    return subprocess.run(
        [str(DENY_HOOK)], input=json.dumps(DEPLOY_CALL),
        capture_output=True, text=True, timeout=10,
    )


def test_hook_exits_zero_so_its_json_decision_is_honoured():
    # A non-zero exit would be read as a hook error, not as the structured deny below.
    result = _run_hook()
    assert result.returncode == 0, result.stderr


def test_hook_returns_a_pretooluse_deny_with_a_reason():
    output = json.loads(_run_hook().stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"
    assert "deploy" in output["permissionDecisionReason"].lower()
