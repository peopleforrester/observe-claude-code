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

## 2026-11-01 · A run that starts its own stack moves off host ports already taken (#26)

**Decision:** option 1 of the three the issue offered. Inside the #25 host lock, and only when no
container of this Compose project exists on the host, `tests/conftest.py` checks each default host
port before the stack starts. A port another listener holds on `0.0.0.0` moves to one the kernel
reports free. The matching `OCC_*_PORT` variable is exported to the process environment, which
`docker compose` inherits, and the endpoint constants (`GRAFANA_URL`, `GRAFANA_PORT` and the rest)
are rebound in `conftest` and in every collected test module. A variable the caller set is used
as set, even when its port is taken, so the failure stays loud. Each moved port is named in the
pytest terminal summary.

**Why not an uncommon port block (option 2):** fixed ports collide with whatever else picks them,
which is the #25 reasoning against a shared default; an uncommon block only makes the collision
rarer. **Why not re-running the gate (option 3):** the issue's own criterion asks for the
collision to stop turning the gate red.

**Why only when no stack exists:** a running stack (the demo box) is reused, as #15 decides, on the
ports it already publishes. Its own containers hold the defaults there, and moving them would make
`up` recreate the demo containers on new ports.

**Why inside the lock and after collection:** the free ports are chosen right before `up`, not up
to 30 minutes earlier while the run waits on the lock. Test modules import the constants by name
at collection, which comes before the lock; a test function reads its module's globals when it
runs, so rebinding them before the first test reaches every test without changing the test files.

**Why the probe uses `SO_REUSEADDR`, bind and listen on `0.0.0.0`:** that is what the Compose port
forwarder (rootlessport or docker-proxy, both Go listeners that set `SO_REUSEADDR`) does, so the
probe agrees with it: a port left in `TIME_WAIT` by an earlier stack is free to both.

## 2026-11-15 · #32's runs fail at the dispatcher's alert read, and question 1578 waits on Chrome (#34)

**Decision:** nothing in this repo changes for the failure. The lock bump #32 asks for lands
through a child of #32 that carries no `dependabot-fix`, and the browser read question 1578 asked
for is not escalated again from this repo until Michael's Chrome with remote debugging (CDP on
127.0.0.1:9222) runs on tanjiro-wsl2.

**The cause:** runs 26138, 26148 and 26257 on #32 each committed a correct `uv.lock` bump, then
ended executor-error with HTTP 403 (`HTTPError: HTTP Error 403: Forbidden`) before any gate ran.
Because #32 carries `dependabot-fix`, the dispatcher reads each listed alert (GET
/repos/peopleforrester/observe-claude-code/dependabot/alerts/N) with the hecatongithub App token,
which has no Dependabot alerts permission, so GitHub refuses the read and the refusal ends the run.
Michael's own token reads the same 19 alerts: all open, none dismissed. No change in this repo
fixes it. Michael granting Dependabot alerts: Read-only on the App and accepting it on the
peopleforrester installation does, because the dispatcher mints its token with the installation's
whole reach. peopleforrester/hecaton#768 asks for the same App change for the heavy gate's token.

**Question 1578:** a run on #32 asked for a browser read of
https://github.com/settings/apps/hecatongithub/permissions, to confirm whether the hecatongithub
App's Dependabot alerts permission reads No access. The answer, word for word:

> Back to the run (hecaton#510): `browser read github.com` was refused by a rule hecaton has decided (hecaton#538), so asking again changes nothing. What to do instead: the elevated tier did not run it: "step 1: precondition: Michael's Chrome with remote debugging (CDP on 127.0.0.1:9222) is not running on tanjiro-wsl2. The wrapper's browser read fails with 'fetch failed', and a curl to :9222/json/version there is refused (exit 7). Re-run this read once that Chrome is up again. Until then the hecaton follow-up can go ahead without it: add 'Dependabot alerts: Read-only' to the hecatongithub App and accept the change on the peopleforrester installation. The 403 from GET /repos/.../dependabot/alerts/N with the App token is already strong evidence that the permission is missing.". The tier found that something the act needs does not hold yet, named above, so it did not run it, and no tier above would. Do not escalate the act again until that holds. If your own work can make it hold (a commit or a fix on your branch, which the dispatcher merges into staging after your run), do that first and put the act in `escalate` in that same report. If it waits on something no run makes happen, such as the dispatcher promoting staging to main, another issue closing or a day, end with a `wait` on it (kind `issue` or `date`, else `recheck`); once it holds, read it back and put the same act in `escalate` with that evidence in its why.

Who decided it, word for word:

> Decided by the coordinator under Michael's standing rules, not by Michael.

**What follows for #32:** a child of #32 with no `dependabot-fix` makes no App-token read, so its
lock bump can pass the gates. #32 itself can close through a run that commits nothing and finds
every criterion met, which ends before the read. A run on #32 that commits anything still fails at
the read until the App has the permission. The fix for the dispatcher is tracked on
peopleforrester/hecaton, filed from #34.
