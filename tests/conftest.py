# ABOUTME: Shared pytest fixtures and a polling helper for the live-stack integration tests.
# ABOUTME: Tests run on the VPS and probe each service on localhost.
import os
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
