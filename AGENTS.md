# observe-claude-code

_Repo context file for AI coding CLIs (Claude Code, Codex, OpenCode, Gemini, etc.)._

## What this is

Demo for the talk "What Does a Good Agent Look Like? Observing Claude Code in Production With
OpenTelemetry," first written as an AGNTCon + MCPCon NA 2026 submission. One Claude Code session emits OTLP to a
single Collector that fans the identical stream to a full CNCF open-source stack (Prometheus, Loki,
Jaeger, Grafana) and — when Datadog is wired in — to a commercial backend side by side.

Co-presented with Nick Isaacs (Datadog). Michael owns the CNCF side; Nick owns the Datadog side.

## Where things live

- **Conferences, CFPs, deadlines, submission status, attendance, travel:** conference-knowledge
  (`~/repos/conferences/conference-knowledge`: `events/cfp_pipeline.yaml`, `events/registry.yaml`).
  Read it there; don't copy it here. To change it, file an `agent-task` issue on
  `peopleforrester/conference-knowledge`.
- **The talk's register entry, content, argument and abstracts:** talks-knowledge
  (`~/repos/talks/talks-knowledge`: `talks/register.md` row 8, `abstracts/`). Read it there. To
  change it, file an `agent-task` issue on `peopleforrester/talks-knowledge`.
- **The Toronto standby version of this talk:** its own repo,
  `peopleforrester/reading-agent-mcp-calls-through-otel` (`~/repos/talks/reading-agent-mcp-calls-through-otel`),
  built from this one. This repo is its source; don't put that deck here.
- **Build state:** `PROJECT_STATE.md`. **Decisions:** `decisions.md`, append-only: add new entries
  at the end, never edit or remove old ones.

## Stack

Python 3.13 + uv + pytest · Docker Compose (single-host VPS) · FastMCP 4.1.x · OTel Collector
Contrib 0.154.0 · Prometheus 3.12.0 · Loki 3.7.2 · Jaeger 2.19.0 · Grafana 12.4.x · OTel Weaver
0.23.0

## Commands

- **Install:** `uv sync --dev`
- **Test:** `uv run pytest -m "not integration"` (offline unit tests; no stack needed). Integration
  smoke suite: `uv run pytest -m integration` (needs a working `docker`; it brings the Compose
  stack up with `up -d --wait`, reuses one that is already running, and takes down only a stack
  it started). Plain `uv run pytest` runs both.
- **Bring stack up:** `make up` (runs via `ssh netcup 'make -C ~/observe-claude-code up'`)
- **Bring stack down:** `make down`
- **Run scripted demo session:** `bash demo/run-session.sh`
- **Offline replay:** `uv run python demo/replay/replay.py`
- **Capture a session (OTLP + transcript pair):** `bash demo/replay/capture-session.sh`
- **Join a trace back to its prompt:** `uv run python demo/replay/join.py --capture <capture> --trace <id>`
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
- Integration runs on one host take turns: the suite holds a flock on
  `/run/lock/observe-claude-code-stack.lock` (`OCC_STACK_LOCK`) for the whole session, waiting up
  to `OCC_STACK_LOCK_TIMEOUT` seconds (default 1800). Each published host port reads an
  `OCC_*_PORT` variable in both `compose/docker-compose.yml` and `tests/conftest.py`, defaulting to
  the service's own port, so a stack can also be published elsewhere (#25).
- `transcripts/` is gitignored — the MRF transcript pipeline routes here; keep that content local.

Test command: `uv run pytest -m "not integration"`
E2E command: `uv run pytest -m integration`
