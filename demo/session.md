# Scripted demo session

ABOUTME: The fixed prompt sequence that drives the on-stage telemetry, and how to run it.
ABOUTME: Produces productivity, cost, and security signals — including a denied prod deploy.

The session is run headless and non-interactively so the telemetry is deterministic.
`demo/run-session.sh` sources `env/claude-code.env`, then runs the agent with the prod-api
MCP server registered and a policy that denies the deploy tool.

## What the session does

1. **Edit** `demo/target/app.py` (appends a line) → productivity: `lines_of_code`, an Edit tool call.
2. **Bash** `echo build ok` → a Bash tool call with `full_command` (security pane detail).
3. **Call `prod-api.get_status`** for the `checkout` service → an MCP tool call, **accepted**.
4. **Call `prod-api.deploy`** `checkout` `2.0.0` → **denied** by the PreToolUse hook
   (`.claude/hooks/deny-prod-deploy.sh`) → `tool_decision` with `decision=reject`, `source=hook`.

Why a hook and not a `deny` rule: a permission `deny` rule *withholds* the MCP tool from the
agent entirely (it's never advertised, never called, emits no event — the denial is invisible).
Allowing the tool so it's advertised and denying it at the call via a PreToolUse hook is what
makes the denial surface as a visible `tool_decision=reject` event for the Security pane.

## Telemetry produced

- Metrics (Prometheus): `claude_code.session.count`, `lines_of_code.count`, `cost.usage`,
  `token.usage`, `active_time.total`.
- Events (Loki): `mcp_server_connection` (prod-api, stdio), `tool_decision` (accept for
  get_status, **reject for deploy**), `tool_result` for executed tools. (Loki stores the bare
  `event_name` value — `tool_decision` — not `claude_code.tool_decision`.)
- Traces (Jaeger): the `claude_code.interaction` → `llm_request` / `tool` waterfall, with the MCP
  tool call visible.

## Run it

```bash
demo/run-session.sh
```

Reset the target between runs if desired:

```bash
git checkout -- demo/target/app.py
```

## Stage assertion

The invariant security signal is `claude_code.tool_decision` with `decision=reject` for
`mcp_tool_name=deploy`. The `source` value differs between interactive and headless runs, so the
demo keys on `decision=reject` + the deploy tool, not on `source`.
