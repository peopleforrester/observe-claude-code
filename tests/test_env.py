# ABOUTME: Static validation of env/claude-code.env against the verified Claude Code schema.
# ABOUTME: Asserts required telemetry vars are correct and the content-privacy gates stay unset.
from conftest import REPO_ROOT

ENV_FILE = REPO_ROOT / "env" / "claude-code.env"

REQUIRED = {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
    "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE": "cumulative",
    "OTEL_LOG_TOOL_DETAILS": "1",
    "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "1",
    "OTEL_TRACES_EXPORTER": "otlp",
}

# These pull in prompt text / tool output / raw API bodies — they must stay unset.
FORBIDDEN = {"OTEL_LOG_USER_PROMPTS", "OTEL_LOG_TOOL_CONTENT", "OTEL_LOG_RAW_API_BODIES"}


def _parse_env(path):
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def test_required_vars_present_and_correct():
    env = _parse_env(ENV_FILE)
    for key, expected in REQUIRED.items():
        assert env.get(key) == expected, f"{key} should be {expected!r}, got {env.get(key)!r}"


def test_content_privacy_gates_unset():
    env = _parse_env(ENV_FILE)
    leaked = FORBIDDEN & env.keys()
    assert not leaked, f"content-revealing telemetry vars must stay unset: {sorted(leaked)}"


def test_resource_attributes_carry_role_framing():
    env = _parse_env(ENV_FILE)
    attrs = env.get("OTEL_RESOURCE_ATTRIBUTES", "")
    for expected in ("role=backend", "team.id=demo", "cost_center=agntcon"):
        assert expected in attrs, f"missing resource attribute {expected!r}"
