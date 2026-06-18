# ABOUTME: Validates the project MCP registration and the permission policy that denies deploy.
# ABOUTME: The deny rule is what produces the tool_decision=reject event on stage.
import json

from conftest import REPO_ROOT

MCP_JSON = REPO_ROOT / ".mcp.json"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def test_mcp_json_registers_prod_api_stdio_server():
    cfg = json.loads(MCP_JSON.read_text())
    server = cfg["mcpServers"]["prod-api"]
    assert server["command"], "prod-api server has no command"
    assert any("server.py" in arg for arg in server["args"]), "args do not reference server.py"


def test_settings_denies_deploy_and_allows_read():
    perms = json.loads(SETTINGS.read_text())["permissions"]
    assert "mcp__prod-api__deploy" in perms["deny"], "deploy is not denied"
    assert "mcp__prod-api__get_status" in perms["allow"], "get_status is not allowed"
