# observe-claude-code

_Repo context file for AI coding CLIs (Claude Code, Codex, OpenCode, Gemini, etc.)._

## What this is

Conference demo for AGNTCon + MCPCon NA 2026 (Oct 22–23, San Jose): "What Does a Good Agent Look Like?
Observing Claude Code in Production With OpenTelemetry." One Claude Code session emits OTLP to a
single Collector that fans the identical stream to a full CNCF open-source stack (Prometheus, Loki,
Jaeger, Grafana) and — when Datadog is wired in — to a commercial backend side by side.

Co-presented with Nick Isaacs (Datadog). Michael owns the CNCF side; Nick owns the Datadog side.

## Stack

Python 3.13 + uv + pytest · Docker Compose (single-host VPS) · FastMCP 3.4.x · OTel Collector
Contrib 0.154.0 · Prometheus 3.12.0 · Loki 3.7.2 · Jaeger 2.19.0 · Grafana 12.4.x · OTel Weaver
0.23.0

## Commands

- **Install:** `uv sync --dev`
- **Test:** `uv run pytest` (integration smoke suite; requires live Compose stack)
- **Bring stack up:** `make up` (runs via `ssh netcup 'make -C ~/observe-claude-code up'`)
- **Bring stack down:** `make down`
- **Run scripted demo session:** `bash demo/run-session.sh`
- **Offline replay:** `uv run python demo/replay/replay.py`
- **Publish Drive handoff docs:** `make publish-handoff`

## Conventions

- Work on `staging` only; never push directly to `main`.
- Docker commands go through `ssh netcup` — the direct shell lacks the docker group.
- ~63 `claude` processes run permanently on the VPS; never kill/signal them.
- All OTel exporters are OTLP-native: no remote write, no push gateway.
- Datadog integration is marked with `# --- Datadog (Nick) ---` in `collector/config.yaml`.
- Privacy gates (`OTEL_LOG_USER_PROMPTS` etc.) are deliberately NOT set in `env/claude-code.env`.
- The MCP `deploy` tool is ALLOWED (so it's advertised) but denied by a PreToolUse hook — this is
  intentional; a permission `deny` rule withholds the tool entirely and produces no telemetry event.
- `uv.lock` is committed for reproducibility.
- `transcripts/` is gitignored — the MRF transcript pipeline routes here; keep that content local.
