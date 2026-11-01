# ABOUTME: Shared pytest fixtures and a polling helper for the live-stack integration tests.
# ABOUTME: Integration tests bring the Compose stack up themselves and probe it on localhost.
import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Default poll timeout for readiness checks; lower it (e.g. OCC_WAIT_TIMEOUT=6) to
# confirm a red test quickly before the service is up.
DEFAULT_WAIT_TIMEOUT = float(os.environ.get("OCC_WAIT_TIMEOUT", "90"))

# Service endpoints as exposed on the VPS host (published compose ports).
PROMETHEUS_URL = "http://localhost:9090"
LOKI_URL = "http://localhost:3100"
JAEGER_UI_URL = "http://localhost:16686"
GRAFANA_URL = "http://localhost:3000"
# The Collector owns the OTLP ingress ports and exposes a health_check extension.
COLLECTOR_OTLP_HTTP = "http://localhost:4318"
COLLECTOR_HEALTH_URL = "http://localhost:13133"


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


COMPOSE_BASE = [
    "docker", "compose", "--project-directory", ".", "-f", "compose/docker-compose.yml",
]
# Ceiling for `up --wait`: image pulls on a cold host plus the health-gated start order.
COMPOSE_UP_TIMEOUT = 600


def _compose(*args, timeout=120):
    return subprocess.run([*COMPOSE_BASE, *args], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=timeout)


@pytest.fixture(scope="session")
def compose_stack():
    """Bring the Compose stack up for the integration suite; tear down only what it started.

    `up -d --wait` is idempotent, so a stack that is already running (the demo box) is
    reused and left running afterwards.
    """
    before = _compose("ps", "-a", "-q")
    assert before.returncode == 0, f"`docker compose ps` failed:\n{before.stderr}"
    started_here = not before.stdout.strip()
    up = _compose("up", "-d", "--wait", timeout=COMPOSE_UP_TIMEOUT)
    assert up.returncode == 0, f"`docker compose up -d --wait` failed:\n{up.stderr}"
    yield
    if started_here:
        _compose("down")


@pytest.fixture(autouse=True)
def _integration_needs_stack(request):
    """Every `integration`-marked test runs against the live stack."""
    if request.node.get_closest_marker("integration"):
        request.getfixturevalue("compose_stack")


@pytest.fixture(scope="session")
def http():
    """A shared HTTP client with a short timeout for probing services."""
    with httpx.Client(timeout=5.0) as client:
        yield client
