# ABOUTME: Verifies container healthchecks, resource limits, and Grafana's health-gated start order.
# ABOUTME: Loki is distroless (no shell/wget) so it carries no in-container healthcheck by design.
import json
import subprocess

from conftest import REPO_ROOT, wait_until

COMPOSE_BASE = [
    "docker", "compose", "--project-directory", ".", "-f", "compose/docker-compose.yml",
]
ALL_SERVICES = {"prometheus", "loki", "jaeger", "grafana"}
# Loki ships distroless — no shell, wget, or busybox — so it cannot run an HTTP healthcheck.
HEALTHCHECKED = {"prometheus", "jaeger", "grafana"}


def _compose_services():
    r = subprocess.run([*COMPOSE_BASE, "config", "--format", "json"],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["services"]


def _inspect(container, fmt):
    r = subprocess.run(["docker", "inspect", "--format", fmt, container],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def test_grafana_start_order_is_health_gated():
    deps = _compose_services()["grafana"]["depends_on"]
    assert deps["prometheus"]["condition"] == "service_healthy"
    assert deps["jaeger"]["condition"] == "service_healthy"
    # Loki has no healthcheck (distroless), so it is gated on start, not health.
    assert deps["loki"]["condition"] == "service_started"


def test_healthchecked_containers_report_healthy():
    for name in sorted(HEALTHCHECKED):
        container = f"occ-{name}"

        def healthy(c=container):
            return _inspect(c, "{{.State.Health.Status}}") == "healthy"

        assert wait_until(healthy, what=f"{name} container healthy")


def test_loki_runs_without_a_healthcheck():
    assert _inspect("occ-loki", "{{.State.Status}}") == "running"
    assert _inspect("occ-loki", "{{if .State.Health}}has{{else}}none{{end}}") == "none"


def test_all_containers_have_resource_limits():
    for name in sorted(ALL_SERVICES):
        container = f"occ-{name}"
        mem = _inspect(container, "{{.HostConfig.Memory}}")
        cpus = _inspect(container, "{{.HostConfig.NanoCpus}}")
        assert mem and int(mem) > 0, f"{name} has no memory limit"
        assert cpus and int(cpus) > 0, f"{name} has no cpu limit"
