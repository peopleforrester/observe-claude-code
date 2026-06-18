# ABOUTME: Unit tests for the prod-api FastMCP server's two tools.
# ABOUTME: v3 @mcp.tool returns the original callable, so the tool functions are tested directly.
import importlib.util

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
