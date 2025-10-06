"""Main Ansari LangGraph agent implementation."""

from ansari_agent.utils import setup_logger
from ansari_langgraph.graph import create_graph
from ansari_langgraph.state import AnsariState

logger = setup_logger(__name__)


class AnsariLangGraph:
    """Ansari Agent using LangGraph for orchestration."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """Initialize the Ansari LangGraph agent.

        Args:
            model: Anthropic model name (claude-sonnet-4-20250514, claude-opus-4-20250514, etc.)
        """
        self.model = model
        self.graph = create_graph(model=model)
        logger.info(f"AnsariLangGraph initialized with {model}")

    async def query(self, message: str) -> str:
        """Send a query to the agent and get complete response.

        Args:
            message: User's question

        Returns:
            Agent's complete response as string
        """
        logger.info(f'User query: "{message}"')

        # Create initial state
        initial_state: AnsariState = {
            "messages": [{"role": "user", "content": message}],
        }

        # Run the graph
        result = await self.graph.ainvoke(initial_state)

        # Extract final response
        final_response = result.get("final_response", "")
        citations = result.get("citations", [])

        logger.info(
            f"Query complete: {len(final_response)} chars, {len(citations)} citations"
        )

        return final_response

    async def query_with_citations(self, message: str) -> dict:
        """Send a query and get response with citations.

        Args:
            message: User's question

        Returns:
            Dict with 'response', 'citations', 'input_tokens', and 'output_tokens' keys
        """
        logger.info(f'User query: "{message}"')

        # Create initial state
        initial_state: AnsariState = {
            "messages": [{"role": "user", "content": message}],
        }

        # Run the graph
        result = await self.graph.ainvoke(initial_state)

        # Extract response and citations
        final_response = result.get("final_response", "")
        citations = result.get("citations", [])
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)

        logger.info(
            f"Query complete: {len(final_response)} chars, {len(citations)} citations, "
            f"{input_tokens} input tokens, {output_tokens} output tokens"
        )

        return {
            "response": final_response,
            "citations": citations,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    async def stream_query(self, message: str):
        """Send a query and stream the response token-by-token.

        Uses LangGraph's stream_mode="messages" to get token-level streaming
        from the LLM via ChatAnthropic.

        Args:
            message: User's question

        Yields:
            Token chunks as they arrive from the LLM
        """
        logger.info(f'Streaming query: "{message}"')

        # Create initial state
        initial_state: AnsariState = {
            "messages": [{"role": "user", "content": message}],
        }

        # Stream with messages mode to get token-level chunks
        async for event in self.graph.astream_events(initial_state, version="v2"):
            # Look for streaming events from the LLM
            kind = event.get("event")

            if kind == "on_chat_model_stream":
                # This is a token from the LLM
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content"):
                    # chunk.content is a list of content blocks
                    for block in chunk.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            # Yield just the text portion
                            text = block.get("text", "")
                            if text:
                                yield text
