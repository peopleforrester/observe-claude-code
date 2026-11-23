# ABOUTME: Offline checks that the integration suite brings its own Compose stack up and tears
# ABOUTME: down only a stack it started, with a Collector user that can write the capture (#15).
import os
import subprocess

import pytest

from conftest import HOST_PORT_DEFAULTS, _collector_ids, compose_up
from test_stack_lock import _run_suite_copy


class FakeCompose:
    """Records `docker compose` calls and answers `up` with a canned result."""

    def __init__(self, *, up_returncode=0, up_raises=None):
        self.calls = []
        self.up_returncode = up_returncode
        self.up_raises = up_raises

    def __call__(self, *args, timeout=120):
        self.calls.append(args[0])
        if args[0] == "up":
            if self.up_raises:
                raise self.up_raises
            stderr = "bind: address already in use"
            return subprocess.CompletedProcess(args, self.up_returncode, "", stderr)
        return subprocess.CompletedProcess(args, 0, "", "")


def test_a_stack_started_here_is_taken_down_after_the_run():
    compose = FakeCompose()
    with compose_up(started_here=True, compose=compose):
        assert compose.calls == ["up"]
    assert compose.calls == ["up", "down"]


def test_a_stack_already_running_is_reused_and_left_running():
    compose = FakeCompose()
    with compose_up(started_here=False, compose=compose):
        pass
    assert compose.calls == ["up"]


def test_a_failed_up_takes_down_the_half_started_stack():
    compose = FakeCompose(up_returncode=1)
    with pytest.raises(AssertionError, match="address already in use"):
        with compose_up(started_here=True, compose=compose):
            pass
    assert compose.calls == ["up", "down"]


def test_a_timed_out_up_takes_down_the_half_started_stack():
    compose = FakeCompose(up_raises=subprocess.TimeoutExpired("docker compose up", 600))
    with pytest.raises(subprocess.TimeoutExpired):
        with compose_up(started_here=True, compose=compose):
            pass
    assert compose.calls == ["up", "down"]


def test_a_failed_up_leaves_a_stack_it_did_not_start_running():
    compose = FakeCompose(up_returncode=1)
    with pytest.raises(AssertionError):
        with compose_up(started_here=False, compose=compose):
            pass
    assert compose.calls == ["up"]


def test_a_rootless_engine_runs_the_collector_as_container_root():
    assert _collector_ids({}, rootless=True, uid=1000, gid=1001) == {"OCC_UID": "0", "OCC_GID": "0"}


def test_a_rootful_engine_runs_the_collector_as_the_running_user():
    ids = _collector_ids({}, rootless=False, uid=1000, gid=1001)
    assert ids == {"OCC_UID": "1000", "OCC_GID": "1001"}


@pytest.mark.parametrize("env", [{"OCC_UID": "1234"}, {"OCC_GID": "1234"}])
def test_collector_ids_the_caller_set_are_kept(env):
    assert _collector_ids(env, rootless=True, uid=1000, gid=1001) == {}


WIRING_SUITE = """
    import os

    import pytest

    @pytest.mark.integration
    def test_first():
        print("OCC_UID", os.environ.get("OCC_UID"), os.environ.get("OCC_GID"))

    @pytest.mark.integration
    def test_second():
        pass

    def test_offline():
        pass
"""


def _run_wiring_suite(tmp_path, *, containers, security_options, pytest_args=("-m", "integration")):
    """Run a throwaway suite under a fake `docker` that logs each call to docker.log."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "docker.log"
    docker = bin_dir / "docker"
    docker.write_text(
        "#!/bin/sh\n"
        f"echo \"$*\" >> '{log}'\n"
        "case \"$*\" in\n"
        f"  info*) printf '%s' '{security_options}' ;;\n"
        f"  *' ps '*) printf '%s' '{containers}' ;;\n"
        "esac\n"
    )
    docker.chmod(0o755)
    dropped = {"OCC_UID", "OCC_GID", *HOST_PORT_DEFAULTS}
    env = {k: v for k, v in os.environ.items() if k not in dropped}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    result = _run_suite_copy(tmp_path, tmp_path / "stack.lock", "-s", *pytest_args,
                             suite=WIRING_SUITE, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = log.read_text().splitlines() if log.exists() else []
    # The compose subcommand follows the `-f compose/docker-compose.yml` arguments.
    verbs = [c.split()[0] if c.startswith("info") else c.split()[5] for c in calls]
    return result.stdout, verbs


def test_integration_run_starts_the_stack_once_and_takes_it_down(tmp_path):
    stdout, verbs = _run_wiring_suite(
        tmp_path, containers="", security_options='["name=seccomp","name=rootless"]',
    )
    assert verbs == ["ps", "info", "up", "down"]
    assert "OCC_UID 0 0" in stdout
    assert (tmp_path.parent / "demo" / "replay" / "raw").is_dir()


def test_integration_run_reuses_a_running_stack_and_leaves_it_up(tmp_path):
    stdout, verbs = _run_wiring_suite(
        tmp_path, containers="0123456789ab", security_options='["name=rootless"]',
    )
    assert verbs == ["ps", "up"]
    assert "OCC_UID None None" in stdout


def test_offline_run_does_not_touch_docker(tmp_path):
    _, verbs = _run_wiring_suite(
        tmp_path, containers="", security_options="", pytest_args=("-m", "not integration"),
    )
    assert verbs == []
