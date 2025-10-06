"""Test Ansari Agent core functionality."""

import anyio
from ansari_agent.core import AnsariAgent
from ansari_agent.utils import config, setup_logger

logger = setup_logger(__name__)


async def test_agent_query():
    """Test agent with a query that should trigger SearchQuran tool."""
    print("\n=== Testing Ansari Agent ===\n")

    # Validate config
    try:
        config.validate()
        print("✅ Configuration validated")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return

    # Initialize agent
    agent = AnsariAgent()
    print("✅ Agent initialized")

    # Connect to SDK
    await agent.connect()
    print("✅ Agent connected")

    try:
        # Test query
        query = "What does the Quran say about patience?"
        print(f'\nQuery: "{query}"')
        print("\nWaiting for response...\n")

        response = await agent.query(query)
    finally:
        # Disconnect
        await agent.disconnect()

    print("=" * 60)
    print("RESPONSE:")
    print("=" * 60)
    print(response)
    print("=" * 60)

    # Verify response contains Quranic content
    has_arabic = any(ord(c) > 127 for c in response)  # Arabic characters
    has_citation = any(num in response for num in ["2:153", "39:10", "3:200"])

    print("\n=== GATE 2: State Management & Tool Integration ===")
    print(f"Response length: {len(response)} chars")
    print(f"Contains Arabic text: {has_arabic}")
    print(f"Contains citations: {has_citation}")

    if response and len(response) > 50:
        print("✅ PASS: Agent responded with substantial content")
        if has_arabic and has_citation:
            print("✅ PASS: Response includes Quranic verses with citations")
            print("✅ Ready to proceed to Phase 4 (Citation Formatting)")
        else:
            print("⚠️  WARNING: Response may not include expected verse format")
    else:
        print("❌ FAIL: Agent response too short or missing")

    return response


async def test_agent_streaming():
    """Test agent streaming capability."""
    print("\n\n=== Testing Agent Streaming ===\n")

    agent = AnsariAgent()
    await agent.connect()

    try:
        query = "Tell me briefly about sabr in Islam"

        print(f'Query: "{query}"')
        print("\nStreaming response:\n")
        print("-" * 60)

        chunks = []
        async for chunk in agent.stream_query(query):
            print(chunk, end="", flush=True)
            chunks.append(chunk)

        print("\n" + "-" * 60)
        print(f"\nReceived {len(chunks)} chunks")

        return "".join(chunks)
    finally:
        await agent.disconnect()


if __name__ == "__main__":
    print("Running basic query test...")
    anyio.run(test_agent_query)

    print("\n" + "=" * 60)
    print("Running streaming test...")
    anyio.run(test_agent_streaming)
