# ABOUTME: Validates the project MCP registration and the PreToolUse hook that denies deploy.
# ABOUTME: deploy must be advertised (allow-listed) so the hook can reject it at the call —
# ABOUTME: a plain deny rule withholds the tool entirely and emits no tool_decision event.
import json
import os

from conftest import REPO_ROOT

MCP_JSON = REPO_ROOT / ".mcp.json"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
DENY_HOOK = REPO_ROOT / ".claude" / "hooks" / "deny-prod-deploy.sh"


def test_mcp_json_registers_prod_api_stdio_server():
    cfg = json.loads(MCP_JSON.read_text())
    server = cfg["mcpServers"]["prod-api"]
    assert server["command"], "prod-api server has no command"
    assert any("server.py" in arg for arg in server["args"]), "args do not reference server.py"


def test_both_tools_are_advertised():
    allow = json.loads(SETTINGS.read_text())["permissions"]["allow"]
    # deploy must be allowed/advertised so the hook can reject it at call time (visible denial).
    assert "mcp__prod-api__get_status" in allow
    assert "mcp__prod-api__deploy" in allow


def test_deploy_is_denied_by_a_pretooluse_hook():
    hooks = json.loads(SETTINGS.read_text())["hooks"]["PreToolUse"]
    matchers = [h.get("matcher", "") for h in hooks]
    assert any("deploy" in m for m in matchers), "no PreToolUse hook matches deploy"
    assert DENY_HOOK.exists(), "deny hook script missing"
    assert os.access(DENY_HOOK, os.X_OK), "deny hook script is not executable"
