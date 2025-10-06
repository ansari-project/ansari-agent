"""Tests for session management."""

import pytest
import asyncio
from model_comparison.session import Session, SessionManager
from model_comparison.models import ChatMessage
from model_comparison.config import config


def test_session_creation():
    """Test session creation."""
    session = Session("test-123")
    assert session.session_id == "test-123"
    assert session.created_at > 0
    assert session.last_accessed > 0
    assert len(session.histories) == len(config.MODELS)


def test_session_access_time_update():
    """Test access time updates."""
    session = Session("test-123")
    original_time = session.last_accessed
    asyncio.sleep(0.01)
    session.update_access_time()
    assert session.last_accessed > original_time


def test_session_message_addition():
    """Test adding messages to session."""
    session = Session("test-123")
    msg = ChatMessage(role="user", content="Hello")

    session.add_message("gemini-2.5-pro", msg)
    history = session.get_history("gemini-2.5-pro")
    assert len(history) == 1
    assert history[0].content == "Hello"


def test_session_history_truncation_by_turns():
    """Test history truncation by number of turns."""
    session = Session("test-123")

    # Add more than MAX_HISTORY_TURNS * 2 messages
    for i in range(config.MAX_HISTORY_TURNS * 2 + 5):
        msg = ChatMessage(
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}"
        )
        session.add_message("gemini-2.5-pro", msg)

    history = session.get_history("gemini-2.5-pro")
    # Should be truncated to MAX_HISTORY_TURNS * 2
    assert len(history) <= config.MAX_HISTORY_TURNS * 2


def test_session_history_truncation_by_tokens():
    """Test history truncation by token estimate."""
    session = Session("test-123")

    # Add a very long message (>MAX_HISTORY_TOKENS * 4 chars)
    long_content = "a" * (config.MAX_HISTORY_TOKENS * 5)
    msg1 = ChatMessage(role="user", content=long_content)
    session.add_message("gemini-2.5-pro", msg1)

    # Add another message
    msg2 = ChatMessage(role="assistant", content="Short response")
    session.add_message("gemini-2.5-pro", msg2)

    history = session.get_history("gemini-2.5-pro")
    # First message should have been truncated
    total_chars = sum(len(msg.content) for msg in history)
    assert total_chars // 4 <= config.MAX_HISTORY_TOKENS


def test_session_expiration():
    """Test session expiration logic."""
    session = Session("test-123")
    assert not session.is_expired()

    # Manually set last_accessed to old time
    session.last_accessed = session.last_accessed - config.SESSION_TTL_SECONDS - 1
    assert session.is_expired()


@pytest.mark.asyncio
async def test_session_manager_create():
    """Test session creation via manager."""
    manager = SessionManager()
    session_id = await manager.create_session()

    assert session_id is not None
    assert len(session_id) > 0

    # Should be able to retrieve the session
    session = await manager.get_session(session_id)
    assert session is not None
    assert session.session_id == session_id


@pytest.mark.asyncio
async def test_session_manager_lru_eviction():
    """Test LRU eviction when max sessions reached."""
    manager = SessionManager()

    # Create MAX_SESSIONS + 1 sessions
    session_ids = []
    for _ in range(config.MAX_SESSIONS + 1):
        sid = await manager.create_session()
        session_ids.append(sid)

    # First session should have been evicted
    first_session = await manager.get_session(session_ids[0])
    assert first_session is None

    # Last session should exist
    last_session = await manager.get_session(session_ids[-1])
    assert last_session is not None


@pytest.mark.asyncio
async def test_session_manager_expired_cleanup():
    """Test cleanup of expired sessions."""
    manager = SessionManager()
    session_id = await manager.create_session()

    # Get session to set it up
    session = await manager.get_session(session_id)
    assert session is not None

    # Manually expire it
    session.last_accessed = session.last_accessed - config.SESSION_TTL_SECONDS - 1

    # Try to get it again - should be cleaned up
    expired_session = await manager.get_session(session_id)
    assert expired_session is None


@pytest.mark.asyncio
async def test_session_manager_delete():
    """Test session deletion."""
    manager = SessionManager()
    session_id = await manager.create_session()

    # Verify it exists
    session = await manager.get_session(session_id)
    assert session is not None

    # Delete it
    await manager.delete_session(session_id)

    # Should be gone
    deleted_session = await manager.get_session(session_id)
    assert deleted_session is None


@pytest.mark.asyncio
async def test_session_manager_count():
    """Test session count tracking."""
    manager = SessionManager()

    initial_count = await manager.get_session_count()

    await manager.create_session()
    await manager.create_session()

    count_after = await manager.get_session_count()
    assert count_after == initial_count + 2
