# ABOUTME: Shared pytest fixtures and a polling helper for the live-stack integration tests.
# ABOUTME: Tests run on the VPS and probe each service on localhost.
import contextlib
import fcntl
import os
import time
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Default poll timeout for readiness checks; lower it (e.g. OCC_WAIT_TIMEOUT=6) to
# confirm a red test quickly before the service is up.
DEFAULT_WAIT_TIMEOUT = float(os.environ.get("OCC_WAIT_TIMEOUT", "90"))


def _host_port(var, default):
    """A published host port: the same OCC_*_PORT variable compose/docker-compose.yml reads."""
    return int(os.environ.get(var, default))


# Service endpoints as exposed on the VPS host (published compose ports).
PROMETHEUS_PORT = _host_port("OCC_PROMETHEUS_PORT", 9090)
LOKI_PORT = _host_port("OCC_LOKI_PORT", 3100)
JAEGER_UI_PORT = _host_port("OCC_JAEGER_UI_PORT", 16686)
GRAFANA_PORT = _host_port("OCC_GRAFANA_PORT", 3000)
# The Collector owns the OTLP ingress ports and exposes a health_check extension.
OTLP_GRPC_PORT = _host_port("OCC_OTLP_GRPC_PORT", 4317)
OTLP_HTTP_PORT = _host_port("OCC_OTLP_HTTP_PORT", 4318)
COLLECTOR_HEALTH_PORT = _host_port("OCC_COLLECTOR_HEALTH_PORT", 13133)

PROMETHEUS_URL = f"http://localhost:{PROMETHEUS_PORT}"
LOKI_URL = f"http://localhost:{LOKI_PORT}"
JAEGER_UI_URL = f"http://localhost:{JAEGER_UI_PORT}"
GRAFANA_URL = f"http://localhost:{GRAFANA_PORT}"
COLLECTOR_OTLP_HTTP = f"http://localhost:{OTLP_HTTP_PORT}"
COLLECTOR_HEALTH_URL = f"http://localhost:{COLLECTOR_HEALTH_PORT}"

# One lock per host serialises integration runs: every run publishes the stack on the same host
# ports, so two at once (two agents, or the gate beside an agent) make one `up` fail. /run/lock is
# shared by every user on the host, unlike a service's private /tmp.
STACK_LOCK_PATH = Path(os.environ.get("OCC_STACK_LOCK", "/run/lock/observe-claude-code-stack.lock"))
# How long a run waits for another run's stack; a fully red run takes about 22 minutes.
STACK_LOCK_TIMEOUT = float(os.environ.get("OCC_STACK_LOCK_TIMEOUT", "1800"))


def wait_until(predicate, *, timeout=DEFAULT_WAIT_TIMEOUT, interval=2.0, what="condition"):
    """Poll `predicate` until it returns a truthy value or the timeout elapses.

    Args:
        predicate: Zero-arg callable; its truthy return value is returned.
        timeout: Seconds to keep trying before giving up.
        interval: Seconds between attempts.
        what: Human-readable description used in the timeout message.

    Returns:
        The first truthy value returned by `predicate`.

    Raises:
        TimeoutError: If the predicate never returns truthy within `timeout`.
    """
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except Exception as exc:  # noqa: BLE001 - surfaced via TimeoutError below
            last_error = exc
        time.sleep(interval)
    suffix = f" (last error: {last_error})" if last_error else ""
    raise TimeoutError(f"Timed out after {timeout:.0f}s waiting for {what}{suffix}")


@pytest.fixture(scope="session")
def http():
    """A shared HTTP client with a short timeout for probing services."""
    with httpx.Client(timeout=5.0) as client:
        yield client


def _open_lock_file(path):
    """Open `path` for flock, creating it readable by every user on the host if missing.

    Opens without O_CREAT first: with fs.protected_regular set, O_CREAT on a file another
    user owns in a sticky world-writable directory (/run/lock, /tmp) is refused.
    """
    while True:
        try:
            return os.open(path, os.O_RDONLY)
        except FileNotFoundError:
            pass
        try:
            fd = os.open(path, os.O_RDONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            continue  # another run created it between the two opens
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"cannot create the integration stack lock {path}: its directory is missing; "
                "point OCC_STACK_LOCK at a directory every user on this host can write"
            ) from exc
        os.fchmod(fd, 0o644)  # the umask must not hide it from other users' runs
        return fd


@contextlib.contextmanager
def host_lock(path, *, timeout, interval=2.0):
    """Hold an exclusive flock on `path` for the duration of the block.

    Raises:
        TimeoutError: If another holder keeps the lock for longer than `timeout` seconds.
    """
    fd = _open_lock_file(path)
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Timed out after {timeout:.0f}s waiting for {path}: another integration "
                        "run on this host still holds the Compose stack"
                    ) from None
                time.sleep(interval)
        yield
    finally:
        os.close(fd)  # closing the descriptor releases the flock


@pytest.fixture(scope="session", autouse=True)
def _integration_host_lock(request):
    """Serialise integration runs on this host for the whole session.

    Session-scoped and autouse, so it is set up before any other session fixture an
    integration test uses (the stack itself) and torn down after them.
    """
    if not any(item.get_closest_marker("integration") for item in request.session.items):
        yield
        return
    with host_lock(STACK_LOCK_PATH, timeout=STACK_LOCK_TIMEOUT):
        yield
