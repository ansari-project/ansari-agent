"""Tests for Pydantic models and event serialization."""

import pytest
from model_comparison.models import (
    ChatMessage,
    QueryRequest,
    SessionResponse,
    StartEvent,
    TTFTEvent,
    TokenEvent,
    ToolStartEvent,
    ToolEndEvent,
    DoneEvent,
    ErrorEvent,
    HeartbeatEvent,
)


def test_chat_message():
    """Test ChatMessage model."""
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_query_request():
    """Test QueryRequest validation."""
    req = QueryRequest(message="Test query")
    assert req.message == "Test query"

    # Test min length
    with pytest.raises(ValueError):
        QueryRequest(message="")


def test_session_response():
    """Test SessionResponse model."""
    resp = SessionResponse(session_id="test-123")
    assert resp.session_id == "test-123"


def test_start_event():
    """Test StartEvent serialization."""
    event = StartEvent(model_id="gemini-2.5-pro")
    assert event.type == "start"
    assert event.model_id == "gemini-2.5-pro"
    assert event.timestamp > 0

    # Test serialization
    data = event.model_dump()
    assert data["type"] == "start"
    assert data["model_id"] == "gemini-2.5-pro"


def test_ttft_event():
    """Test TTFTEvent serialization."""
    event = TTFTEvent(model_id="claude-opus-4-20250514", ttft_ms=250.5)
    assert event.type == "ttft"
    assert event.ttft_ms == 250.5


def test_token_event():
    """Test TokenEvent serialization."""
    event = TokenEvent(model_id="gemini-2.5-flash", content="Hello")
    assert event.type == "token"
    assert event.content == "Hello"


def test_tool_events():
    """Test tool start/end events."""
    start = ToolStartEvent(model_id="test-model", tool_name="search_quran")
    assert start.type == "tool_start"
    assert start.tool_name == "search_quran"

    end = ToolEndEvent(
        model_id="test-model", tool_name="search_quran", duration_ms=123.4
    )
    assert end.type == "tool_end"
    assert end.duration_ms == 123.4


def test_done_event():
    """Test DoneEvent serialization."""
    event = DoneEvent(
        model_id="test-model",
        total_ms=1500.0,
        tokens_in=10,
        tokens_out=50,
    )
    assert event.type == "done"
    assert event.total_ms == 1500.0
    assert event.tokens_in == 10
    assert event.tokens_out == 50


def test_error_event():
    """Test ErrorEvent serialization."""
    event = ErrorEvent(
        model_id="test-model",
        error="API rate limit exceeded",
        retry_after_ms=5000,
    )
    assert event.type == "error"
    assert event.error == "API rate limit exceeded"
    assert event.retry_after_ms == 5000


def test_heartbeat_event():
    """Test HeartbeatEvent serialization."""
    event = HeartbeatEvent()
    assert event.type == "heartbeat"
    assert event.timestamp > 0
