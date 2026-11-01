# ABOUTME: Offline checks that the integration suite tears down only a Compose stack it started.
# ABOUTME: Drives conftest.compose_up with a fake `docker compose` runner; no Docker needed (#15).
import subprocess

import pytest

from conftest import compose_up


class FakeCompose:
    """Records `docker compose` calls and answers `ps` and `up` with canned results."""

    def __init__(self, *, running=False, up_returncode=0, up_raises=None):
        self.calls = []
        self.running = running
        self.up_returncode = up_returncode
        self.up_raises = up_raises

    def __call__(self, *args, timeout=120):
        self.calls.append(args[0])
        if args[0] == "ps":
            return subprocess.CompletedProcess(args, 0, "abc123\n" if self.running else "", "")
        if args[0] == "up":
            if self.up_raises:
                raise self.up_raises
            stderr = "bind: address already in use"
            return subprocess.CompletedProcess(args, self.up_returncode, "", stderr)
        return subprocess.CompletedProcess(args, 0, "", "")


def test_a_stack_started_here_is_taken_down_after_the_run():
    compose = FakeCompose()
    with compose_up(compose):
        assert compose.calls == ["ps", "up"]
    assert compose.calls == ["ps", "up", "down"]


def test_a_stack_already_running_is_reused_and_left_running():
    compose = FakeCompose(running=True)
    with compose_up(compose):
        pass
    assert compose.calls == ["ps", "up"]


def test_a_failed_up_takes_down_the_half_started_stack():
    compose = FakeCompose(up_returncode=1)
    with pytest.raises(AssertionError, match="address already in use"):
        with compose_up(compose):
            pass
    assert compose.calls == ["ps", "up", "down"]


def test_a_timed_out_up_takes_down_the_half_started_stack():
    compose = FakeCompose(up_raises=subprocess.TimeoutExpired("docker compose up", 600))
    with pytest.raises(subprocess.TimeoutExpired):
        with compose_up(compose):
            pass
    assert compose.calls == ["ps", "up", "down"]


def test_a_failed_up_leaves_a_stack_it_did_not_start_running():
    compose = FakeCompose(running=True, up_returncode=1)
    with pytest.raises(AssertionError):
        with compose_up(compose):
            pass
    assert compose.calls == ["ps", "up"]
