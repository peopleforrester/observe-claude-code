# ABOUTME: Offline checks that `netcup` tests run only under `-m netcup`, never in the heavy gate's
# ABOUTME: `-m integration` run or the offline run, and that they still take the host lock (2713).
import os

from conftest import host_lock
from test_stack_lock import _run_suite_copy

SUITE = """
    import pytest

    @pytest.mark.integration
    def test_stack():
        pass

    @pytest.mark.netcup
    def test_canonical():
        print("CANONICAL RAN")

    def test_offline():
        pass
"""


def _selected(tmp_path, *pytest_args):
    result = _run_suite_copy(tmp_path, tmp_path / "stack.lock", "--collect-only", *pytest_args,
                             suite=SUITE)
    assert result.returncode == 0, result.stdout + result.stderr
    return {line.split("::")[1] for line in result.stdout.splitlines() if "::" in line}


def test_the_gate_run_leaves_netcup_tests_out(tmp_path):
    assert _selected(tmp_path, "-m", "integration") == {"test_stack"}


def test_the_offline_run_leaves_netcup_tests_out(tmp_path):
    assert _selected(tmp_path, "-m", "not integration") == {"test_offline"}


def test_a_run_with_no_marker_expression_leaves_netcup_tests_out(tmp_path):
    assert _selected(tmp_path) == {"test_stack", "test_offline"}


def test_the_netcup_run_selects_only_netcup_tests(tmp_path):
    assert _selected(tmp_path, "-m", "netcup") == {"test_canonical"}


def test_the_netcup_run_waits_for_the_run_holding_the_stack(tmp_path):
    lock = tmp_path / "stack.lock"
    with host_lock(lock, timeout=1):
        result = _run_suite_copy(tmp_path, lock, "-m", "netcup", suite=SUITE)
    assert result.returncode != 0, result.stdout
    assert "another integration run on this host still holds the Compose stack" in result.stdout


def test_the_netcup_run_does_not_start_this_checkouts_stack(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "docker.log"
    docker = bin_dir / "docker"
    docker.write_text(f"#!/bin/sh\necho \"$*\" >> '{log}'\n")
    docker.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    result = _run_suite_copy(tmp_path, tmp_path / "stack.lock", "-s", "-m", "netcup",
                             suite=SUITE, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CANONICAL RAN" in result.stdout
    assert not log.exists(), log.read_text()
