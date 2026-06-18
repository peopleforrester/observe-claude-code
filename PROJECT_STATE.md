# PROJECT_STATE.md — observe-claude-code

ABOUTME: Durable build state for the observe-claude-code demo. Read this first when resuming.
ABOUTME: Source of truth across sessions; reconcile against git log/status before trusting it.

**Last updated:** 2026-06-15
**Branch:** `staging` (work here; PR to `main` after tests pass — never push main directly)
**Repo:** github.com/peopleforrester/observe-claude-code

## What this is

Demo + talk for AGNTCon + MCPCon NA 2026 (Oct 22–23, San Jose). One Claude Code session emits
OTLP to one Collector that fans the identical stream to an open CNCF stack (Prometheus, Loki,
Jaeger, Grafana) and later a commercial backend, side by side. See `docs/spec.md` for intent,
`docs/design.md` for the build plan.

## Verification method

Research-based: four parallel sub-agents verified all component versions and the Claude Code
telemetry schema against official release pages and live docs on 2026-06-15 (web research, not
live browser). Claude Code schema confirmed verbatim against code.claude.com/docs/en/monitoring-usage.
Nothing has been run or stood up yet — no container has been launched.

## Locked decisions

- Compose on the VPS (not k8s) for the stage.
- OTLP-native everywhere: Prometheus native OTLP receiver (not remote write), Loki `/otlp`, Jaeger OTLP.
- OTel Weaver `registry live-check` as a live "validate against an open standard" beat.
- Offline replay = capture + re-emit OTLP; screen recording as the floor.
- Commercial backend (Datadog) deferred until a key is available.
- Demo MCP = custom "prod API" server with one denied write tool.
- Grafana pinned 12.4.x (NOT latest 13.0.2) to avoid v13 provisioning trap — **pending Michael's
  final sign-off**; he was asked to veto if he wants latest.
- Substrate confirmed: **Docker Compose, single-host** on the VPS for the AGNTCon 25-min slot
  (Helm/k8s reserved for the KubeCon 35-min version). Substrate is plumbing, not content.
- Talk close confirmed: **forward-looking close + cross-link** to the sibling enforcement project
  `idea-dynamic-software-blocker` (observe → enforce). Not merged; see design.md §7.

## Pinned versions (verified 2026-06-15, re-verify week of Oct 2026)

Collector Contrib v0.154.0 · Prometheus v3.12.0 · Loki v3.7.2 · Jaeger v2.19.0 ·
Grafana 12.4.x (latest is 13.0.2) · OTel semconv v1.42.0 · OTel Weaver v0.23.0 (pre-1.0).

## Phase checklist

- [x] Repo init + GitHub remote + staging branch
- [x] Docs: spec, abstract, versions, design, gotchas-weaver, gotchas-otlp-integration
- [x] Phase 0 — Scaffold (dir tree, README, .gitignore, PROJECT_STATE)
- [x] Phase 0.5 — Weaver research spike (→ docs/gotchas-weaver.md; verdict: live step feasible, LOW cost)
- [x] Phase 1 — Compose stack stands up (4 backends, pinned) ← just completed. Built TDD on the
      VPS; 14 integration tests green; all containers healthy; Grafana shows 3 connected datasources.
      Jaeger `0.0.0.0` bind trap did NOT occur on v2.19 (doc corrected). Collector moved to Phase 2.
- [x] Phase 1.1 — Hardening: healthchecks (Prometheus/Jaeger/Grafana via wget; Loki is distroless,
      no probe), mem_limit/cpus on all four, Grafana depends_on health-gated. 18 tests green.
- [x] Phase 2 — Collector with all-OTLP fan-out. One OTLP receiver → 3 pipelines → Prometheus
      /api/v1/otlp, Loki /otlp, Jaeger OTLP. Collector owns host 4317/4318/13133; Jaeger moved
      internal. Round-trip proven (metric→Prom, log→Loki, trace→Jaeger). 22 tests green.
- [x] Phase 3 — Agent telemetry env file (env/claude-code.env). Static validation (3 tests) +
      a live smoke: one headless `claude -p` with the env sourced emitted real telemetry into
      Prometheus (session.count, cost.usage_USD, token.usage x4, active_time) labelled
      cost_center=agntcon/role=backend. 25 tests green. Live emit kept as manual validation, not
      a claude-spawning test (suite stays fast/deterministic; we run on this box, ~63 claude procs).
- [x] Phase 4 — Grafana dashboard, 3 panes (v1 schema). Productivity/Cost/Security rows wired to
      claude_code_* metrics + Loki events; provisioned and verified. 29 tests green. (Smoke data
      from Phase 3 is ~18h old now and aged out of the default window — irrelevant for live/replay.)
- [ ] Phase 5 — Scripted session + custom prod-API MCP. This is what finally fills the Security
      pane (tool_decision reject + mcp_server_connection) with real data on stage.
- [ ] Phase 6 — Capture + re-emit offline replay (highest risk)
- [ ] Phase 7 — Vendor backend + rehearsal + screen-capture floor

## Build host + dev loop

**We run ON the netcup box itself** (hostname `v2202603344103445992`) — this Claude session and
the build are on the VPS, not a separate laptop. The `netcup` ssh alias loops back to localhost;
that loopback session is what carries the `docker` group, so docker/uv commands go through
`ssh netcup '...'` (the direct shell lacks the docker group). Docker 29.5.3 + Compose v5.1.4
(installed via `scripts/bootstrap-docker.sh`); uv user-space. `Makefile`: `make sync` rsyncs the
tree to `~/observe-claude-code`, `make up/down/test` drive Compose and pytest. Tests hit the live
stack on localhost.

**~63 `claude` processes run on this box.** Never kill/signal/interfere with them — no pkill,
killall, or broad signals. All work stays scoped to `occ-*` containers and `~/observe-claude-code`.

## Last completed step

Phase 4 done on branch `feature/phase-4-dashboard` (dashboard provider + v1-schema dashboard,
TDD). 29 integration tests pass against the live stack. Next: merge to staging.

## Next step

Phase 5: build the custom "prod-API" MCP server (one benign read tool + one sensitive write/deploy
tool denied by config), wire it into a scripted session (`demo/session.md`) that edits files in
`demo/target/`, runs Bash, calls the read tool, then trips the denied write — producing the
tool_decision reject + mcp_server_connection events the Security pane needs. See
frameworks/fastmcp.md for the MCP server conventions.

## Open items needing Michael

1. Grafana 12.4.x vs latest 13.0.2 — confirm the deliberate non-latest pin is acceptable.
2. Datadog key availability (gates Phase 7).
