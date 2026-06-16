# ABOUTME: Verifies Grafana is healthy and the three provisioned datasources are connected.
# ABOUTME: This is the Phase 1 done-criteria: Prometheus, Loki, and Jaeger reachable by uid.
import httpx

from conftest import GRAFANA_URL, wait_until

AUTH = ("admin", "admin")
EXPECTED_UIDS = {"prometheus", "loki", "jaeger"}


def test_grafana_is_healthy(http):
    def healthy():
        r = http.get(f"{GRAFANA_URL}/api/health")
        return r.status_code == 200 and r.json().get("database") == "ok"

    assert wait_until(healthy, what="Grafana /api/health")


def test_three_datasources_provisioned(http):
    wait_until(
        lambda: http.get(f"{GRAFANA_URL}/api/health").status_code == 200,
        what="Grafana ready",
    )
    r = http.get(f"{GRAFANA_URL}/api/datasources", auth=AUTH)
    r.raise_for_status()
    uids = {ds["uid"] for ds in r.json()}
    missing = EXPECTED_UIDS - uids
    assert not missing, f"datasources not provisioned: {sorted(missing)}"


def test_each_datasource_is_connected(http):
    wait_until(
        lambda: http.get(f"{GRAFANA_URL}/api/health").status_code == 200,
        what="Grafana ready",
    )
    for uid in sorted(EXPECTED_UIDS):
        def connected(uid=uid):
            r = http.get(f"{GRAFANA_URL}/api/datasources/uid/{uid}/health", auth=AUTH)
            return r.status_code == 200 and r.json().get("status") == "OK"

        assert wait_until(connected, what=f"datasource {uid} health OK")
