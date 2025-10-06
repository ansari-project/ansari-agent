"""SSE streaming utilities."""

import json
from typing import AsyncGenerator
from .models import SSEEvent


def format_sse(event: SSEEvent) -> str:
    """Format an event as Server-Sent Event.

    Format:
        data: {...}\\n\\n

    For heartbeat events, use comment format:
        : heartbeat\\n\\n
    """
    if event.type == "heartbeat":
        return ": heartbeat\n\n"

    # Serialize event to JSON
    data = event.model_dump(mode="json")
    return f"data: {json.dumps(data)}\n\n"


async def heartbeat_generator(interval_seconds: int = 10) -> AsyncGenerator[str, None]:
    """Generate heartbeat comments at regular intervals.

    This is a placeholder for now; actual implementation will be in Phase 2
    when we integrate with the streaming logic.
    """
    import asyncio
    from .models import HeartbeatEvent

    while True:
        await asyncio.sleep(interval_seconds)
        yield format_sse(HeartbeatEvent())
