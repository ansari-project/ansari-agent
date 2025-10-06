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
    CitationsEvent,
    DoneEvent,
    ErrorEvent,
    ChatMessage,
)
from .config import config
from ansari_agent.utils.pricing import calculate_cost, format_cost

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
        from ansari_langgraph.graph_provider import get_graph
        from ansari_langgraph.state import AnsariState

        logger.info(f"[session: {session_id}] [model: {model_id}] Starting stream")

        # Send start event
        await event_queue.put(StartEvent(model_id=model_id))

        # Get pre-compiled graph from cache
        graph = get_graph(model_id)
        if not graph:
            error_msg = f"Graph for model '{model_id}' not found in cache"
            logger.error(f"[session: {session_id}] [model: {model_id}] {error_msg}")
            await event_queue.put(
                ErrorEvent(
                    model_id=model_id,
                    error=error_msg,
                )
            )
            return

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
        accumulated_citations = []
        tokens_in = 0
        tokens_out = 0
        tool_call_count = 0

        # Stream events with timeout using astream_events for token-by-token streaming
        final_state = None
        async with asyncio.timeout(config.STREAM_TIMEOUT_SECONDS):
            async for event in graph.astream_events(initial_state, version="v2"):
                kind = event.get("event")

                # Capture final state from graph
                if kind == "on_chain_end":
                    # This fires when the entire graph completes
                    output = event.get("data", {}).get("output")
                    if output:
                        final_state = output

                # Handle token streaming from chat model
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, 'content') and chunk.content:
                        # Extract text content (handle both string and list formats)
                        text_content = ""
                        if isinstance(chunk.content, str):
                            text_content = chunk.content
                        elif isinstance(chunk.content, list):
                            # Claude returns content as list of blocks
                            for block in chunk.content:
                                if isinstance(block, dict) and block.get('type') == 'text':
                                    text_content += block.get('text', '')
                                elif hasattr(block, 'text'):
                                    text_content += block.text

                        if text_content:
                            # Track TTFT on first token
                            if first_token_time is None:
                                first_token_time = time.time()
                                ttft_ms = (first_token_time - start_time) * 1000
                                await event_queue.put(
                                    TTFTEvent(model_id=model_id, ttft_ms=ttft_ms)
                                )

                            # Send token chunk
                            await event_queue.put(
                                TokenEvent(model_id=model_id, content=text_content)
                            )
                            accumulated_content += text_content

                # Handle tool start
                elif kind == "on_tool_start":
                    data = event.get("data", {})
                    tool_name = event.get("name", "unknown")
                    tool_input = data.get("input", {})

                    if tool_name not in tool_start_times:
                        tool_start_times[tool_name] = time.time()
                        tool_call_count += 1  # Count tool calls
                        await event_queue.put(
                            ToolStartEvent(
                                model_id=model_id,
                                tool_name=tool_name,
                                tool_input=tool_input,
                            )
                        )
                        logger.info(
                            f"[session: {session_id}] [model: {model_id}] "
                            f"Tool started: {tool_name} with input: {tool_input}"
                        )

                # Handle tool end
                elif kind == "on_tool_end":
                    data = event.get("data", {})
                    tool_name = event.get("name", "unknown")
                    tool_output = data.get("output")

                    if tool_name in tool_start_times:
                        duration_ms = (
                            time.time() - tool_start_times.pop(tool_name)
                        ) * 1000
                        await event_queue.put(
                            ToolEndEvent(
                                model_id=model_id,
                                tool_name=tool_name,
                                duration_ms=duration_ms,
                                tool_result=tool_output,
                            )
                        )
                        logger.info(
                            f"[session: {session_id}] [model: {model_id}] "
                            f"Tool completed: {tool_name} ({duration_ms:.0f}ms)"
                        )

                        # Extract citations from tool results if present
                        if isinstance(tool_output, dict) and "results" in tool_output:
                            accumulated_citations = tool_output.get("results", [])

        # Get ACTUAL token counts from final state (includes tool usage)
        if final_state:
            tokens_in = final_state.get("input_tokens", 0)
            tokens_out = final_state.get("output_tokens", 0)

            logger.info(
                f"[session: {session_id}] [model: {model_id}] "
                f"Actual token usage from LLM: input={tokens_in}, output={tokens_out}"
            )
        else:
            # Fallback to estimation if state not available (shouldn't happen)
            logger.warning(
                f"[session: {session_id}] [model: {model_id}] "
                f"No final state available, falling back to estimation"
            )
            total_input = sum(len(msg.content) for msg in messages)
            tokens_in = total_input // 4
            tokens_out = len(accumulated_content) // 4

        # Send citations before completion event
        if accumulated_citations:
            await event_queue.put(
                CitationsEvent(
                    model_id=model_id,
                    citations=accumulated_citations,
                )
            )
            logger.info(
                f"[session: {session_id}] [model: {model_id}] "
                f"Sent {len(accumulated_citations)} citations"
            )

        # Calculate pricing (will add the same overhead internally)
        cost_info = calculate_cost(model_id, tokens_in, tokens_out, tool_call_count)

        # Send completion event with adjusted tokens and pricing
        total_ms = (time.time() - start_time) * 1000
        await event_queue.put(
            DoneEvent(
                model_id=model_id,
                total_ms=total_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                tool_calls=tool_call_count,
                cost=cost_info,
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
