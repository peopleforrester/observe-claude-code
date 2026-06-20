# observe-claude-code

Observing an agentic coding tool (Claude Code) in production with OpenTelemetry.

A single agent session emits metrics, events, and beta traces over OTLP to one OpenTelemetry
Collector, which fans the **identical stream** to a commercial backend (Datadog in this build) and
to an open CNCF stack (Prometheus, Loki, Jaeger, Grafana). Built for the AGNTCon + MCPCon NA 2026
session *"What Does a Good Agent Look Like? Observing Claude Code in Production With OpenTelemetry."*

The demo answers three questions on screen, not in narration:

1. **Productivity** — is the agent moving real work, or just generating activity?
2. **Cost** — where does the spend go, and where does it stop earning?
3. **Security** — what did the agent touch, which tool calls and MCP servers ran, and which were
   allowed or denied?

## Status

The **open CNCF half is complete and validated against real agent telemetry**: a real session runs,
telemetry fans out through the Collector into Prometheus/Loki/Jaeger, lands on a provisioned Grafana
dashboard (including the denied-deploy security moment), and an offline replay re-emits canned
telemetry so the dashboards move with the box offline. 40 integration tests pass against the live
stack.

Remaining: the Datadog backend integration (Nick, ~July). See [`docs/design.md`](docs/design.md)
and [`PROJECT_STATE.md`](PROJECT_STATE.md).

## Backend roles (read this)

The **commercial backend (Datadog) is the primary surface on stage**; the open CNCF stack is the
**fallback** — always present, ready to carry the demo if the vendor path fails, and the basis of
the build-versus-buy comparison. Per the CFP, the on-stage slides keep the vendor **generic** ("a
commercial backend") and do not tour Datadog dashboards; this repo names it because it is the build
target. The open spine (OpenTelemetry, the CNCF stack, the GenAI conventions) carries the talk.

## Who builds what (division of labor)

This repo is shared so a co-presenter can see clearly what is theirs versus what is already done.

- **Michael (built, ~done):** the entire open CNCF stack, the Collector and all-OTLP pipelines, the
  telemetry env file, the custom prod-api MCP server + scripted session + deny hook (the security
  moment), the Grafana dashboards, OTel Weaver, the offline replay, and the run of show.
- **Nick / Datadog (final phase, pending approval — expected July 2026):** the Datadog backend
  integration only — the Datadog OTLP exporter on the Collector, the Datadog intake/key, and the
  Datadog-side views (the primary on-stage surface, kept generic in slides).
- **Not Nick's:** the CNCF stack, the MCP server, the dashboards, the replay — all built already.

Full breakdown and the marked integration point: [`docs/ownership.md`](docs/ownership.md).
Stage sequence and who drives each segment: [`docs/run-of-show.md`](docs/run-of-show.md).

## Architecture

```
Claude Code (CLI, env from env/claude-code.env)
   | OTLP grpc :4317   metrics + logs/events + traces(beta)
   v
OpenTelemetry Collector (one config, three pipelines, all-OTLP exporters)
   metrics ── otlphttp ──► Prometheus  (/api/v1/otlp)      ┐
   logs ───── otlphttp ──► Loki        (/otlp)             ├─► Grafana (3 panes) — FALLBACK
   traces ─── otlp ──────► Jaeger      (:4317 internal)    ┘
        └──────────────► Datadog (OTLP)  — PRIMARY on stage (added in the final phase)
   (aux) OTel Weaver live-check validates the stream against a custom semconv registry
```

## Repository layout

| Path | What |
|---|---|
| `docs/` | Spec, abstract, pinned versions, design + build plan, gotchas (otel, fastmcp, weaver) |
| `compose/docker-compose.yml` | The full stack (Collector + Prometheus + Loki + Jaeger + Grafana) |
| `collector/config.yaml` | One Collector, three all-OTLP pipelines |
| `prometheus/`, `loki/` | Backend configs (native OTLP ingestion) |
| `grafana/provisioning/`, `grafana/dashboards/` | Datasources by uid + the 3-pane dashboard |
| `env/claude-code.env` | Telemetry env that points a session at the Collector |
| `demo/prod-api/server.py` | Custom FastMCP server (benign read + sensitive deploy tool) |
| `.mcp.json`, `.claude/` | MCP registration + the PreToolUse hook that denies deploy |
| `demo/run-session.sh`, `demo/session.md` | The scripted, headless demo session |
| `scripts/bootstrap-docker.sh` | One-time Docker install for the demo host |
| `tests/` | pytest integration suite run against the live stack |
| `Makefile` | sync / up / down / test dev loop |

## How to run

The build host is the demo VPS (Docker + Compose installed via `scripts/bootstrap-docker.sh`).

```bash
# 1. Bring the open stack up (Collector, Prometheus, Loki, Jaeger, Grafana)
docker compose --project-directory . -f compose/docker-compose.yml up -d

# 2. Run the scripted agent session (telemetry flows to the Collector)
demo/run-session.sh

# 3. View Grafana (productivity / cost / security panes)
#    e.g. over an SSH tunnel: ssh -L 3000:localhost:3000 <host> then open http://localhost:3000
#    (admin / admin)
```

The scripted session edits a file, runs Bash, calls the MCP `get_status` tool (accepted), and
attempts the MCP `deploy` tool, which the PreToolUse hook denies — surfacing a visible
`tool_decision=reject` in the Security pane. See [`demo/session.md`](demo/session.md).

## Testing

Integration tests run on the host against the live stack:

```bash
make test     # rsync the tree, then pytest over the dev loop
make up       # bring the stack up
make down     # stop the stack
```

36 tests cover: compose validity, each backend's health and OTLP ingestion, the Collector
fan-out round-trip (metric→Prometheus, log→Loki, trace→Jaeger), container hardening, the dashboard,
the env file, the MCP server, and the deny policy.

## Pinned versions (verified — see docs/versions.md)

Collector Contrib `v0.154.0` · Prometheus `v3.12.0` · Loki `v3.7.2` · Jaeger `v2.19.0` ·
Grafana `12.4.4` · OTel semconv `v1.42.0` · OTel Weaver `v0.23.0` · FastMCP `3.4.x`.

## Documentation

- [`docs/spec.md`](docs/spec.md) — talk and demo build spec (intent)
- [`docs/abstract.md`](docs/abstract.md) — AGNTCon submission
- [`docs/versions.md`](docs/versions.md) — pinned GA versions + spec corrections
- [`docs/design.md`](docs/design.md) — architecture decisions and phased build plan
- [`docs/gotchas-otlp-integration.md`](docs/gotchas-otlp-integration.md) — OTLP-native pipeline gotchas
- [`docs/gotchas-fastmcp.md`](docs/gotchas-fastmcp.md) — FastMCP + MCP-tool-denial recipe
- [`docs/gotchas-weaver.md`](docs/gotchas-weaver.md) — OTel Weaver usage
