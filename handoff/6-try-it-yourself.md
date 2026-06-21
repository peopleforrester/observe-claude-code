# 6 — Try It Yourself

Bring the real thing up and watch it move. Everything here runs from the repo on the demo host
(Docker + Compose installed; see the repo README for the one-time bootstrap).

## 1. Bring the open stack up

```bash
docker compose --project-directory . -f compose/docker-compose.yml up -d
```

Five containers come up: the OpenTelemetry Collector, Prometheus, Loki, Jaeger, and Grafana.

## 2. Run a scripted agent session

```bash
demo/run-session.sh
```

This drives a headless agent session that edits a file, runs a command, calls the prod-api
`get_status` tool (allowed), and attempts `deploy` (denied by policy — the security moment).

## 3. Watch the dashboard

Open Grafana (e.g. over an SSH tunnel: `ssh -L 3000:localhost:3000 <host>`, then
http://localhost:3000, admin/admin). The three panes — Productivity, Cost, Security — fill with the
session's telemetry, including the denied deploy in the Security row.

## 4. See the offline replay (the safety net)

```bash
python3 demo/replay/replay.py --capture demo/replay/session-sample.jsonl --loop
```

Re-emits canned telemetry with fresh timestamps so the dashboards move with no live agent — this is
what carries the demo if the room network misbehaves.

## 5. See the open-standard validation (Weaver)

```bash
weaver/live-check.sh
```

Validates the agent's telemetry against our semantic-convention registry and prints the report —
`claude_code.*` attributes recognized, `gen_ai.*` flagged as the evolving standard.

## 6. Run the tests

```bash
make test
```

The integration suite brings probes through the live stack and asserts the whole pipeline works.

## Tear down

```bash
docker compose --project-directory . -f compose/docker-compose.yml down
```
