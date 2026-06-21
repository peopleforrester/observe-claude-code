# ABOUTME: Validates the custom OTel Weaver semconv registry for the agent's telemetry.
# ABOUTME: A fast YAML structure check plus the authoritative `weaver registry check`.
import subprocess

import yaml

from conftest import REPO_ROOT

WEAVER_IMAGE = "otel/weaver:v0.23.0"
REGISTRY_DIR = REPO_ROOT / "weaver" / "registry"


def test_registry_defines_core_agent_attributes():
    groups = yaml.safe_load((REGISTRY_DIR / "claude_code.yaml").read_text())["groups"]
    attrs = {a["id"] for g in groups for a in g.get("attributes", [])}
    for expected in ("claude_code.tool.decision", "claude_code.mcp.tool_name",
                     "claude_code.mcp.server_name"):
        assert expected in attrs, f"registry missing {expected}"

    # the decision enum must carry accept and reject (the security-pane signal).
    decision = next(
        a for g in groups for a in g.get("attributes", [])
        if a["id"] == "claude_code.tool.decision"
    )
    members = {m["value"] for m in decision["type"]["members"]}
    assert {"accept", "reject"} <= members


def test_live_check_feeder_has_required_settings():
    # These two settings are load-bearing for live-check and easy to lose:
    # start_at:beginning (else the file's existing content is ignored) and
    # compression:none (weaver's OTLP receiver rejects gzip).
    feeder = yaml.safe_load((REPO_ROOT / "weaver" / "feeder.yaml").read_text())
    receiver = feeder["receivers"]["otlpjsonfile"]
    assert receiver.get("start_at") == "beginning"
    exporter = feeder["exporters"]["otlp/weaver"]
    assert exporter.get("compression") == "none"


def test_weaver_registry_check_passes():
    result = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{REGISTRY_DIR}:/registry",
         WEAVER_IMAGE, "registry", "check", "-r", "/registry", "--future"],
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, f"weaver registry check failed:\n{result.stdout}\n{result.stderr}"
