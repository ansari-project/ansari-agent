"""Pydantic models for SSE events and API requests."""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessage(BaseModel):
    """Single message in a conversation."""
    role: Literal["user", "assistant"]
    content: str


class QueryRequest(BaseModel):
    """Request to submit a new query."""
    message: str = Field(..., min_length=1, max_length=10000)


class SessionResponse(BaseModel):
    """Response with session ID."""
    session_id: str


# SSE Event Models
class SSEEventBase(BaseModel):
    """Base class for all SSE events."""
    type: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())


class StartEvent(SSEEventBase):
    """Stream initialization event."""
    type: Literal["start"] = "start"
    model_id: str


class TTFTEvent(SSEEventBase):
    """Time to first token event."""
    type: Literal["ttft"] = "ttft"
    model_id: str
    ttft_ms: float


class TokenEvent(SSEEventBase):
    """Content token event."""
    type: Literal["token"] = "token"
    model_id: str
    content: str


class ToolStartEvent(SSEEventBase):
    """Tool invocation start."""
    type: Literal["tool_start"] = "tool_start"
    model_id: str
    tool_name: str
    tool_input: dict = {}


class ToolEndEvent(SSEEventBase):
    """Tool invocation end."""
    type: Literal["tool_end"] = "tool_end"
    model_id: str
    tool_name: str
    duration_ms: float
    tool_result: Optional[dict] = None


class CitationsEvent(SSEEventBase):
    """Citations from tool results."""
    type: Literal["citations"] = "citations"
    model_id: str
    citations: list[dict]


class DoneEvent(SSEEventBase):
    """Stream completion event."""
    type: Literal["done"] = "done"
    model_id: str
    total_ms: float
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    tool_calls: Optional[int] = None
    cost: Optional[dict] = None  # Pricing information


class ErrorEvent(SSEEventBase):
    """Error event."""
    type: Literal["error"] = "error"
    model_id: str
    error: str
    retry_after_ms: Optional[int] = None


class HeartbeatEvent(SSEEventBase):
    """Keepalive heartbeat."""
    type: Literal["heartbeat"] = "heartbeat"


# Union type for all events
SSEEvent = (
    StartEvent
    | TTFTEvent
    | TokenEvent
    | ToolStartEvent
    | ToolEndEvent
    | CitationsEvent
    | DoneEvent
    | ErrorEvent
    | HeartbeatEvent
)
