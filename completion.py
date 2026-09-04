"""Fail-closed session completion classification for Ontinuity.

This module is intentionally dependency-free so the completion gate can be
tested without starting Flask, Socket.IO, a model provider, or the workspace
server.
"""

TERMINAL_REASONS = {
    "incomplete_model_dead": "researcher_provider_dead",
    "incomplete_challenger_dead": "challenger_provider_dead",
    "incomplete_terminated": "process_terminated",
    "incomplete_timeout": "session_timeout",
    "incomplete_malformed_response": "malformed_model_response",
    "incomplete_missing_extraction": "work_product_extraction_failed",
    "incomplete_no_close": "no_certified_close",
    "stopped": "operator_stop",
    "failed": "session_failed",
    "abandoned": "session_abandoned",
}


def classify_completion(requested_status=None, transcript_turns=None,
                        unreviewed_cycles=None, end_reason=None):
    """Return an honest ``(status, end_reason)`` pair.

    ``complete`` is never accepted merely because a caller requested it. A
    certified close must be present and no cycle may be unreviewed. Explicit
    failure/stop statuses pass through with a normalized reason. Missing or
    provisional status is evaluated by the same close evidence.
    """
    turns = transcript_turns or []
    unreviewed = list(unreviewed_cycles or [])
    has_close = any(turn.get("tag") == "SESSION_END" for turn in turns)
    has_no_review = any(turn.get("tag") == "NO_REVIEW" for turn in turns)

    status = (requested_status or "in_progress").strip()
    if status not in ("complete", "in_progress"):
        return status, end_reason or TERMINAL_REASONS.get(status, status)
    if unreviewed or has_no_review:
        return "incomplete_challenger_dead", (
            end_reason or "challenger_provider_dead")
    if has_close:
        return "complete", "certified_close"
    return "incomplete_no_close", end_reason or "no_certified_close"


def model_failure_outcome(role, failure_kind):
    """Map a structured seat failure to its terminal session outcome."""
    seat = "researcher" if role == "model_a" else "challenger"
    kind = failure_kind or "provider_dead"
    if role == "model_a" and kind == "timeout":
        return "incomplete_timeout", "researcher_timeout"
    if role == "model_a" and kind == "malformed_response":
        return "incomplete_malformed_response", "researcher_malformed_response"
    if role == "model_a":
        return "incomplete_model_dead", f"researcher_{kind}"
    return "incomplete_challenger_dead", f"{seat}_{kind}"


def extract_anthropic_text(payload):
    """Return Anthropic text or raise when a successful response has no output."""
    text = payload["content"][0]["text"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Anthropic returned empty text")
    return text


def extract_gemini_text(payload):
    """Return Gemini text or raise when a successful response has no output."""
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Gemini returned empty text")
    return text
