"""Main agent class for Ansari Gemini implementation."""

from ansari_agent.utils import setup_logger
from ansari_gemini.graph import create_graph
from ansari_gemini.state import AnsariState

logger = setup_logger(__name__)


class AnsariGemini:
    """Ansari agent using Gemini with LangGraph orchestration."""

    def __init__(self, model: str = "gemini-2.5-pro"):
        """Initialize the Ansari Gemini agent.

        Args:
            model: Gemini model name (gemini-2.5-pro or gemini-2.5-flash)
        """
        self.model = model
        self.graph = create_graph(model=model)
        logger.info(f"AnsariGemini initialized with {model}")

    async def query(self, message: str) -> str:
        """Send a query and get the response.

        Args:
            message: User's question

        Returns:
            Final response string
        """
        logger.info(f'Query: "{message}"')

        # Create initial state
        initial_state: AnsariState = {
            "messages": [{"role": "user", "content": message}],
        }

        # Execute graph
        result = await self.graph.ainvoke(initial_state)

        # Extract final response
        final_response = result.get("final_response", "")

        logger.info(
            f"Query complete ({len(final_response)} chars, "
            f"{len(result.get('citations', []))} citations)"
        )

        return final_response

    async def query_with_citations(self, message: str) -> dict:
        """Send a query and get response with citations.

        Args:
            message: User's question

        Returns:
            Dict with 'response', 'citations', 'input_tokens', and 'output_tokens' keys
        """
        logger.info(f'Query: "{message}"')

        # Create initial state
        initial_state: AnsariState = {
            "messages": [{"role": "user", "content": message}],
        }

        # Execute graph
        result = await self.graph.ainvoke(initial_state)

        # Extract response and citations
        final_response = result.get("final_response", "")
        citations = result.get("citations", [])
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)

        logger.info(
            f"Query complete ({len(final_response)} chars, {len(citations)} citations, "
            f"{input_tokens} input tokens, {output_tokens} output tokens)"
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
        from the LLM via ChatGoogleGenerativeAI.

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
                    # Gemini returns content as a string, not a list
                    content = chunk.content
                    if isinstance(content, str) and content:
                        yield content
