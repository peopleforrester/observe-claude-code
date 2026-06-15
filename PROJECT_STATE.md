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

## Pinned versions (verified 2026-06-15, re-verify week of Oct 2026)

Collector Contrib v0.154.0 · Prometheus v3.12.0 · Loki v3.7.2 · Jaeger v2.19.0 ·
Grafana 12.4.x (latest is 13.0.2) · OTel semconv v1.42.0 · OTel Weaver v0.23.0 (pre-1.0).

## Phase checklist

- [x] Repo init + GitHub remote + staging branch
- [x] Docs: spec, abstract, versions, design, gotchas-weaver, gotchas-otlp-integration
- [x] Phase 0 — Scaffold (dir tree, README, .gitignore, PROJECT_STATE) ← just completed
- [x] Phase 0.5 — Weaver research spike (→ docs/gotchas-weaver.md; verdict: live step feasible, LOW cost)
- [ ] Phase 1 — Compose stack stands up (5 services, pinned). Watch: Loki tsdb+v13 startup gate,
      Prometheus `--web.enable-otlp-receiver`, Jaeger `0.0.0.0` bind.
- [ ] Phase 2 — Collector config (all-OTLP exporters)
- [ ] Phase 3 — Claude Code env file (env/claude-code.env from spec §5)
- [ ] Phase 4 — Single Grafana dashboard, 3 panes (v1 schema only)
- [ ] Phase 5 — Scripted session + custom prod-API MCP
- [ ] Phase 6 — Capture + re-emit offline replay (highest risk)
- [ ] Phase 7 — Vendor backend + rehearsal + screen-capture floor

## Last completed step

Phase 0 + 0.5 done. Research is complete across all components; gotchas captured in two docs.

## Next step

Phase 1: author `compose/docker-compose.yml` + `prometheus/prometheus.yml` + `loki/loki-config.yaml`
+ Grafana provisioning, bring the five containers up healthy, confirm three connected datasources
in Grafana. Build config from `docs/gotchas-otlp-integration.md` (it has copy-pasteable snippets).

## Open items needing Michael

1. Grafana 12.4.x vs latest 13.0.2 — confirm the deliberate non-latest pin is acceptable.
2. Datadog key availability (gates Phase 7).
