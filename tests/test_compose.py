# ABOUTME: Validates the Compose file parses and resolves via `docker compose config`.
# ABOUTME: First gate of the Phase 1 stack — a malformed compose file fails fast here.
import json
import os
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


# Each published host port, its OCC_*_PORT override, and the container port it maps to.
HOST_PORTS = {
    ("prometheus", 9090): "OCC_PROMETHEUS_PORT",
    ("loki", 3100): "OCC_LOKI_PORT",
    ("jaeger", 16686): "OCC_JAEGER_UI_PORT",
    ("grafana", 3000): "OCC_GRAFANA_PORT",
    ("collector", 4317): "OCC_OTLP_GRPC_PORT",
    ("collector", 4318): "OCC_OTLP_HTTP_PORT",
    ("collector", 13133): "OCC_COLLECTOR_HEALTH_PORT",
}


def _published_ports(env):
    result = subprocess.run(
        [*COMPOSE_BASE, "config", "--format", "json"],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    services = json.loads(result.stdout)["services"]
    return {(name, p["target"]): int(p["published"])
            for name, svc in services.items() for p in svc.get("ports", [])}


def test_host_ports_default_to_the_service_ports():
    env = {k: v for k, v in os.environ.items() if k not in HOST_PORTS.values()}
    assert _published_ports(env) == {key: key[1] for key in HOST_PORTS}


def test_each_host_port_reads_its_override():
    """A second stack on the same host can publish elsewhere (#25)."""
    overrides = {var: 20000 + i for i, var in enumerate(HOST_PORTS.values())}
    published = _published_ports({**os.environ, **{k: str(v) for k, v in overrides.items()}})
    assert published == {key: overrides[var] for key, var in HOST_PORTS.items()}
