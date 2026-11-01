# ABOUTME: Offline unit tests for the trace-to-prompt join over a capture and its transcript.
# ABOUTME: Covers the parentUuid walk, session matching, trace filtering, and the CLI's failures.
import importlib.util
import json
import sys

import pytest

from conftest import REPO_ROOT

JOIN_PATH = REPO_ROOT / "demo" / "replay" / "join.py"
SAMPLE_FILE = REPO_ROOT / "demo" / "replay" / "session-sample.jsonl"
SAMPLE_TRANSCRIPT = REPO_ROOT / "demo" / "replay" / "session-sample.transcript.jsonl"
SID = "11111111-1111-4111-8111-111111111111"
TRACE = "aa" * 16


@pytest.fixture
def join(monkeypatch):
    spec = importlib.util.spec_from_file_location("join_unit", JOIN_PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)  # dataclasses resolve their module here
    spec.loader.exec_module(module)
    return module


def _attrs(**kw):
    return [{"key": k, "value": {"stringValue": v}} for k, v in kw.items()]


def _tool_span(tool_use_id, *, trace=TRACE, span_id="bb" * 8, name="claude_code.tool",
               session=SID, tool_name="Edit"):
    attrs = {"tool_name": tool_name, "tool_use_id": tool_use_id}
    if session is not None:
        attrs["session.id"] = session
    return {"traceId": trace, "spanId": span_id, "name": name, "attributes": _attrs(**attrs)}


def _capture(*spans, resource_session=None):
    resource = {"attributes": _attrs(**{"session.id": resource_session})} if resource_session else {}
    return [{"resourceSpans": [{"resource": resource, "scopeSpans": [{"spans": list(spans)}]}]}]


def _entry(kind, uuid, parent, content, session=SID):
    role = "assistant" if kind == "assistant" else "user"
    return {"type": kind, "uuid": uuid, "parentUuid": parent, "sessionId": session,
            "message": {"role": role, "content": content}}


def _tool_use(tool_use_id):
    return [{"type": "tool_use", "id": tool_use_id, "name": "Edit", "input": {}}]


def _tool_result(tool_use_id):
    return [{"type": "tool_result", "tool_use_id": tool_use_id, "content": "ok"}]


def _transcript():
    """Two turns: the second turn's tool_use must resolve to the second prompt, not the first."""
    return [
        _entry("user", "p1", None, "first prompt"),
        _entry("assistant", "a1", "p1", _tool_use("toolu_1")),
        _entry("user", "r1", "a1", _tool_result("toolu_1")),
        _entry("assistant", "a2", "r1", _tool_use("toolu_2")),
        _entry("user", "r2", "a2", _tool_result("toolu_2")),
        _entry("assistant", "t1", "r2", [{"type": "text", "text": "done"}]),
        _entry("user", "p2", "t1", [{"type": "text", "text": "second"},
                                    {"type": "text", "text": "prompt"}]),
        {"type": "attachment", "uuid": "x1", "parentUuid": "p2", "sessionId": SID},
        _entry("assistant", "a3", "x1", _tool_use("toolu_3")),
        # Off-chain bookkeeping that repeats a tool_use block but has no uuid: must be ignored.
        {"type": "api-request-blob", "sessionId": SID, "message": {"content": _tool_use("toolu_x")}},
    ]


def test_tool_use_in_a_later_step_walks_up_past_tool_results_to_its_prompt(join):
    joins = join.join(_capture(_tool_span("toolu_2")), _transcript())
    assert [(j.prompt_uuid, j.prompt) for j in joins] == [("p1", "first prompt")]


def test_second_turn_resolves_to_its_own_prompt_through_an_attachment(join):
    joins = join.join(_capture(_tool_span("toolu_3")), _transcript())
    assert [(j.prompt_uuid, j.prompt) for j in joins] == [("p2", "second\nprompt")]


def test_join_carries_the_span_identity(join):
    (only,) = join.join(_capture(_tool_span("toolu_1", span_id="cc" * 8)), _transcript())
    assert (only.span.trace_id, only.span.span_id, only.span.tool_name) == (TRACE, "cc" * 8, "Edit")
    assert only.span.tool_use_id == "toolu_1"


def test_trace_filter_keeps_only_that_trace(join):
    capture = _capture(_tool_span("toolu_1"), _tool_span("toolu_3", trace="dd" * 16))
    joins = join.join(capture, _transcript(), trace_id="dd" * 16)
    assert [j.span.tool_use_id for j in joins] == ["toolu_3"]


def test_unknown_trace_is_an_error(join):
    with pytest.raises(join.JoinError, match="no claude_code.tool spans"):
        join.join(_capture(_tool_span("toolu_1")), _transcript(), trace_id="ee" * 16)


