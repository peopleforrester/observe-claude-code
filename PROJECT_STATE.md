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
- [ ] Phase 3 — Claude Code env file (env/claude-code.env from spec §5). Open question: does the
      "run a real claude session" validation happen on the VPS (needs claude installed + authed
      there) or locally pointed at the VPS collector? Decide before building the Phase 3 test.
- [ ] Phase 4 — Single Grafana dashboard, 3 panes (v1 schema only)
- [ ] Phase 5 — Scripted session + custom prod-API MCP
- [ ] Phase 6 — Capture + re-emit offline replay (highest risk)
- [ ] Phase 7 — Vendor backend + rehearsal + screen-capture floor

## Build host + dev loop

Build host is the **netcup VPS** (Docker 29.5.3 + Compose v5.1.4 installed via
`scripts/bootstrap-docker.sh`; uv installed user-space). Local→VPS loop is the `Makefile`:
`make sync` rsyncs the tree to `netcup:~/observe-claude-code`, `make up/down/test` drive Compose
and pytest over SSH. Tests run on the VPS against the live stack on localhost.

## Last completed step

Phase 2 done on branch `feature/phase-2-collector` (2 TDD batches: collector up/healthy, then the
OTLP round-trip). 22 integration tests pass against the live stack. Next: merge to staging.

## Next step

Phase 3: author `env/claude-code.env` from spec §5 (verified schema). Decide the validation
approach first (see Phase 3 note above) — whether a real `claude` session runs on the VPS or
locally against the VPS collector. Build the Phase 3 test around that decision.

## Open items needing Michael

1. Grafana 12.4.x vs latest 13.0.2 — confirm the deliberate non-latest pin is acceptable.
2. Datadog key availability (gates Phase 7).
