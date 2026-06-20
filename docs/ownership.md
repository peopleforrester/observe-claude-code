# Division of Labor

ABOUTME: Clear ownership map so a co-presenter knows exactly what is theirs vs already built.
ABOUTME: Datadog is the only co-presenter scope; everything else is built and owned by Michael.

**Speakers:** Michael Forrester (Accenture, primary) + Nick Isaacs (Datadog, co-speaker).
**Status as of 2026-06-19:** the open CNCF half is built and validated (36 tests green). The
Datadog integration is the final phase and is **parked until approval (expected July 2026)**.

## TL;DR

| Area | Owner | State |
|---|---|---|
| OTel Collector + all-OTLP pipelines | Michael | Done |
| Prometheus / Loki / Jaeger / Grafana (CNCF stack) | Michael | Done |
| Grafana dashboards (3 panes) | Michael | Done |
| Telemetry env file | Michael | Done |
| Custom prod-api MCP server + scripted session + deny hook | Michael | Done |
| OTel Weaver validation beat | Michael | Researched; build pending |
| Offline replay (stage safety net) | Michael | Done |
| Run of show / talk structure | Michael | In progress |
| **Datadog backend integration** | **Nick** | **Parked → July** |
| **Datadog-side views (primary on-stage surface)** | **Nick** | **Parked → July** |

## Michael's scope (built / owned)

The entire **open spine and the agent side**. None of this needs Nick:

- `compose/docker-compose.yml`, `collector/config.yaml`, `prometheus/`, `loki/`, `grafana/`.
- `env/claude-code.env` — the telemetry configuration.
- `demo/prod-api/server.py`, `.mcp.json`, `.claude/` (settings + deny hook), `demo/run-session.sh`,
  `demo/session.md` — the scripted session and the security moment.
- `weaver/` (registry) and the Weaver live-check beat.
- `demo/replay/` — offline replay (Phase 6).
- All `tests/`, the `Makefile` dev loop, and `scripts/bootstrap-docker.sh`.

## Nick's scope (Datadog only — the final phase)

Everything Datadog, and **only** Datadog. The integration point is already marked in
`collector/config.yaml` (a commented `# --- Datadog (Nick) ---` block). Concretely:

1. **Collector exporter.** Add the Datadog OTLP exporter (a second exporter on each of the three
   pipelines — metrics, logs, traces) so the *same* OTLP stream lands in Datadog alongside the CNCF
   stack. No change to receivers, processors, or the existing exporters.
2. **Intake / credentials.** The Datadog API key/site config — supplied via the env vault
   (`~/secrets`), **never committed**. The `.env`/key handling is Nick's to provide.
3. **Datadog-side views.** The productivity / cost / security views in Datadog from the same
   stream. These are the **primary on-stage surface** but stay **generic in slides** (no product
   tour — CFP rejects pitches). Not discussed as "Datadog dashboards" on stage.
4. **Parity check.** Confirm the same three views render in Datadog from the identical OTLP the CNCF
   stack receives — the heart of the build-versus-buy comparison.

## Explicitly NOT Nick's

The CNCF stack, the Collector pipelines themselves, the MCP server, the dashboards, the env file,
the replay, and the tests are all built and owned by Michael. Nick adds Datadog as a fan-out
destination; he does not modify the agent side or the open stack.

## Handing off cleanly

- The repo is public; Nick (or a replacement) works from this doc + `docs/design.md` +
  `docs/run-of-show.md`.
- The Datadog work is self-contained: add the exporter at the marked point, supply the key, build
  the views, verify parity. It does not block — and is not blocked by — anything else.
- Backend role: **Datadog is primary on stage; the CNCF stack is the fallback.** If the Datadog path
  is not ready by the event, the CNCF dashboards carry the demo unchanged.
