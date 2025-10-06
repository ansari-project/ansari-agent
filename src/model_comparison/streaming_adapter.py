"""Direct streaming adapter that bypasses LangGraph limitations."""

import asyncio
import logging
import time
from typing import AsyncGenerator, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

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
from ansari_langgraph.tools import search_quran
from ansari_langgraph.nodes import SYSTEM_MESSAGE

logger = logging.getLogger(__name__)


async def stream_model_direct(
    model_id: str,
    messages: list[ChatMessage],
    event_queue: asyncio.Queue,
    session_id: str,
) -> None:
    """Stream directly from LLM, bypassing LangGraph for true token streaming.

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
        logger.info(f"[session: {session_id}] [model: {model_id}] Starting direct stream")

        # Send start event
        await event_queue.put(StartEvent(model_id=model_id))

        # Create LLM client
        is_gemini = model_id.startswith("gemini")

        if is_gemini:
            llm = ChatGoogleGenerativeAI(
                model=model_id,
                temperature=config.TEMPERATURE,
                max_output_tokens=config.MAX_TOKENS,
                google_api_key=config.google_api_key,
            )
        else:
            llm = ChatAnthropic(
                model=model_id,
                temperature=config.TEMPERATURE,
                max_tokens=config.MAX_TOKENS,
                anthropic_api_key=config.anthropic_api_key,
            )

        # Bind tools
        llm_with_tools = llm.bind_tools([search_quran])

        # Convert messages to LangChain format
        lc_messages = [SystemMessage(content=SYSTEM_MESSAGE)]
        for msg in messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))

        # Track accumulated response
        accumulated_content = ""
        accumulated_tool_calls = []
        tokens_in = 0
        tokens_out = 0

        # Stream with timeout
        async with asyncio.timeout(config.STREAM_TIMEOUT_SECONDS):
            # Use astream for true token streaming
            async for chunk in llm_with_tools.astream(lc_messages):
                # Track TTFT
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft_ms = (first_token_time - start_time) * 1000
                    await event_queue.put(
                        TTFTEvent(model_id=model_id, ttft_ms=ttft_ms)
                    )

                # Handle streaming content
                if hasattr(chunk, 'content') and chunk.content:
                    # This is a text token
                    await event_queue.put(
                        TokenEvent(
                            model_id=model_id,
                            content=chunk.content,
                        )
                    )
                    accumulated_content += chunk.content

                # Handle tool calls
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    for tool_call in chunk.tool_calls:
                        accumulated_tool_calls.append(tool_call)
                        tool_name = tool_call.get("name", "unknown")

                        if tool_name not in tool_start_times:
                            tool_start_times[tool_name] = time.time()
                            await event_queue.put(
                                ToolStartEvent(
                                    model_id=model_id,
                                    tool_name=tool_name,
                                    tool_input=tool_call.get("args", {}),
                                )
                            )
                            logger.info(
                                f"[session: {session_id}] [model: {model_id}] "
                                f"Tool started: {tool_name}"
                            )

                # Track token usage from metadata
                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    tokens_in = chunk.usage_metadata.get("input_tokens", tokens_in)
                    tokens_out = chunk.usage_metadata.get("output_tokens", tokens_out)

        # If we have tool calls, execute them
        if accumulated_tool_calls:
            for tool_call in accumulated_tool_calls:
                tool_name = tool_call.get("name", "unknown")
                tool_input = tool_call.get("args", {})

                # Execute tool
                if tool_name == "search_quran":
                    result = await search_quran.ainvoke(tool_input)

                    # Send tool completion
                    if tool_name in tool_start_times:
                        duration_ms = (time.time() - tool_start_times[tool_name]) * 1000
                        await event_queue.put(
                            ToolEndEvent(
                                model_id=model_id,
                                tool_name=tool_name,
                                duration_ms=duration_ms,
                                tool_result=result,
                            )
                        )

                    # Extract citations
                    if result.get("count", 0) > 0:
                        citations = result.get("results", [])
                        if citations:
                            await event_queue.put(
                                CitationsEvent(
                                    model_id=model_id,
                                    citations=citations,
                                )
                            )

            # Now stream the follow-up response with tool results
            tool_messages = []
            for tool_call in accumulated_tool_calls:
                tool_messages.append(
                    ToolMessage(
                        content=str(result),  # Use the last result for simplicity
                        tool_call_id=tool_call.get("id", ""),
                    )
                )

            # Add tool results to message history and get final response
            lc_messages.extend(tool_messages)

            # Stream final response after tools
            async for chunk in llm_with_tools.astream(lc_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    await event_queue.put(
                        TokenEvent(
                            model_id=model_id,
                            content=chunk.content,
                        )
                    )
                    accumulated_content += chunk.content

                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    tokens_in = chunk.usage_metadata.get("input_tokens", tokens_in)
                    tokens_out = chunk.usage_metadata.get("output_tokens", tokens_out)

        # Estimate tokens if not provided
        if tokens_in == 0:
            total_input = sum(len(msg.content) for msg in messages)
            tokens_in = total_input // 4

        if tokens_out == 0:
            tokens_out = len(accumulated_content) // 4

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
            f"Direct stream completed: {total_ms:.0f}ms, "
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


async def stream_all_models_direct(
    messages: list[ChatMessage],
    session_id: str,
) -> AsyncGenerator[SSEEvent, None]:
    """Stream from all 4 models directly without LangGraph.

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
                stream_model_direct(
                    model_id=model_id,
                    messages=messages,
                    event_queue=event_queue,
                    session_id=session_id,
                )
            )

        # Drain queue concurrently with tasks
        async for event in drain_queue():
            yield event