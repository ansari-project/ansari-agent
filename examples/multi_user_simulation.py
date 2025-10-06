"""Example: Multi-user simulation with Claude Agent SDK.

This demonstrates how to handle multiple concurrent users with the SDK.
Each user gets their own agent instance and session ID.
"""

import anyio
from ansari_agent.core import AnsariAgent


async def handle_user_session(user_id: int, questions: list[str]):
    """Handle a single user's conversation session.

    Args:
        user_id: Unique user identifier
        questions: List of questions from this user
    """
    print(f"\n{'='*60}")
    print(f"User {user_id} Session Starting")
    print(f"{'='*60}")

    # Each user gets their own agent instance
    agent = AnsariAgent()
    await agent.connect()

    try:
        # Use user-specific session ID for conversation continuity
        session_id = f"user_{user_id}"

        for i, question in enumerate(questions, 1):
            print(f"\n[User {user_id}, Q{i}] {question}")

            # Query with session ID for conversation memory
            response = await agent.query(question, session_id=session_id)

            print(f"[User {user_id}, A{i}] {response[:200]}...")

    finally:
        await agent.disconnect()
        print(f"\n[User {user_id}] Session ended")


async def main():
    """Simulate multiple concurrent users."""

    print("=" * 60)
    print("Multi-User Simulation")
    print("=" * 60)
    print("\nSimulating 3 concurrent users with different questions\n")

    # Define user conversations
    users = [
        (1, ["What is sabr?", "Give me an example from the Quran"]),
        (2, ["Tell me about prayer in Islam"]),
        (3, ["What does the Quran say about charity?"]),
    ]

    # Run all user sessions concurrently
    async with anyio.create_task_group() as tg:
        for user_id, questions in users:
            tg.start_soon(handle_user_session, user_id, questions)

    print("\n" + "=" * 60)
    print("All user sessions complete")
    print("=" * 60)


if __name__ == "__main__":
    anyio.run(main)
