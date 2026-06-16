# ABOUTME: Verifies Prometheus is healthy, has the OTLP receiver enabled, and loads the OTLP config.
# ABOUTME: Guards the metrics backend of the Phase 1 stack.
import httpx

from conftest import PROMETHEUS_URL, wait_until


def test_prometheus_is_ready(http):
    def ready():
        r = http.get(f"{PROMETHEUS_URL}/-/ready")
        return r.status_code == 200

    assert wait_until(ready, what="Prometheus /-/ready")


def test_otlp_receiver_is_enabled(http):
    # The OTLP write endpoint is POST-only. A GET returns 405 when the receiver is
    # mounted (--web.enable-otlp-receiver), and 404 when it is not.
    wait_until(
        lambda: http.get(f"{PROMETHEUS_URL}/-/ready").status_code == 200,
        what="Prometheus ready",
    )
    r = http.get(f"{PROMETHEUS_URL}/api/v1/otlp/v1/metrics")
    assert r.status_code != 404, "OTLP receiver not mounted — is --web.enable-otlp-receiver set?"
    assert r.status_code == 405, f"expected 405 from OTLP endpoint GET, got {r.status_code}"


def test_otlp_promotes_resource_attributes(http):
    # The running config should promote the demo's role/team/cost attributes to labels.
    wait_until(
        lambda: http.get(f"{PROMETHEUS_URL}/-/ready").status_code == 200,
        what="Prometheus ready",
    )
    r = http.get(f"{PROMETHEUS_URL}/api/v1/status/config")
    r.raise_for_status()
    config_yaml = r.json()["data"]["yaml"]
    for attr in ("role", "team.id", "cost_center"):
        assert attr in config_yaml, f"{attr!r} missing from promote_resource_attributes"
