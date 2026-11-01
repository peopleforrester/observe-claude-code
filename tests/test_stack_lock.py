# ABOUTME: Offline checks that concurrent integration runs on one host cannot collide (#25, #26).
# ABOUTME: Covers the host lock, the OCC_*_PORT overrides, and moving off host ports already taken.
import os
import shutil
import socket
import stat
import subprocess
import sys
import textwrap

import pytest

import conftest
from conftest import HOST_PORT_DEFAULTS, REPO_ROOT, host_lock

PORT_VARS = {
    "OCC_PROMETHEUS_PORT": ("PROMETHEUS_URL", 19090),
    "OCC_LOKI_PORT": ("LOKI_URL", 13100),
    "OCC_JAEGER_UI_PORT": ("JAEGER_UI_URL", 26686),
    "OCC_GRAFANA_PORT": ("GRAFANA_URL", 13000),
    "OCC_OTLP_HTTP_PORT": ("COLLECTOR_OTLP_HTTP", 14318),
    "OCC_COLLECTOR_HEALTH_PORT": ("COLLECTOR_HEALTH_URL", 23133),
}


def test_second_holder_times_out_while_the_lock_is_held(tmp_path):
    lock = tmp_path / "stack.lock"
    with host_lock(lock, timeout=1):
        with pytest.raises(TimeoutError, match="another integration run on this host"):
            with host_lock(lock, timeout=0.3, interval=0.1):
                pass


def test_lock_is_free_again_after_release(tmp_path):
    lock = tmp_path / "stack.lock"
    with host_lock(lock, timeout=1):
        pass
    with host_lock(lock, timeout=0.3, interval=0.1):
        pass


def test_lock_file_is_readable_by_other_users_despite_the_umask(tmp_path):
    lock = tmp_path / "stack.lock"
    old = os.umask(0o077)
    try:
        with host_lock(lock, timeout=1):
            pass
    finally:
        os.umask(old)
    assert stat.S_IMODE(lock.stat().st_mode) == 0o644


def test_missing_lock_directory_names_the_override(tmp_path):
    with pytest.raises(RuntimeError, match="OCC_STACK_LOCK"):
        with host_lock(tmp_path / "missing" / "stack.lock", timeout=1):
            pass


LOCK_SUITE = """
    import pytest

    @pytest.mark.integration
    def test_needs_stack():
        pass

    def test_offline():
        pass
"""


def _run_suite_copy(tmp_path, lock, *pytest_args, suite=LOCK_SUITE, env=None):
    """Run a throwaway suite under a copy of tests/conftest.py, with `lock` as the host lock."""
    shutil.copy(REPO_ROOT / "tests" / "conftest.py", tmp_path / "conftest.py")
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers =\n    integration: live stack\n")
    (tmp_path / "test_suite.py").write_text(textwrap.dedent(suite))
    env = {**(os.environ if env is None else env),
           "OCC_STACK_LOCK": str(lock), "OCC_STACK_LOCK_TIMEOUT": "0.5"}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *pytest_args],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )


def test_integration_run_waits_for_the_run_holding_the_stack(tmp_path):
    lock = tmp_path / "stack.lock"
    with host_lock(lock, timeout=1):
        result = _run_suite_copy(tmp_path, lock, "-m", "integration")
    assert result.returncode != 0, result.stdout
    assert "another integration run on this host still holds the Compose stack" in result.stdout


def test_offline_run_ignores_the_stack_lock(tmp_path):
    lock = tmp_path / "stack.lock"
    with host_lock(lock, timeout=1):
        result = _run_suite_copy(tmp_path, lock, "-m", "not integration")
    assert result.returncode == 0, result.stdout + result.stderr


def test_service_urls_follow_the_port_overrides():
    env = {**os.environ, **{var: str(port) for var, (_, port) in PORT_VARS.items()}}
    names = ", ".join(name for name, _ in PORT_VARS.values())
    result = subprocess.run(
        [sys.executable, "-c", f"from conftest import {names}; print({names}, sep='\\n')"],
        cwd=REPO_ROOT / "tests", env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [f"http://localhost:{port}" for _, port in PORT_VARS.values()]


def _listener():
    """A socket listening on 0.0.0.0, as another project's published container port would."""
    sock = socket.socket()
    sock.bind(("0.0.0.0", 0))
    sock.listen()
    return sock


def test_a_port_another_listener_holds_is_taken():
    with _listener() as held:
        port = held.getsockname()[1]
        assert not conftest._port_is_free(port)
    assert conftest._port_is_free(port)


def test_only_taken_defaults_move_and_each_to_its_own_free_port(monkeypatch):
    taken = {3000, 9090, 3100}
    monkeypatch.setattr(conftest, "_port_is_free", lambda port: port not in taken)
    moves = conftest._free_port_moves({})
    assert set(moves) == {"OCC_GRAFANA_PORT", "OCC_PROMETHEUS_PORT", "OCC_LOKI_PORT"}
    assert len(set(moves.values())) == len(moves)
    assert not taken & set(moves.values())
    assert all(conftest._port_is_free(port) for port in moves.values())


def test_a_port_the_caller_set_is_kept_even_when_taken(monkeypatch):
    monkeypatch.setattr(conftest, "_port_is_free", lambda port: False)
    moves = conftest._free_port_moves({"OCC_GRAFANA_PORT": "3000"})
    assert "OCC_GRAFANA_PORT" not in moves
    assert set(moves) == set(HOST_PORT_DEFAULTS) - {"OCC_GRAFANA_PORT"}


# Run under a fake `docker` whose `compose ps -a -q` prints CONTAINERS; Grafana's 3000 is taken.
MOVE_SUITE = """
    import os

    import pytest

    import conftest
    from conftest import GRAFANA_PORT, GRAFANA_URL, PROMETHEUS_URL

    conftest._port_is_free = lambda port: port != 3000

    @pytest.mark.integration
    def test_endpoints():
        print("GRAFANA", GRAFANA_PORT, GRAFANA_URL, os.environ.get("OCC_GRAFANA_PORT"))
        print("PROMETHEUS", PROMETHEUS_URL, os.environ.get("OCC_PROMETHEUS_PORT"))
"""


def _run_move_suite(tmp_path, containers):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(f"#!/bin/sh\nprintf '%s' '{containers}'\n")
    docker.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in HOST_PORT_DEFAULTS}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    result = _run_suite_copy(tmp_path, tmp_path / "stack.lock", "-s", "-m", "integration",
                             suite=MOVE_SUITE, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    lines = {line.split()[0]: line.split()[1:] for line in result.stdout.splitlines()
             if line.startswith(("GRAFANA ", "PROMETHEUS "))}
    return result.stdout, lines


def test_run_starting_its_own_stack_moves_a_taken_port_for_compose_and_the_tests(tmp_path):
    stdout, lines = _run_move_suite(tmp_path, containers="")
    port, url, exported = lines["GRAFANA"]
    assert port != "3000"
    assert url == f"http://localhost:{port}"
    assert exported == port  # what docker compose reads
    assert lines["PROMETHEUS"] == ["http://localhost:9090", "None"]
    assert f"OCC_GRAFANA_PORT={port}: default host port 3000 was taken" in stdout


def test_run_reusing_a_running_stack_keeps_its_ports(tmp_path):
    stdout, lines = _run_move_suite(tmp_path, containers="0123456789ab")
    assert lines["GRAFANA"] == ["3000", "http://localhost:3000", "None"]
    assert "was taken" not in stdout
