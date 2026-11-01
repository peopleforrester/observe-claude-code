# ABOUTME: Shared pytest fixtures and a polling helper for the live-stack integration tests.
# ABOUTME: Tests run on the VPS and probe each service on localhost.
import contextlib
import errno
import fcntl
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Default poll timeout for readiness checks; lower it (e.g. OCC_WAIT_TIMEOUT=6) to
# confirm a red test quickly before the service is up.
DEFAULT_WAIT_TIMEOUT = float(os.environ.get("OCC_WAIT_TIMEOUT", "90"))


# Each published host port's OCC_*_PORT variable (compose/docker-compose.yml reads the same one)
# and its default, the service's own port.
HOST_PORT_DEFAULTS = {
    "OCC_PROMETHEUS_PORT": 9090,
    "OCC_LOKI_PORT": 3100,
    "OCC_JAEGER_UI_PORT": 16686,
    "OCC_GRAFANA_PORT": 3000,
    # The Collector owns the OTLP ingress ports and exposes a health_check extension.
    "OCC_OTLP_GRPC_PORT": 4317,
    "OCC_OTLP_HTTP_PORT": 4318,
    "OCC_COLLECTOR_HEALTH_PORT": 13133,
}


def _endpoints(env):
    """The host ports and service URLs the integration tests probe, as `env` publishes them."""
    port = {var: int(env.get(var, default)) for var, default in HOST_PORT_DEFAULTS.items()}
    return {
        "PROMETHEUS_PORT": port["OCC_PROMETHEUS_PORT"],
        "LOKI_PORT": port["OCC_LOKI_PORT"],
        "JAEGER_UI_PORT": port["OCC_JAEGER_UI_PORT"],
        "GRAFANA_PORT": port["OCC_GRAFANA_PORT"],
        "OTLP_GRPC_PORT": port["OCC_OTLP_GRPC_PORT"],
        "OTLP_HTTP_PORT": port["OCC_OTLP_HTTP_PORT"],
        "COLLECTOR_HEALTH_PORT": port["OCC_COLLECTOR_HEALTH_PORT"],
        "PROMETHEUS_URL": f"http://localhost:{port['OCC_PROMETHEUS_PORT']}",
        "LOKI_URL": f"http://localhost:{port['OCC_LOKI_PORT']}",
        "JAEGER_UI_URL": f"http://localhost:{port['OCC_JAEGER_UI_PORT']}",
        "GRAFANA_URL": f"http://localhost:{port['OCC_GRAFANA_PORT']}",
        "COLLECTOR_OTLP_HTTP": f"http://localhost:{port['OCC_OTLP_HTTP_PORT']}",
        "COLLECTOR_HEALTH_URL": f"http://localhost:{port['OCC_COLLECTOR_HEALTH_PORT']}",
    }


# Service endpoints as exposed on the host (published compose ports). An integration run that
# starts its own stack may move them onto free ports first; see _publish_on_free_ports.
_ENDPOINTS = _endpoints(os.environ)
PROMETHEUS_PORT = _ENDPOINTS["PROMETHEUS_PORT"]
LOKI_PORT = _ENDPOINTS["LOKI_PORT"]
JAEGER_UI_PORT = _ENDPOINTS["JAEGER_UI_PORT"]
GRAFANA_PORT = _ENDPOINTS["GRAFANA_PORT"]
OTLP_GRPC_PORT = _ENDPOINTS["OTLP_GRPC_PORT"]
OTLP_HTTP_PORT = _ENDPOINTS["OTLP_HTTP_PORT"]
COLLECTOR_HEALTH_PORT = _ENDPOINTS["COLLECTOR_HEALTH_PORT"]

PROMETHEUS_URL = _ENDPOINTS["PROMETHEUS_URL"]
LOKI_URL = _ENDPOINTS["LOKI_URL"]
JAEGER_UI_URL = _ENDPOINTS["JAEGER_UI_URL"]
GRAFANA_URL = _ENDPOINTS["GRAFANA_URL"]
COLLECTOR_OTLP_HTTP = _ENDPOINTS["COLLECTOR_OTLP_HTTP"]
COLLECTOR_HEALTH_URL = _ENDPOINTS["COLLECTOR_HEALTH_URL"]

COMPOSE_BASE = [
    "docker", "compose", "--project-directory", ".", "-f", "compose/docker-compose.yml",
]

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


def _port_is_free(port):
    """Whether a listener could bind 0.0.0.0:`port` now, as Compose's port forwarder does.

    SO_REUSEADDR matches the forwarder's own listener, so a port left in TIME_WAIT by an
    earlier stack still counts as free.
    """
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
            sock.listen()
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
            return False
    return True


def _free_port_moves(env):
    """The OCC_*_PORT values to export so a stack started now publishes only free host ports.

    A variable set in `env` is kept as the caller set it. A free default is kept. A taken one
    (another project's container, on a shared host) moves to a port the kernel reports free.
    """
    moves = {}
    with contextlib.ExitStack() as held:
        for var, default in HOST_PORT_DEFAULTS.items():
            if var in env or _port_is_free(default):
                continue
            # Held open until every port is picked, so no two variables get the same one.
            sock = held.enter_context(socket.socket())
            sock.bind(("0.0.0.0", 0))
            moves[var] = sock.getsockname()[1]
    return moves


def _stack_exists():
    """Whether any container of this Compose project exists on the host, running or not."""
    ps = subprocess.run([*COMPOSE_BASE, "ps", "-a", "-q"], cwd=REPO_ROOT,
                        capture_output=True, text=True, timeout=120)
    assert ps.returncode == 0, f"`docker compose ps` failed:\n{ps.stderr}"
    return bool(ps.stdout.strip())


# The ports this run moved off their defaults, for the terminal summary.
MOVED_HOST_PORTS = {}


def _publish_on_free_ports(modules):
    """Move every taken default host port to a free one, for both Compose and the tests.

    Compose reads the exported OCC_*_PORT variables from this process's environment. Test
    modules imported the endpoint constants by name at collection, before the host lock was
    held; a test reads its module's globals when it runs, so rebinding them here reaches it.
    """
    moves = _free_port_moves(os.environ)
    if not moves:
        return
    os.environ.update({var: str(port) for var, port in moves.items()})
    MOVED_HOST_PORTS.update(moves)
    endpoints = _endpoints(os.environ)
    for module in {sys.modules[__name__], *modules}:
        for name, value in endpoints.items():
            if name in vars(module):
                setattr(module, name, value)


@pytest.fixture(scope="session", autouse=True)
def _integration_host_lock(request):
    """Serialise integration runs on this host for the whole session.

    Session-scoped and autouse, so it is set up before any other session fixture an
    integration test uses (the stack itself) and torn down after them. Inside the lock, a
    run that will start its own stack first moves any taken default host port to a free one;
    a stack that already exists (the demo box) is reused on the ports it publishes.
    """
    if not any(item.get_closest_marker("integration") for item in request.session.items):
        yield
        return
    with host_lock(STACK_LOCK_PATH, timeout=STACK_LOCK_TIMEOUT):
        if not _stack_exists():
            _publish_on_free_ports({item.module for item in request.session.items})
        yield


def pytest_terminal_summary(terminalreporter):
    """Name each host port the run moved, so a failure's URLs can be read against it."""
    for var, port in MOVED_HOST_PORTS.items():
        terminalreporter.write_line(
            f"{var}={port}: default host port {HOST_PORT_DEFAULTS[var]} was taken on this host"
        )
