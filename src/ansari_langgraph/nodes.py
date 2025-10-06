"""Graph nodes for Ansari LangGraph implementation."""

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from ansari_agent.utils import setup_logger
from ansari_langgraph.state import AnsariState
from ansari_langgraph.tools import search_quran

logger = setup_logger(__name__)


# System message
SYSTEM_MESSAGE = """You are Ansari, an Islamic knowledge assistant.

When answering questions about Islam, the Quran, or Islamic teachings:
- Use the search_quran tool to find relevant ayahs
- Provide accurate citations
- Be respectful and educational
- Cite your sources using the ayah references"""


def create_agent_node(llm_with_tools):
    """Create an agent node with a pre-configured LLM client.

    Args:
        llm_with_tools: A pre-configured LangChain runnable (LLM bound with tools)

    Returns:
        Agent node function
    """

    async def agent_node(state: AnsariState) -> AnsariState:
        """Agent node - calls LLM with tools using LangChain."""
        logger.debug("→ Agent node executing...")

        messages = state.get("messages", [])

        # Convert Anthropic message format to LangChain format
        lc_messages = [SystemMessage(content=SYSTEM_MESSAGE)]

        for msg in messages:
            if msg["role"] == "user":
                content = msg["content"]

                # Check if content contains tool_result blocks
                if isinstance(content, list) and content and isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                    # Convert tool_result blocks to ToolMessage objects
                    for tool_result in content:
                        lc_messages.append(ToolMessage(
                            content=tool_result["content"],
                            tool_call_id=tool_result["tool_use_id"],
                        ))
                else:
                    # Regular user message
                    lc_messages.append(HumanMessage(content=content))

            elif msg["role"] == "assistant":
                # Check if this message has tool_calls
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    # Create AIMessage with tool_calls
                    lc_messages.append(AIMessage(
                        content=msg.get("content", ""),
                        tool_calls=tool_calls,
                    ))
                else:
                    lc_messages.append(AIMessage(content=msg["content"]))

        # Call LLM with tools
        response = await llm_with_tools.ainvoke(lc_messages)

        # Track token usage
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = state.get("input_tokens", 0)
            output_tokens = state.get("output_tokens", 0)

            input_tokens += response.usage_metadata.get("input_tokens", 0)
            output_tokens += response.usage_metadata.get("output_tokens", 0)

            state["input_tokens"] = input_tokens
            state["output_tokens"] = output_tokens

        # Check if there are tool calls
        if response.tool_calls:
            logger.debug(f"LLM requested {len(response.tool_calls)} tool calls")

            tool_calls = []
            for tool_call in response.tool_calls:
                tool_calls.append({
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "args": tool_call["args"],
                })
                logger.info(f"Tool call: {tool_call['name']} with input: {tool_call['args']}")

            state["tool_calls"] = tool_calls
            state["stop_reason"] = "tool_use"

            # Add assistant message with tool_use to history (in Anthropic format)
            # LangChain's response.content may be empty when there are tool calls
            # Store tool_calls in the message so we can reconstruct proper LangChain messages
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": tool_calls,
            })
            state["messages"] = messages

        else:
            # No tool calls - this is the final response
            logger.debug("LLM returned final response")

            # Handle both string and list content formats
            final_text = response.content
            if isinstance(final_text, list):
                # Extract text from content blocks
                final_text = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in final_text
                )

            # Log warning if response is empty
            if not final_text:
                logger.warning(f"Empty final response from LLM. Response type: {type(response.content)}, Raw content: {response.content}")
                logger.warning(f"Full response object: {response}")

            state["final_response"] = final_text
            state["stop_reason"] = "end_turn"

            # Add assistant message to history
            messages.append({
                "role": "assistant",
                "content": final_text,
            })
            state["messages"] = messages

            logger.debug(f"Final response length: {len(final_text)}")

        return state

    return agent_node


async def tool_node(state: AnsariState) -> AnsariState:
    """Tool node - executes tools and formats results for Anthropic."""
    logger.debug("→ Tool node executing...")

    tool_calls = state.get("tool_calls", [])
    messages = state.get("messages", [])

    tool_results = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]
        tool_id = tool_call["id"]

        logger.info(f"Executing tool: {tool_name}")

        # Execute the tool
        if tool_name == "search_quran":
            result = await search_quran.ainvoke(tool_input)
        else:
            logger.warning(f"Unknown tool: {tool_name}")
            result = {"error": f"Unknown tool: {tool_name}"}

        tool_results.append({
            "tool_use_id": tool_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "result": result,
        })

        logger.debug(f"Tool result: {result.get('count', 0)} ayahs found")

    # Format tool results for Anthropic (must include tool_use_id and content)
    tool_result_blocks = []
    for tr in tool_results:
        # Format the result as text with citations
        result_data = tr["result"]

        if "error" in result_data:
            content_text = f"Error: {result_data['error']}"
        elif result_data.get("count", 0) == 0:
            content_text = "No results found."
        else:
            # Format each ayah with citation
            ayahs = result_data.get("results", [])
            formatted_ayahs = []

            for ayah in ayahs:
                formatted_ayahs.append(
                    f"**{ayah['citation']}**\n"
                    f"Arabic: {ayah['arabic']}\n"
                    f"English: {ayah['english']}\n"
                )

            content_text = "\n---\n".join(formatted_ayahs)

            # Store citations in state
            citations = state.get("citations", [])
            citations.extend(ayahs)
            state["citations"] = citations

        tool_result_blocks.append({
            "type": "tool_result",
            "tool_use_id": tr["tool_use_id"],
            "content": content_text,
        })

    # Add tool results to message history
    messages.append({
        "role": "user",
        "content": tool_result_blocks,
    })

    state["messages"] = messages
    state["tool_results"] = tool_results

    logger.info(f"Completed {len(tool_results)} tool calls")

    return state


async def finalize_node(state: AnsariState) -> AnsariState:
    """Finalize node - formats final response."""
    logger.debug("→ Finalize node executing...")

    final_response = state.get("final_response", "")
    citations = state.get("citations", [])

    logger.info(f"Final response ready ({len(final_response)} chars, {len(citations)} citations)")

    return state
