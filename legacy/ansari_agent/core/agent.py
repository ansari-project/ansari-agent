"""Core Ansari Agent using Claude SDK."""

import os
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, create_sdk_mcp_server
from ansari_agent.utils import config, setup_logger
from ansari_agent.tools import search_quran

logger = setup_logger(__name__)


class AnsariAgent:
    """Ansari Agent - Islamic knowledge assistant using Claude SDK."""

    def __init__(self, api_key: str = None):
        """Initialize Ansari Agent.

        Args:
            api_key: Anthropic API key (uses config if not provided)
        """
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        # Set API key in environment for SDK
        os.environ["ANTHROPIC_API_KEY"] = self.api_key

        # Create MCP server with tools
        ansari_server = create_sdk_mcp_server(
            name="ansari_tools",
            version="1.0.0",
            tools=[search_quran]
        )

        # Configure SDK with tools via MCP SDK server
        options = ClaudeAgentOptions(
            mcp_servers={"ansari_tools": ansari_server},
            model="claude-3-7-sonnet-20250219",
            permission_mode="bypassPermissions",
            allowed_tools=["mcp__ansari_tools__search_quran"],
        )

        # Initialize SDK client
        self.client = ClaudeSDKClient(options=options)

        logger.info("Ansari Agent initialized with SearchQuran tool")

    async def connect(self):
        """Connect to the Claude SDK session."""
        await self.client.connect()
        logger.info("Connected to Claude SDK")

    async def disconnect(self):
        """Disconnect from the Claude SDK session."""
        await self.client.disconnect()
        logger.info("Disconnected from Claude SDK")

    async def query(self, message: str, session_id: str = "default") -> str:
        """Send a query to the agent.

        Args:
            message: User's question
            session_id: Session identifier for conversation continuity

        Returns:
            Agent's response as string
        """
        logger.info(f'User query: "{message}"')

        # Send message
        await self.client.query(message, session_id=session_id)

        # Receive complete response
        response_text = []
        async for msg in self.client.receive_response():
            logger.debug(f"Message type: {type(msg).__name__}, content: {msg}")

            # Extract text from message
            if hasattr(msg, "content"):
                if isinstance(msg.content, str):
                    response_text.append(msg.content)
                elif isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, dict) and "text" in block:
                            response_text.append(block["text"])
                        elif hasattr(block, "text"):
                            response_text.append(block.text)

        result = "".join(response_text)
        logger.debug(f"Final response length: {len(result)}")
        return result

    async def stream_query(self, message: str, session_id: str = "default"):
        """Send a query and stream the response.

        Args:
            message: User's question
            session_id: Session identifier for conversation continuity

        Yields:
            Response chunks
        """
        logger.info(f'Streaming query: "{message}"')

        await self.client.query(message, session_id=session_id)

        async for msg in self.client.receive_response():
            # Extract text from message
            if hasattr(msg, "content"):
                if isinstance(msg.content, str):
                    yield msg.content
                elif isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, dict) and "text" in block:
                            yield block["text"]
                        elif hasattr(block, "text"):
                            yield block.text
