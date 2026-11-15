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

# The scripted prompt lives in its own file so capture-session.sh can check that every captured
# tool span, the denied deploy's included, joins back to exactly this prompt.
PROMPT="$(cat demo/session-prompt.txt)"

printf 'Running scripted session (deploy is expected to be denied)...\n' >&2

# deploy is allow-listed so it stays advertised and the model actually calls it; the PreToolUse
# hook in .claude/settings.json then denies it at the call, which is the surface-then-reject path
# that emits tool_decision=reject (source=hook). A plain deny rule would withhold the tool instead.
# OCC_SESSION_ID pins the session ID so capture-session.sh can find the transcript afterwards.
SESSION_ARGS=()
if [[ -n "${OCC_SESSION_ID:-}" ]]; then
  SESSION_ARGS=(--session-id "${OCC_SESSION_ID}")
fi

# --setting-sources project,local keeps the presenter's user settings out of the scripted session:
# a user-level Stop hook (a pytest run, say) would make the session long and could send the
# replayed sample into the Collector mid-capture. The repo's own deny hook still loads.
# stdin is closed so `claude -p` does not wait 3 seconds for piped input.
claude -p "${PROMPT}" "${SESSION_ARGS[@]}" \
  --setting-sources project,local \
  --permission-mode acceptEdits \
  --mcp-config .mcp.json --strict-mcp-config \
  --allowedTools "mcp__prod-api__get_status,mcp__prod-api__deploy,Read,Edit,Write,Bash" \
  </dev/null
