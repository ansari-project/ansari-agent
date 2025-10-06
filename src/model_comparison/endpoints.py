"""API endpoints for model comparison."""

import asyncio
import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from .models import QueryRequest, SessionResponse, ChatMessage, HeartbeatEvent
from .session import session_manager
from .auth import verify_credentials
from .streaming import format_sse
from .langgraph_adapter import stream_all_models
from .config import config

logger = logging.getLogger(__name__)

router = APIRouter()

# Track active streaming tasks per session
active_tasks: Dict[str, asyncio.Task] = {}


@router.post("/api/query", response_model=SessionResponse)
async def submit_query(
    request: QueryRequest,
    username: str = Depends(verify_credentials),
):
    """Submit a new query and get session ID.

    Args:
        request: Query request with message
        username: Authenticated username

    Returns:
        Session ID for streaming
    """
    # Create new session
    session_id = await session_manager.create_session()

    # Add user message to all model histories
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create session")

    user_message = ChatMessage(role="user", content=request.message)
    for model_id in config.MODELS.keys():
        session.add_message(model_id, user_message)

    logger.info(
        f"[session: {session_id}] Query submitted by {username}: "
        f"{request.message[:50]}..."
    )

    return SessionResponse(session_id=session_id)


@router.get("/api/stream/{session_id}")
async def stream_responses(
    session_id: str,
    username: str = Depends(verify_credentials),
):
    """Stream responses from all 4 models via SSE.

    Args:
        session_id: Session ID from /api/query
        username: Authenticated username

    Returns:
        SSE stream with events from all models
    """
    # Get session
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info(f"[session: {session_id}] Starting stream for user {username}")

    async def event_generator():
        """Generate SSE events with heartbeat."""
        try:
            # Get all messages except the last user message
            # (which was added in /api/query)
            messages = []
            for model_id in config.MODELS.keys():
                history = session.get_history(model_id)
                if history:
                    messages = history
                    break

            # Stream from all models
            heartbeat_task = None

            async def send_heartbeats():
                """Send periodic heartbeats."""
                while True:
                    await asyncio.sleep(config.HEARTBEAT_INTERVAL_SECONDS)
                    yield format_sse(HeartbeatEvent())

            # Start heartbeat task
            heartbeat_gen = send_heartbeats()
            heartbeat_task = asyncio.create_task(
                heartbeat_gen.__anext__()
            )

            # Stream events from all models
            model_stream = stream_all_models(
                messages=messages,
                session_id=session_id,
            )

            # Interleave model events and heartbeats
            async for event in model_stream:
                yield format_sse(event)

                # Check if heartbeat is ready
                if heartbeat_task.done():
                    try:
                        heartbeat_event = heartbeat_task.result()
                        yield heartbeat_event
                        # Schedule next heartbeat
                        heartbeat_task = asyncio.create_task(
                            heartbeat_gen.__anext__()
                        )
                    except StopAsyncIteration:
                        pass

                # Update session with assistant responses
                if event.type == "done" and hasattr(event, "model_id"):
                    # Get the accumulated content for this model
                    # (Already tracked in stream_model)
                    pass

            # Cancel heartbeat task
            if heartbeat_task and not heartbeat_task.done():
                heartbeat_task.cancel()

            logger.info(f"[session: {session_id}] Stream completed")

        except asyncio.CancelledError:
            logger.info(f"[session: {session_id}] Stream cancelled by client")
            raise
        except Exception as e:
            logger.error(
                f"[session: {session_id}] Stream error: {e}",
                exc_info=True,
            )
            raise

    # Return SSE response with proper headers
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        },
    )


@router.post("/api/cancel/{session_id}")
async def cancel_stream(
    session_id: str,
    username: str = Depends(verify_credentials),
):
    """Cancel an in-flight stream.

    Args:
        session_id: Session ID to cancel
        username: Authenticated username

    Returns:
        Success message
    """
    logger.info(
        f"[session: {session_id}] Cancel requested by {username}"
    )

    # Check if session has active task
    if session_id in active_tasks:
        task = active_tasks[session_id]
        if not task.done():
            task.cancel()
            logger.info(f"[session: {session_id}] Stream task cancelled")

    return {"status": "cancelled", "session_id": session_id}
