"""LangGraph integration and event normalization."""

import asyncio
import logging
import time
from typing import AsyncGenerator, Optional
from .models import (
    SSEEvent,
    StartEvent,
    TTFTEvent,
    TokenEvent,
    ToolStartEvent,
    ToolEndEvent,
    DoneEvent,
    ErrorEvent,
    ChatMessage,
)
from .config import config

logger = logging.getLogger(__name__)


async def stream_model(
    model_id: str,
    messages: list[ChatMessage],
    event_queue: asyncio.Queue,
    session_id: str,
) -> None:
    """Stream from a single model and put events into queue.

    Args:
        model_id: Model identifier
        messages: Conversation history
        event_queue: Queue to put SSE events
        session_id: Session ID for logging context
    """
    start_time = time.time()
    first_token_time: Optional[float] = None
    tool_start_times: dict[str, float] = {}

    try:
        # Import here to avoid circular imports
        from ansari_langgraph.graph import create_graph
        from ansari_langgraph.state import AnsariState

        logger.info(f"[session: {session_id}] [model: {model_id}] Starting stream")

        # Send start event
        await event_queue.put(StartEvent(model_id=model_id))

        # Create agent graph for this model
        graph = create_graph(model=model_id)

        # Convert messages to LangGraph format
        lg_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Initialize state
        initial_state = AnsariState(
            messages=lg_messages,
            tool_calls=None,
            tool_results=[],
            citations=[],
            final_response=None,
            stop_reason=None,
            input_tokens=0,
            output_tokens=0,
        )

        # Track accumulated response
        accumulated_content = ""
        tokens_in = 0
        tokens_out = 0

        # Stream events with timeout
        async with asyncio.timeout(config.STREAM_TIMEOUT_SECONDS):
            async for event in graph.astream(initial_state, stream_mode="values"):
                # Track TTFT
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft_ms = (first_token_time - start_time) * 1000
                    await event_queue.put(
                        TTFTEvent(model_id=model_id, ttft_ms=ttft_ms)
                    )

                # Handle tool events
                if "current_tool" in event and event["current_tool"]:
                    tool_name = event["current_tool"]
                    if tool_name not in tool_start_times:
                        # Tool started
                        tool_start_times[tool_name] = time.time()
                        await event_queue.put(
                            ToolStartEvent(
                                model_id=model_id,
                                tool_name=tool_name,
                            )
                        )
                        logger.info(
                            f"[session: {session_id}] [model: {model_id}] "
                            f"Tool started: {tool_name}"
                        )

                # Handle completed tools
                if "tool_results" in event and event["tool_results"]:
                    for result in event["tool_results"]:
                        tool_name = result.get("tool_name", "unknown")
                        if tool_name in tool_start_times:
                            duration_ms = (
                                time.time() - tool_start_times[tool_name]
                            ) * 1000
                            await event_queue.put(
                                ToolEndEvent(
                                    model_id=model_id,
                                    tool_name=tool_name,
                                    duration_ms=duration_ms,
                                )
                            )
                            logger.info(
                                f"[session: {session_id}] [model: {model_id}] "
                                f"Tool completed: {tool_name} ({duration_ms:.0f}ms)"
                            )

                # Handle message updates
                if "messages" in event and event["messages"]:
                    last_message = event["messages"][-1]
                    if last_message.get("role") == "assistant":
                        content = last_message.get("content", "")
                        if content and content != accumulated_content:
                            # Send only new content (delta)
                            delta = content[len(accumulated_content):]
                            if delta:
                                await event_queue.put(
                                    TokenEvent(
                                        model_id=model_id,
                                        content=delta,
                                    )
                                )
                            accumulated_content = content
                            # Rough token estimate
                            tokens_out = len(content) // 4

        # Estimate input tokens
        total_input = sum(len(msg.content) for msg in messages)
        tokens_in = total_input // 4

        # Send completion event
        total_ms = (time.time() - start_time) * 1000
        await event_queue.put(
            DoneEvent(
                model_id=model_id,
                total_ms=total_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
        )

        logger.info(
            f"[session: {session_id}] [model: {model_id}] "
            f"Stream completed: {total_ms:.0f}ms, "
            f"tokens_in={tokens_in}, tokens_out={tokens_out}"
        )

    except asyncio.TimeoutError:
        error_msg = f"Stream timeout after {config.STREAM_TIMEOUT_SECONDS}s"
        logger.warning(
            f"[session: {session_id}] [model: {model_id}] {error_msg}"
        )
        await event_queue.put(
            ErrorEvent(
                model_id=model_id,
                error=error_msg,
            )
        )
    except asyncio.CancelledError:
        logger.info(
            f"[session: {session_id}] [model: {model_id}] Stream cancelled"
        )
        raise  # Propagate cancellation
    except Exception as e:
        error_msg = f"Error streaming: {str(e)}"
        logger.error(
            f"[session: {session_id}] [model: {model_id}] {error_msg}",
            exc_info=True,
        )
        await event_queue.put(
            ErrorEvent(
                model_id=model_id,
                error=error_msg,
            )
        )


async def stream_all_models(
    messages: list[ChatMessage],
    session_id: str,
) -> AsyncGenerator[SSEEvent, None]:
    """Stream from all 4 models concurrently using Queue + TaskGroup.

    Args:
        messages: Conversation messages
        session_id: Session ID for logging

    Yields:
        SSE events from all models as they arrive
    """
    event_queue: asyncio.Queue[SSEEvent] = asyncio.Queue()
    active_models = set(config.MODELS.keys())

    async def drain_queue():
        """Drain events from queue and track completion."""
        while active_models or not event_queue.empty():
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.5)

                # Track completion
                if event.type == "done" or event.type == "error":
                    if hasattr(event, "model_id") and event.model_id in active_models:
                        active_models.remove(event.model_id)

                yield event
            except asyncio.TimeoutError:
                # No events available, continue waiting
                continue

    # Start all model streams in task group
    async with asyncio.TaskGroup() as tg:
        # Create tasks for each model
        for model_id in config.MODELS.keys():
            tg.create_task(
                stream_model(
                    model_id=model_id,
                    messages=messages,
                    event_queue=event_queue,
                    session_id=session_id,
                )
            )

        # Drain queue concurrently with tasks
        async for event in drain_queue():
            yield event
