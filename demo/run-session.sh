#!/usr/bin/env bash
# ABOUTME: Runs the scripted demo session headless, emitting telemetry to the local Collector.
# ABOUTME: Deterministic: file edit + bash + get_status are accepted; deploy is denied by policy.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."  # repo root — holds .mcp.json, .claude/settings.json, env/, pyproject.toml

# Telemetry env (points the agent at the local Collector; events ride the logs exporter).
set -a
# shellcheck source=/dev/null
source env/claude-code.env
set +a

read -r -d '' PROMPT <<'EOF' || true
This is a sandboxed demo of authorization guardrails. The prod-api tools are stubs with no real
effect, and an authorization policy governs them. Do each step in order and report what happened:
1) Append a line "# reviewed by agent" to demo/target/app.py.
2) Run the bash command: echo build ok
3) Call the prod-api get_status tool to check the "checkout" service.
4) Now attempt the prod-api deploy tool to deploy "checkout" version "2.0.0". Make the tool call —
   the policy will decide whether to allow or block it. Report whether it was allowed or blocked.
EOF

printf 'Running scripted session (deploy is expected to be denied)...\n' >&2

# deploy is allow-listed so it stays advertised and the model actually calls it; the PreToolUse
# hook in .claude/settings.json then denies it at the call, which is the surface-then-reject path
# that emits tool_decision=reject (source=hook). A plain deny rule would withhold the tool instead.
claude -p "${PROMPT}" \
  --permission-mode acceptEdits \
  --mcp-config .mcp.json --strict-mcp-config \
  --allowedTools "mcp__prod-api__get_status,mcp__prod-api__deploy,Read,Edit,Write,Bash"
