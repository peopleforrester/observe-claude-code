# decisions.md: observe-claude-code

Append-only. Add each new decision at the end with its date and the issue it came from; never edit
or remove an earlier entry. Decisions taken before 2026-11-01 are in `PROJECT_STATE.md` ("Locked
decisions") and `docs/design.md`; they are not copied here.

## 2026-11-01 · The README says who this repo is and points at the knowledge repos (#10)

**Decision:** README.md gains a "This talk" table that gives the title, the speakers, the argument,
the form, the event, the status, what the repo is built from, where it is registered, and the
sibling repo. AGENTS.md (CLAUDE.md is a symlink to it) names talks-knowledge for the register
entry and abstracts, conference-knowledge for event state, and the sibling repo.

**Why:** talks-knowledge asked on 2026-10-14 that every talk repo say who it is and point at
talks-knowledge, which is the source of truth for the register (`talks/register.md`, row 8 for
this talk) and the abstracts.

**Event state stays a pointer.** The Event row says only that nothing is booked or delivered as
of 2026-11-01, and names conference-knowledge for submissions, dates and bookings. It lists no
submissions, because #7 removed copied conference facts from this repo and a copied list would go
stale.

**Built from:** this repo is the source; the demo is written here. The Toronto
standby deck, `peopleforrester/reading-agent-mcp-calls-through-otel`, is a separate repo built from
this one (Michael, 2026-10-05: each talk has its own repo; source repos are read, never written).
`tests/test_repo_identity.py` fails if any of these pointers goes missing.

## 2026-11-01 · An unreachable Collector skips the replay pass in --loop and fails a single pass (#23)

**Decision:** when `demo/replay/replay.py` cannot reach the Collector at all (refused connection,
DNS failure, socket timeout: any `OSError` out of `post()`), `--loop` prints a warning, skips the
rest of that pass, and tries again after `--interval`. A single pass (no `--loop`) exits non-zero
with "Collector unreachable at <endpoint>: <reason>" instead of a traceback. A 4xx/5xx rejection
still warns per record and moves on, as #13 decided.

**Why the pass, not the record:** a down Collector fails every record the same way, and with the
10-second `urlopen` timeout, skipping record by record could stall a pass for 10 seconds per record.
Skipping the pass costs at most one timeout per interval, and the next pass re-shifts the whole
capture to the new "now", so nothing is lost by dropping the rest of the failed pass.

**Why a single pass still fails:** a one-shot replay is run by hand or by the integration test,
which checks the exit code; a silent zero exit with nothing sent would hide a dead Collector.
`tests/test_replay_unit.py` drives both paths against a closed loopback port.

## 2026-11-01 · Integration runs on one host take turns on a host lock; host ports are overridable (#25)

**Decision:** both fixes the issue offered. A session-scoped autouse fixture in
`tests/conftest.py` holds an exclusive `flock` on `/run/lock/observe-claude-code-stack.lock` for the
whole pytest session whenever the run selects an `integration` test, so a second run on the same
host waits (up to `OCC_STACK_LOCK_TIMEOUT`, 1800 s by default) and then fails with a message that
names the lock. Every published host port also reads an `OCC_*_PORT` variable
(`OCC_PROMETHEUS_PORT`, `OCC_LOKI_PORT`, `OCC_JAEGER_UI_PORT`, `OCC_GRAFANA_PORT`,
`OCC_OTLP_GRPC_PORT`, `OCC_OTLP_HTTP_PORT`, `OCC_COLLECTOR_HEALTH_PORT`) in both
`compose/docker-compose.yml` and `tests/conftest.py`, defaulting to today's ports.

**Why the lock is the fix and the ports are the escape hatch:** each run defaults to the same ports,
so overridable ports alone still collide unless every caller picks its own. The lock makes the
default case safe with no setup. The port variables cover what a lock cannot: a stack that is not
a test run's (the demo box), or a run that needs to go alongside one.

**Why /run/lock:** the runs are different users, and a service's `/tmp` can be private
(`PrivateTmp`), while `/run/lock` is one sticky world-writable directory per host. The file is
opened without `O_CREAT` first, because `fs.protected_regular` refuses `O_CREAT` on another user's
file there, and it is made `0644` so every user can open it to lock it.

**Why session-scoped and autouse:** pytest sets up session fixtures before function ones and tears
them down in reverse, so a session fixture that brings the stack up (#15) runs inside the lock and
its `down` finishes before the lock is released.

## 2026-11-01 · The integration suite brings its own Compose stack up (#15)

**Decision:** an `integration`-marked test pulls in a session fixture (`compose_stack` in
`tests/conftest.py`) that runs `docker compose up -d --wait` inside the #25 host lock. A stack
already running (the demo box) is reused and left running. A stack the run started is taken down
afterwards, and also when `up` fails or times out. The Collector runs as container root
(`user: "0:0"`) so it can write the bind-mounted `demo/replay/raw` capture directory, and the Loki
OTLP probe POSTs an empty batch where it used to send a GET.

**Why the suite starts the stack:** the heavy gate runs `uv run pytest -m integration` on a fresh
tree with nothing running, so every probe waited out its 90-second timeout. Starting the stack in
the suite makes that command complete on its own, and a missing or broken `docker` fails at once
with the `docker compose` error.

**Why tear down after a failed `up`:** a half-started stack keeps its published host ports after
the run releases the lock. It then breaks the next run on the host, which could be another user's
or the gate's. Seen on 2026-11-01, when another project's container held host port 3000.

**Why root for the Collector:** under the gate host's rootless podman, the image's uid 10001 maps to
a subordinate uid that cannot write a directory the host user owns, so the Collector crash-looped
on its file exporter. Container root maps back to the host user there.

**Why POST for the Loki probe:** Loki answers a GET on its POST-only `/otlp/v1/logs` with 405 or
404, depending on the route order it picks at startup. About one cold start in three gave 404. An
empty POST always reaches the handler, which answers 422.
