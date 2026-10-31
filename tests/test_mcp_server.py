# ABOUTME: Unit tests for the prod-api FastMCP server's two tools.
# ABOUTME: v3 @mcp.tool returns the original callable, so the tool functions are tested directly.
import importlib.util
import json
import select
import subprocess
import sys

from conftest import REPO_ROOT

SERVER_PATH = REPO_ROOT / "demo" / "prod-api" / "server.py"


def _load_server():
    spec = importlib.util.spec_from_file_location("prod_api_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_server_is_named_prod_api():
    assert _load_server().mcp.name == "prod-api"


def test_get_status_is_read_only_and_reports_status():
    result = _load_server().get_status("checkout")
    assert result["service"] == "checkout"
    assert result["status"] == "healthy"
    assert result["environment"] == "production"


def test_deploy_returns_a_production_deployment_result():
    result = _load_server().deploy("checkout", "2.0.0")
    assert result["deployed_version"] == "2.0.0"
    assert result["environment"] == "production"
    assert result["result"] == "deployment triggered"


# FastMCP 4 is built on the 2026-07-28 MCP revision but negotiates per connection; the server must
# keep answering a pre-2026 stdio handshake like the one Claude Code's MCP client sends.
LEGACY_PROTOCOL = "2025-06-18"


def _stdio_session(requests):
    """Speak JSON-RPC to the server over stdio, one request at a time, and return the replies."""
    proc = subprocess.Popen(
        [sys.executable, str(SERVER_PATH)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    replies = []
    try:
        for message in requests:
            proc.stdin.write(json.dumps(message) + "\n")
            proc.stdin.flush()
            if "id" not in message:
                continue  # notifications get no reply
            ready, _, _ = select.select([proc.stdout], [], [], 30)
            assert ready, f"no reply to {message['method']} within 30s"
            replies.append(json.loads(proc.stdout.readline()))
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)
    return replies


def test_server_answers_a_pre_2026_protocol_handshake_over_stdio():
    init, tools, call = _stdio_session([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": LEGACY_PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "claude-code", "version": "test"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "get_status", "arguments": {"service": "checkout"}}},
    ])
    assert init["result"]["protocolVersion"] == LEGACY_PROTOCOL
    assert init["result"]["serverInfo"]["name"] == "prod-api"
    assert {t["name"] for t in tools["result"]["tools"]} == {"get_status", "deploy"}
    assert call["result"]["structuredContent"]["status"] == "healthy"
