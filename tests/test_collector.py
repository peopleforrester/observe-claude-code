# ABOUTME: Verifies the OTel Collector is live, healthy, and accepting OTLP on the ingress ports.
# ABOUTME: The round-trip (OTLP in -> backends) is covered by test_roundtrip.
import socket

from conftest import COLLECTOR_HEALTH_URL, COLLECTOR_OTLP_HTTP, wait_until


def _port_open(host, port):
    with socket.socket() as sock:
        sock.settimeout(2)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


def test_collector_health_extension_ok(http):
    def healthy():
        return http.get(COLLECTOR_HEALTH_URL).status_code == 200

    assert wait_until(healthy, what="Collector health_check :13133")


def test_collector_otlp_grpc_port_open():
    assert wait_until(lambda: _port_open("localhost", 4317), what="Collector OTLP gRPC :4317")


def test_collector_otlp_http_accepts_traces(http):
    wait_until(lambda: _port_open("localhost", 4318), what="Collector OTLP HTTP :4318")
    r = http.post(f"{COLLECTOR_OTLP_HTTP}/v1/traces", json={"resourceSpans": []})
    assert r.status_code == 200, f"Collector did not accept OTLP traces: {r.status_code} {r.text}"
