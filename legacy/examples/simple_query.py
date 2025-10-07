"""Simple example of using Ansari Agent with Claude SDK."""

import anyio
from ansari_agent.core import AnsariAgent


async def main():
    """Run a simple query with the Ansari Agent."""

    # Initialize agent
    agent = AnsariAgent()

    # Connect to Claude SDK
    await agent.connect()

    try:
        # Ask a question
        question = "What does the Quran teach about gratitude?"
        print(f"Question: {question}\n")

        # Get response
        response = await agent.query(question)

        print(f"Response:\n{response}")

    finally:
        # Always disconnect
        await agent.disconnect()


if __name__ == "__main__":
    anyio.run(main)
