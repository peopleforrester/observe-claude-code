# ABOUTME: Validates the Compose file parses and resolves via `docker compose config`.
# ABOUTME: First gate of the Phase 1 stack — a malformed compose file fails fast here.
import subprocess

from conftest import REPO_ROOT

COMPOSE_BASE = [
    "docker", "compose",
    "--project-directory", ".",
    "-f", "compose/docker-compose.yml",
]


def test_compose_config_is_valid():
    result = subprocess.run(
        [*COMPOSE_BASE, "config"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`docker compose config` failed (exit {result.returncode}):\n{result.stderr}"
    )


def test_compose_defines_expected_backend_services():
    result = subprocess.run(
        [*COMPOSE_BASE, "config", "--services"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    services = set(result.stdout.split())
    expected = {"prometheus", "loki", "jaeger", "grafana", "collector"}
    missing = expected - services
    assert not missing, f"compose is missing services: {sorted(missing)}"
