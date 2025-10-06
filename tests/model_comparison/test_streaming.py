"""Tests for SSE streaming utilities."""

import json
from model_comparison.streaming import format_sse
from model_comparison.models import (
    StartEvent,
    TokenEvent,
    HeartbeatEvent,
    ErrorEvent,
)


def test_format_sse_heartbeat():
    """Test heartbeat formatting."""
    event = HeartbeatEvent()
    formatted = format_sse(event)
    assert formatted == ": heartbeat\n\n"


def test_format_sse_start_event():
    """Test start event formatting."""
    event = StartEvent(model_id="gemini-2.5-pro")
    formatted = format_sse(event)

    assert formatted.startswith("data: ")
    assert formatted.endswith("\n\n")

    # Extract and parse JSON
    json_str = formatted[6:-2]  # Remove "data: " and "\n\n"
    data = json.loads(json_str)

    assert data["type"] == "start"
    assert data["model_id"] == "gemini-2.5-pro"
    assert "timestamp" in data


def test_format_sse_token_event():
    """Test token event formatting."""
    event = TokenEvent(model_id="claude-opus-4-20250514", content="Hello world")
    formatted = format_sse(event)

    json_str = formatted[6:-2]
    data = json.loads(json_str)

    assert data["type"] == "token"
    assert data["content"] == "Hello world"


def test_format_sse_error_event():
    """Test error event formatting."""
    event = ErrorEvent(
        model_id="test-model",
        error="Connection timeout",
        retry_after_ms=1000
    )
    formatted = format_sse(event)

    json_str = formatted[6:-2]
    data = json.loads(json_str)

    assert data["type"] == "error"
    assert data["error"] == "Connection timeout"
    assert data["retry_after_ms"] == 1000
