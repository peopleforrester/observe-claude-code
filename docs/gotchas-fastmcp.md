# Gotchas: FastMCP + Claude Code MCP denial (verified 2026-06-18; FastMCP 4 bump 2026-10-31)

ABOUTME: Current FastMCP 4.x API and the deterministic MCP-tool-denial recipe for the demo.
ABOUTME: Verified against gofastmcp.com and code.claude.com on 2026-06-18.

## FastMCP version and API

- **Locked: `fastmcp` 4.1.4 (2026-10-26)**, on MCP Python SDK `mcp` 2.x. 4.0.0 went GA on
  2026-08-31 and is built on the `2026-07-28` MCP protocol revision; 3.x still gets maintenance
  releases. Install with `uv add fastmcp`.
- **FastMCP 4 negotiates the protocol per connection**, so pre-2026 clients keep working: a
  `2025-06-18` stdio handshake gets `2025-06-18` back; `tests/test_mcp_server.py` pins this.
- The 4.0 breaking changes (server-initiated sampling/roots removed, `ctx.elicit()` old-protocol
  only, 3.x deprecated APIs gone, snake_case MCP model fields, tasks moved to `fastmcp-tasks`) don't
  touch this server, which only uses `FastMCP(name)`, `@mcp.tool`, and `mcp.run()`. Upgrade guide:
  <https://gofastmcp.com/getting-started/upgrading/from-fastmcp-3>.
- **Import the standalone package: `from fastmcp import FastMCP`.** `mcp.server.fastmcp` is gone
  in `mcp` 2.x (it was the frozen FastMCP 1.0 bundled in the SDK).
- Repo moved to **`PrefectHQ/fastmcp`** (was `jlowin/fastmcp`); imports and PyPI name unchanged.
- Tool decorator: **`@mcp.tool` (no parens)** is the modern form; `@mcp.tool()` still works.
- **Since v3** (still true in v4): `@mcp.tool` returns the *original, still-callable function* (v2
  returned a `FunctionTool`). So `my_tool.name` after decorating breaks — but the function stays
  directly callable, which is handy for unit tests.
- `mcp.run()` with no args **defaults to stdio**; `mcp.run(transport="stdio")` is the explicit form.
- Returns: `str`/`dict`/dataclass/Pydantic → dicts and models become structured content
  automatically (no manual `TextContent` wrapping).

## Deterministic MCP-tool denial in headless Claude Code

- **Register (project scope)** via `.mcp.json` at the repo root:
  ```json
  {"mcpServers": {"prod-api": {"command": "uv", "args": ["run", "python", "demo/prod-api/server.py"], "env": {}}}}
  ```
  or `claude mcp add --scope project prod-api -- uv run python demo/prod-api/server.py`.
- **Permission rule format is `mcp__<server>__<tool>` (double underscores).** Deny precedence over
  allow; rules merge across scopes. Project `.claude/settings.json`:
  ```json
  {"permissions": {"allow": ["mcp__prod-api__get_status"], "deny": ["mcp__prod-api__deploy"]}}
  ```
- **Run headless and non-interactive** so read=accept, deploy=reject with no prompt:
  ```bash
  claude -p "<prompt>" --permission-mode dontAsk \
    --mcp-config .mcp.json --strict-mcp-config \
    --allowedTools "mcp__prod-api__get_status,Read,Edit,Write,Bash" \
    --disallowedTools "mcp__prod-api__deploy"
  ```
  `dontAsk` auto-denies anything not allow-listed (no prompt); the explicit deny makes the deploy
  denial a hard policy decision.
- **Telemetry** (events ride the **logs** protocol — `OTEL_LOGS_EXPORTER` must be set):
  - `claude_code.tool_decision`: `decision=reject` for deploy, `accept` for get_status. With
    `OTEL_LOG_TOOL_DETAILS=1`, `tool_parameters` carries `mcp_server_name`/`mcp_tool_name`.
  - **`source` varies**: a deny in *project* settings / `--disallowedTools` → `source=config`; a deny
    in *personal* settings under headless `-p` → `source=user_reject`. **Assert on `decision=reject`
    + `mcp_tool_name=deploy` (invariant), not on `source`.**
  - `claude_code.mcp_server_connection`: `status=connected`, `transport_type=stdio`,
    `server_scope=project`; `server_name=prod-api` shown when `OTEL_LOG_TOOL_DETAILS=1`.
  - Rejected calls emit a `tool_decision` but **no `tool_result`** (only executed calls do).

## Things to verify in a dry run

- A checked-in project `.mcp.json` server is normally `⏸ Pending approval` until approved
  interactively. `--mcp-config .mcp.json --strict-mcp-config` is the documented headless path that
  loads only the passed config; confirm it skips the approval prompt on the installed version
  (`claude --help`) before relying on it on stage.