def test_only_claude_code_tool_spans_with_a_tool_use_id_join(join):
    capture = _capture(
        _tool_span("toolu_1", name="claude_code.tool.execution"),
        {"traceId": TRACE, "spanId": "ff" * 8, "name": "claude_code.tool", "attributes": []},
    )
    with pytest.raises(join.JoinError, match="no claude_code.tool spans"):
        join.join(capture, _transcript())


def test_session_mismatch_is_an_error(join):
    capture = _capture(_tool_span("toolu_1", session="22222222-2222-4222-8222-222222222222"))
    with pytest.raises(join.JoinError, match="is not the transcript's sessionId"):
        join.join(capture, _transcript())


def test_session_id_on_the_resource_is_checked_too(join):
    capture = _capture(_tool_span("toolu_1", session=None), resource_session="other-session")
    with pytest.raises(join.JoinError, match="other-session"):
        join.join(capture, _transcript())


def test_transcript_without_a_session_id_is_an_error(join):
    entries = [{k: v for k, v in e.items() if k != "sessionId"} for e in _transcript()]
    with pytest.raises(join.JoinError, match="no sessionId"):
        join.join(_capture(_tool_span("toolu_1")), entries)


def test_tool_use_missing_from_the_transcript_is_an_error(join):
    with pytest.raises(join.JoinError, match="toolu_x has no tool_use block"):
        join.join(_capture(_tool_span("toolu_x")), _transcript())


def test_broken_parent_chain_is_an_error(join):
    entries = [e for e in _transcript() if e.get("uuid") != "r1"]
    with pytest.raises(join.JoinError, match="parentUuid r1 is missing"):
        join.join(_capture(_tool_span("toolu_2")), entries)


def test_parent_cycle_is_an_error(join):
    entries = [
        _entry("assistant", "a1", "r1", _tool_use("toolu_1")),
        _entry("user", "r1", "a1", _tool_result("toolu_1")),
    ]
    with pytest.raises(join.JoinError, match="cycle"):
        join.join(_capture(_tool_span("toolu_1")), entries)


def test_chain_without_a_prompt_is_an_error(join):
    entries = [_entry("assistant", "a1", None, _tool_use("toolu_1"))]
    with pytest.raises(join.JoinError, match="without finding a user prompt"):
        join.join(_capture(_tool_span("toolu_1")), entries)


def test_transcript_path_pairs_with_the_capture_name(join, tmp_path):
    assert join.transcript_path_for(tmp_path / "session-20261101-120000.jsonl") == (
        tmp_path / "session-20261101-120000.transcript.jsonl"
    )
    assert join.transcript_path_for(SAMPLE_FILE) == SAMPLE_TRANSCRIPT


def test_render_groups_spans_under_their_trace_then_prints_the_prompt(join):
    joins = join.join(_capture(_tool_span("toolu_1"), _tool_span("toolu_2")), _transcript())
    lines = join.render(joins).splitlines()
    assert lines[0] == f"trace {TRACE}"
    assert sum("-> prompt p1" in ln for ln in lines) == 2
    assert lines[-2:] == ["  prompt p1:", "    first prompt"]


def test_committed_sample_pair_joins_every_tool_span(join):
    capture = join.load_jsonl(SAMPLE_FILE)
    joins = join.join(capture, join.load_jsonl(SAMPLE_TRANSCRIPT))
    assert len(joins) == len(list(join.tool_spans(capture))) >= 2
    assert len({j.prompt_uuid for j in joins}) == 1, "the sample's tool calls share one prompt"
    assert "mcp__prod-api__deploy" in {j.span.tool_name for j in joins}, (
        "the sample should show the denied deploy joining back to its prompt"
    )


def test_main_prints_the_join_for_the_committed_sample(join, capsys):
    join.main(["--capture", str(SAMPLE_FILE)])
    out = capsys.readouterr().out
    assert out.startswith("trace 33333333333333333333333333333333")
    assert "deploy" in out


def test_main_exits_on_a_missing_transcript(join, tmp_path):
    capture = tmp_path / "session-x.jsonl"
    capture.write_text(json.dumps(_capture(_tool_span("toolu_1"))[0]) + "\n")
    with pytest.raises(SystemExit, match="transcript file not found: .*session-x.transcript.jsonl"):
        join.main(["--capture", str(capture)])


def test_main_exits_on_a_missing_capture(join, tmp_path):
    with pytest.raises(SystemExit, match="capture file not found"):
        join.main(["--capture", str(tmp_path / "nope.jsonl")])


def test_main_exits_when_the_join_fails(join, tmp_path):
    capture = tmp_path / "c.jsonl"
    capture.write_text(json.dumps(_capture(_tool_span("toolu_x"))[0]) + "\n")
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(json.dumps(e) for e in _transcript()) + "\n")
    with pytest.raises(SystemExit, match="join failed: tool_use_id toolu_x"):
        join.main(["--capture", str(capture), "--transcript", str(transcript)])
