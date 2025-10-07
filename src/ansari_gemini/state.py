"""State definitions for Gemini-based Ansari agent."""

from typing import TypedDict


class AnsariState(TypedDict, total=False):
    """State for the Ansari Gemini agent.

    Tracks conversation messages, tool calls, and results throughout the graph execution.
    """

    # Core message history
    messages: list[dict]

    # Tool execution tracking
    tool_calls: list[dict] | None  # Pending tool calls from LLM
    tool_results: list[dict]  # Completed tool results
    tool_call_count: int  # Total number of tool calls made (for limits)

    # Citation and response tracking
    citations: list[dict]  # Extracted citations from tool results
    final_response: str | None  # Final formatted response

    # Execution metadata
    stop_reason: str | None  # Stop reason (tool_use, end_turn, etc.)
    forced_answer: bool  # Whether we forced an answer due to tool limits

    # Token usage tracking
    input_tokens: int  # Total input tokens used
    output_tokens: int  # Total output tokens generated
