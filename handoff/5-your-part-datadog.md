# 5 — Your Part (Datadog)

Nick — this is your scope, and only this. Everything else in the demo is built and owned by
Michael. Datadog is a self-contained final phase; it does not block, and is not blocked by, anything
else. Expected start: after approval, ~July 2026.

## The one-paragraph version

The agent already emits OpenTelemetry to one Collector. The Collector fans the **same stream** to
the open CNCF stack today. Your job is to add **Datadog as a second fan-out destination** and build
the Datadog-side views, so the identical telemetry lands in Datadog alongside the CNCF stack. That
side-by-side is the heart of the build-versus-buy comparison — and on stage, Datadog is the primary
surface.

## Concretely, four pieces

1. **Collector exporter.** Add the Datadog OTLP exporter and attach it as a *second* exporter on each
   of the three pipelines (metrics, logs, traces). The integration point is already marked in
   `collector/config.yaml` with a commented `# --- Datadog (Nick) ---` block and a note on each
   pipeline. No change to receivers, processors, or the existing CNCF exporters.
2. **Intake / credentials.** The Datadog API key + site, supplied via the env vault (`~/secrets`),
   **never committed**. That's yours to provide.
3. **Datadog-side views.** The productivity / cost / security views in Datadog from the same stream.
   These are the **primary on-stage surface** — but stay **generic in slides** (no product tour; the
   CFP rejects pitches). Not narrated as "Datadog dashboards" on stage.
4. **Parity check.** Confirm the same three views render in Datadog from the identical OTLP the CNCF
   stack receives.

## What is NOT yours (already built)

The CNCF stack (Prometheus, Loki, Jaeger, Grafana), the Collector pipelines themselves, the
telemetry env file, the custom prod-api MCP server + scripted session + the deny hook (the security
moment), the Grafana dashboards, OTel Weaver, the offline replay, and all the tests. You add a
destination; you do not touch the agent side or the open stack.

## How to verify your half

The repo's `make` dev loop brings the stack up and runs the test suite. Once your exporter and key
are in, push a session through `demo/run-session.sh` and confirm the metrics, events, and the denied
deploy show up in Datadog the same way they do in Grafana.

## If Datadog isn't ready by the event

No problem for the talk — the CNCF stack is the fallback and carries the whole demo unchanged. Your
work makes Datadog the prominent surface; it does not gate the session.

See **doc 4 — Run of Show** for where your Datadog view appears in the 25 minutes, and the repo's
`docs/ownership.md` for the same breakdown in repo form.
