# ABOUTME: Joins a captured trace back to the prompt that caused it, using the paired transcript.
# ABOUTME: Trace -> claude_code.tool span -> tool_use_id -> transcript tool_use -> parentUuid -> prompt.
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# The transcript beside a capture: session-<stamp>.jsonl -> session-<stamp>.transcript.jsonl.
TRANSCRIPT_SUFFIX = ".transcript.jsonl"


class JoinError(Exception):
    """The capture and transcript do not join; the message says why."""


@dataclass(frozen=True)
class ToolSpan:
    trace_id: str
    span_id: str
    tool_name: str
    tool_use_id: str
    session_id: str | None


@dataclass(frozen=True)
class Join:
    span: ToolSpan
    prompt_uuid: str
    prompt: str


def transcript_path_for(capture):
    """Return the transcript path paired with a capture file by naming convention."""
    capture = Path(capture)
    name = capture.name[: -len(".jsonl")] if capture.name.endswith(".jsonl") else capture.name
    return capture.with_name(name + TRANSCRIPT_SUFFIX)


def load_jsonl(path):
    """Load a JSON-lines file, skipping blank lines."""
    lines = [ln for ln in Path(path).read_text().splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


def any_value(value):
    """Decode an OTLP/JSON AnyValue to a plain Python value (scalars only)."""
    for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if key in value:
            return value[key]
    return None


def attributes(obj):
    """Return an OTLP attribute list as a dict."""
    return {a["key"]: any_value(a.get("value", {})) for a in obj.get("attributes", [])}


def tool_spans(records):
    """Yield every claude_code.tool span in a capture that carries a tool_use_id."""
    for record in records:
        for resource_spans in record.get("resourceSpans", []):
            resource_attrs = attributes(resource_spans.get("resource", {}))
            for scope_spans in resource_spans.get("scopeSpans", []):
                for span in scope_spans.get("spans", []):
                    attrs = attributes(span)
                    tool_use_id = attrs.get("tool_use_id")
                    if not tool_use_id or span.get("name") != "claude_code.tool":
                        continue
                    yield ToolSpan(
                        trace_id=span.get("traceId", ""),
                        span_id=span.get("spanId", ""),
                        tool_name=str(attrs.get("tool_name", "")),
                        tool_use_id=str(tool_use_id),
                        session_id=attrs.get("session.id") or resource_attrs.get("session.id"),
                    )


def is_tool_result(entry):
    content = entry.get("message", {}).get("content")
    return isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "tool_result" for block in content
    )


def prompt_text(entry):
    """Return the text of a typed user prompt (string content or its text blocks)."""
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return content
    return "\n".join(
        block.get("text", "") for block in content or []
        if isinstance(block, dict) and block.get("type") == "text"
    )


class Transcript:
    """Index of one session transcript: entries by uuid, and which entry made each tool_use."""

    def __init__(self, entries):
        self.by_uuid = {}
        self.tool_use_owner = {}
        self.session_ids = set()
        for entry in entries:
            if entry.get("sessionId"):
                self.session_ids.add(entry["sessionId"])
            uuid = entry.get("uuid")
            if not uuid:
                continue  # bookkeeping records (api-request-blob, last-prompt, ...) are off-chain
            self.by_uuid[uuid] = entry
            if entry.get("type") != "assistant":
                continue
            for block in entry.get("message", {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("id"):
                    self.tool_use_owner[block["id"]] = uuid

    def prompt_for(self, tool_use_id):
        """Walk parentUuid up from the tool_use's entry to the typed prompt that started the turn."""
        uuid = self.tool_use_owner.get(tool_use_id)
        if uuid is None:
            raise JoinError(f"tool_use_id {tool_use_id} has no tool_use block in the transcript")
        seen = set()
        while uuid is not None:
            if uuid in seen:
                raise JoinError(f"parentUuid cycle at {uuid} walking up from {tool_use_id}")
            seen.add(uuid)
            entry = self.by_uuid.get(uuid)
            if entry is None:
                raise JoinError(f"parentUuid {uuid} is missing from the transcript")
            if entry.get("type") == "user" and not is_tool_result(entry):
                return entry
            uuid = entry.get("parentUuid")
        raise JoinError(f"reached the root above {tool_use_id} without finding a user prompt")


def join(capture_records, transcript_entries, trace_id=None):
    """Resolve each captured tool span (optionally in one trace) to its prompt.

    Raises JoinError when the capture has no tool spans to join, when the two files come from
    different sessions, or when any tool span fails to reach a prompt.
    """
    spans = list(tool_spans(capture_records))
    if trace_id is not None:
        spans = [s for s in spans if s.trace_id == trace_id]
    if not spans:
        where = f"trace {trace_id}" if trace_id else "the capture"
        raise JoinError(f"no claude_code.tool spans with a tool_use_id in {where}")

    transcript = Transcript(transcript_entries)
    if not transcript.session_ids:
        raise JoinError("the transcript has no sessionId")
    span_sessions = {s.session_id for s in spans if s.session_id}
    stray = span_sessions - transcript.session_ids
    if stray:
        raise JoinError(
            f"capture session.id {sorted(stray)} is not the transcript's "
            f"sessionId {sorted(transcript.session_ids)}"
        )

    joins = []
    for span in spans:
        prompt = transcript.prompt_for(span.tool_use_id)
        joins.append(Join(span=span, prompt_uuid=prompt["uuid"], prompt=prompt_text(prompt)))
    return joins


def render(joins):
    """Format joins grouped by trace: its tool spans, then the prompt each traces back to."""
    lines = []
    for trace_id in dict.fromkeys(j.span.trace_id for j in joins):
        in_trace = [j for j in joins if j.span.trace_id == trace_id]
        lines.append(f"trace {trace_id}")
        for j in in_trace:
            lines.append(f"  span {j.span.span_id}  {j.span.tool_name:<24} "
                         f"{j.span.tool_use_id}  -> prompt {j.prompt_uuid}")
        for prompt_uuid in dict.fromkeys(j.prompt_uuid for j in in_trace):
            prompt = next(j.prompt for j in in_trace if j.prompt_uuid == prompt_uuid)
            lines.append(f"  prompt {prompt_uuid}:")
            lines.extend(f"    {ln}" for ln in prompt.splitlines() or [""])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Join a captured trace back to the prompt that caused it via the transcript."
    )
    parser.add_argument("--capture", default="demo/replay/session-sample.jsonl",
                        help="capture file (OTLP JSON-lines)")
    parser.add_argument("--transcript",
                        help=f"session transcript (default: the capture's *{TRANSCRIPT_SUFFIX})")
    parser.add_argument("--trace", help="only join this trace ID (as shown in Jaeger)")
    args = parser.parse_args(argv)

    capture = Path(args.capture)
    transcript = Path(args.transcript) if args.transcript else transcript_path_for(capture)
    for path, what in ((capture, "capture"), (transcript, "transcript")):
        if not path.exists():
            raise SystemExit(f"{what} file not found: {path}")
    try:
        joins = join(load_jsonl(capture), load_jsonl(transcript), trace_id=args.trace)
    except JoinError as e:
        raise SystemExit(f"join failed: {e}")
    sys.stdout.write(render(joins))


if __name__ == "__main__":
    main()
