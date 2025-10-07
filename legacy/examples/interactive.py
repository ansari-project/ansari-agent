"""Interactive Ansari Agent - Ask questions in a loop."""

import anyio
from ansari_agent.core import AnsariAgent


async def main():
    """Run an interactive session with the agent."""

    print("=" * 60)
    print("Ansari Agent - Interactive Mode")
    print("=" * 60)
    print("\nInitializing agent...")

    agent = AnsariAgent()
    await agent.connect()
    print("✓ Agent ready!\n")
    print("Type your questions (or 'quit' to exit)\n")

    session_id = "interactive_session"

    try:
        while True:
            # Get question from user
            question = input("\nYou: ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            if not question:
                continue

            print("\nAnsari: ", end="", flush=True)

            # Stream the response
            async for chunk in agent.stream_query(question, session_id=session_id):
                print(chunk, end="", flush=True)

            print()  # New line after response

    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
    finally:
        await agent.disconnect()
        print("\n✓ Agent disconnected")


if __name__ == "__main__":
    anyio.run(main)
