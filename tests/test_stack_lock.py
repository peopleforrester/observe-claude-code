# ABOUTME: Offline checks that concurrent integration runs on one host cannot collide (#25).
# ABOUTME: Covers the host lock that serialises runs and the OCC_*_PORT host-port overrides.
import os
import shutil
import stat
import subprocess
import sys
import textwrap

import pytest

from conftest import REPO_ROOT, host_lock

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


def _run_suite_copy(tmp_path, lock, *pytest_args):
    """Run a throwaway suite under a copy of tests/conftest.py, with `lock` as the host lock."""
    shutil.copy(REPO_ROOT / "tests" / "conftest.py", tmp_path / "conftest.py")
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers =\n    integration: live stack\n")
    (tmp_path / "test_suite.py").write_text(textwrap.dedent("""
        import pytest

        @pytest.mark.integration
        def test_needs_stack():
            pass

        def test_offline():
            pass
    """))
    env = {**os.environ, "OCC_STACK_LOCK": str(lock), "OCC_STACK_LOCK_TIMEOUT": "0.5"}
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
