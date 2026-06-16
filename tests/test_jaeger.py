# ABOUTME: Verifies Jaeger v2 serves its UI and accepts OTLP traces on the published ports.
# ABOUTME: Guards the traces backend; catches the localhost-bind trap that blocks published ports.
import socket

from conftest import JAEGER_UI_URL, wait_until

OTLP_HTTP = "http://localhost:4318"


def _port_open(host, port):
    with socket.socket() as sock:
        sock.settimeout(2)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


def test_jaeger_ui_is_up(http):
    def ok():
        return http.get(f"{JAEGER_UI_URL}/").status_code == 200

    assert wait_until(ok, what="Jaeger UI")


def test_jaeger_otlp_grpc_port_open():
    assert wait_until(lambda: _port_open("localhost", 4317), what="Jaeger OTLP gRPC :4317")


def test_jaeger_otlp_http_accepts_traces(http):
    wait_until(lambda: _port_open("localhost", 4318), what="Jaeger OTLP HTTP :4318")
    # An empty but well-formed OTLP/HTTP traces payload must be accepted (200).
    r = http.post(f"{OTLP_HTTP}/v1/traces", json={"resourceSpans": []})
    assert r.status_code == 200, f"OTLP HTTP traces not accepted: {r.status_code} {r.text}"
