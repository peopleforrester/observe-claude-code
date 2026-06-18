#!/usr/bin/env bash
# ABOUTME: PreToolUse hook that denies the prod-api deploy tool — the demo's deterministic guardrail.
# ABOUTME: Returns a deny decision so the blocked deploy surfaces as a tool_decision=reject event.
set -euo pipefail
cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Production deploys are blocked by policy in this demo."}}
JSON
exit 0
