# ABOUTME: Checks a real captured Claude Code session carries what join.py reads on its tool spans.
# ABOUTME: Needs a capture from demo/replay/capture-session.sh (gitignored), so it runs with -m integration.
import importlib.util
import os
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT

pytestmark = pytest.mark.integration

JOIN_PATH = REPO_ROOT / "demo" / "replay" / "join.py"
RAW_DIR = REPO_ROOT / "demo" / "replay" / "raw"
# The resource service.name Claude Code exports under; the committed synthetic sample uses another.
CLAUDE_CODE_SERVICE = "claude-code"


@pytest.fixture
def join(monkeypatch):
    spec = importlib.util.spec_from_file_location("join_real_capture", JOIN_PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)  # dataclasses resolve their module here
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def capture():
    """The real capture to check: OCC_CAPTURE if set, else the newest snapshot capture-session.sh wrote."""
    if os.environ.get("OCC_CAPTURE"):
        path = Path(os.environ["OCC_CAPTURE"])
        assert path.is_file(), f"OCC_CAPTURE names no file: {path}"
        return path
    snapshots = sorted(p for p in RAW_DIR.glob("session-*.jsonl") if ".transcript." not in p.name)
    assert snapshots, (
        f"no real capture under {RAW_DIR}: run `bash demo/replay/capture-session.sh` against the "
        "live stack first, or set OCC_CAPTURE to a capture it wrote"
    )
    return snapshots[-1]  # session-<YYYYmmdd-HHMMSS>.jsonl sorts by time


def _claude_code_tool_spans(join, records):
    """Yield (resource attributes, span attributes, span) for each claude_code.tool span Claude Code sent."""
    for record in records:
        for resource_spans in record.get("resourceSpans", []):
            resource_attrs = join.attributes(resource_spans.get("resource", {}))
            if resource_attrs.get("service.name") != CLAUDE_CODE_SERVICE:
                continue
            for scope_spans in resource_spans.get("scopeSpans", []):
                for span in scope_spans.get("spans", []):
                    if span.get("name") == "claude_code.tool":
                        yield resource_attrs, join.attributes(span), span


def test_real_tool_spans_carry_tool_use_id_and_session_id_where_join_reads_them(join, capture):
    """Every real claude_code.tool span has tool_use_id on the span and session.id on it or its resource.

    join.py reads tool_use_id from the span's attributes only, and session.id from the span's
    attributes or else the resource's; a span without tool_use_id is skipped without a word.
    """
    records = join.load_jsonl(capture)
    real = list(_claude_code_tool_spans(join, records))
    assert real, (
        f"{capture.name} has no claude_code.tool spans from service.name={CLAUDE_CODE_SERVICE}: "
        "is it a real session captured with traces on (env/claude-code.env)?"
    )

    no_tool_use_id = [(span.get("spanId"), attrs.get("tool_name")) for _, attrs, span in real
                      if not attrs.get("tool_use_id")]
    assert not no_tool_use_id, (
        f"claude_code.tool spans with no tool_use_id span attribute (span id, tool): {no_tool_use_id}"
    )
    no_session = [(span.get("spanId"), attrs.get("tool_name")) for resource, attrs, span in real
                  if not (attrs.get("session.id") or resource.get("session.id"))]
    assert not no_session, (
        "claude_code.tool spans with session.id neither on the span nor on its resource "
        f"(span id, tool): {no_session}"
    )

    # join.py itself picks each of them up, with the same tool_use_id and a session.id.
    read = {(s.trace_id, s.span_id): s for s in join.tool_spans(records)}
    for _, attrs, span in real:
        key = (span.get("traceId", ""), span.get("spanId", ""))
        assert key in read, f"join.py did not read claude_code.tool span {key[1]}"
        assert read[key].tool_use_id == str(attrs["tool_use_id"])
        assert read[key].session_id, f"join.py read no session.id for span {key[1]}"


def test_real_capture_joins_every_tool_span_to_its_transcript(join, capture):
    """The span values are the transcript's: session.id is its sessionId, tool_use_id a tool_use block's id."""
    transcript = join.transcript_path_for(capture)
    assert transcript.is_file(), (
        f"no transcript beside {capture.name}: capture-session.sh writes {transcript.name} with it"
    )
    records = join.load_jsonl(capture)
    joins = join.join(records, join.load_jsonl(transcript))
    real = {(span.get("traceId", ""), span.get("spanId", ""))
            for _, _, span in _claude_code_tool_spans(join, records)}
    assert real, f"{capture.name} has no claude_code.tool spans from service.name={CLAUDE_CODE_SERVICE}"
    joined = {(j.span.trace_id, j.span.span_id) for j in joins}
    assert real <= joined, f"real tool spans that did not join: {sorted(real - joined)}"
