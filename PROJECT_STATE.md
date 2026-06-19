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
- Commercial backend = **Datadog: primary on stage, owned by Nick, parked until ~July 2026**. CNCF
  stack is the **fallback** (built first, carries the demo if Datadog isn't ready). Datadog is the
  only co-presenter scope; integration point marked in collector/config.yaml. See docs/ownership.md
  and docs/run-of-show.md.
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
- [x] Phase 5 — Custom prod-api FastMCP server + scripted session + deny hook. Security pane now
      fills with real data: mcp_server_connection, tool_decision accept (get_status) + reject
      (deploy). KEY FINDING: a permission `deny` rule WITHHOLDS an MCP tool (never advertised,
      never called, no event — invisible); to get a visible tool_decision=reject you must ALLOW
      the tool (so it's advertised/called) and deny it via a PreToolUse hook (source=hook). Also
      fixed a Phase 4 dashboard bug: Loki event_name has NO `claude_code.` prefix (it's
      `tool_decision`, `mcp_server_connection`). 36 tests green. Live session runs via
      demo/run-session.sh (kept as a documented smoke, not an automated claude-spawning test).
- [ ] Phase 6 — Capture + re-emit offline replay (highest risk) — OWNER: Michael, next
- [ ] Phase 7 (FINAL) — Datadog backend + parity + rehearsal — OWNER: Nick, parked until ~July 2026

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

Phase 5 done on branch `feature/phase-5-mcp` (3 TDD batches: MCP server, registration+hook,
scripted session). 36 integration tests pass; the live session emits the full security story.
Next: merge to staging.

## Next step

Phase 6: offline replay (highest risk). Capture one real run's OTLP (a `file`/`debug` exporter on
the Collector, or a parallel capture) into `demo/replay/`, then a script that re-emits it over OTLP
to the Collector with freshened timestamps so the dashboards move with the box offline. Decide the
capture mechanism first; keep a screen recording as the floor. The Phase 3 + Phase 5 live runs are
good source material to capture.

## Open items needing Michael

1. Grafana 12.4.x vs latest 13.0.2 — confirm the deliberate non-latest pin is acceptable.
2. Datadog approval + key (gates Phase 7, Nick's scope; expected ~July 2026). Non-blocking for the
   CNCF fallback, which is complete.
