"""Graph nodes for Ansari Gemini implementation."""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from ansari_agent.utils import config, setup_logger
from ansari_gemini.state import AnsariState
from ansari_gemini.tools import search_quran

logger = setup_logger(__name__)


# System message
SYSTEM_MESSAGE = """You are Ansari, an Islamic knowledge assistant.

When answering questions about Islam, the Quran, or Islamic teachings:
- Use the search_quran tool to find relevant ayahs
- Provide accurate citations
- Be respectful and educational
- Cite your sources using the ayah references"""


def create_agent_node(model: str = "gemini-2.5-pro"):
    """Create an agent node with the specified Gemini model.

    Args:
        model: Gemini model name (gemini-2.5-pro or gemini-2.5-flash)

    Returns:
        Agent node function
    """
    # Initialize ChatGoogleGenerativeAI with specified model
    # NOTE: Streaming is disabled because ainvoke() doesn't populate response.content when streaming=True
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=config.GOOGLE_API_KEY,
        max_tokens=16384,  # Allow longer responses
        temperature=0,
        streaming=False,  # Must be False for non-streaming ainvoke() path. Streaming handled via astream_events in agent.py
    )

    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools([search_quran])

    async def agent_node(state: AnsariState) -> AnsariState:
        """Agent node - calls LLM with tools using LangChain."""
        logger.debug("→ Agent node executing...")

        messages = state.get("messages", [])
        tool_call_count = state.get("tool_call_count", 0)

        # CRITICAL GUARDRAIL: Limit tool calls to prevent infinite loops (Gemini issue)
        MAX_TOOL_CALLS = 5

        if tool_call_count >= MAX_TOOL_CALLS:
            logger.warning(f"Tool call limit reached ({tool_call_count} calls). Forcing final answer.")

            # Force LLM to answer without tools
            lc_messages = [
                SystemMessage(content=SYSTEM_MESSAGE),
                HumanMessage(content="You have made several searches. Please provide a final answer based on the information you've gathered. Do not call any more tools.")
            ]

            # Add conversation history (just the tool results)
            for msg in messages:
                if msg["role"] == "user":
                    content = msg.get("content", "")
                    if isinstance(content, list) and len(content) > 0 and content[0].get("type") == "tool_result":
                        for tool_result_block in content:
                            lc_messages.append(ToolMessage(
                                content=tool_result_block["content"],
                                tool_call_id=tool_result_block["tool_use_id"],
                            ))

            # Call WITHOUT tools to force answer
            response = await llm.ainvoke(lc_messages)

            # Track token usage
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tokens = state.get("input_tokens", 0)
                output_tokens = state.get("output_tokens", 0)

                input_tokens += response.usage_metadata.get("input_tokens", 0)
                output_tokens += response.usage_metadata.get("output_tokens", 0)

                state["input_tokens"] = input_tokens
                state["output_tokens"] = output_tokens

            # Mark as forced answer
            state["forced_answer"] = True
            state["final_response"] = response.content
            state["stop_reason"] = "end_turn"

            messages.append({
                "role": "assistant",
                "content": response.content,
            })
            state["messages"] = messages

            return state

        # Normal flow: Convert to LangChain format
        lc_messages = [SystemMessage(content=SYSTEM_MESSAGE)]

        for msg in messages:
            if msg["role"] == "user":
                # Check if this is a tool result message
                content = msg.get("content", "")
                if isinstance(content, list) and len(content) > 0 and content[0].get("type") == "tool_result":
                    # This is a tool result - convert to ToolMessage
                    for tool_result_block in content:
                        lc_messages.append(ToolMessage(
                            content=tool_result_block["content"],
                            tool_call_id=tool_result_block["tool_use_id"],
                        ))
                else:
                    # Regular user message
                    lc_messages.append(HumanMessage(content=content))
            elif msg["role"] == "assistant":
                # CRITICAL: Restore tool_calls so Gemini knows it already called them
                tc = msg.get("tool_calls")
                if tc:
                    lc_messages.append(AIMessage(content=msg.get("content", ""), tool_calls=tc))
                else:
                    lc_messages.append(AIMessage(content=msg.get("content", "")))

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
                    "input": tool_call["args"],
                })
                logger.info(f"Tool call: {tool_call['name']} with input: {tool_call['args']}")

            state["tool_calls"] = tool_calls
            state["stop_reason"] = "tool_use"

            # Add assistant message with tool_use to history
            # CRITICAL: Must preserve tool_calls so Gemini remembers it made them
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {"id": tc["id"], "name": tc["name"], "args": tc["args"]}
                    for tc in response.tool_calls
                ],
            })
            state["messages"] = messages

        else:
            # No tool calls - this is the final response
            logger.debug("LLM returned final response")

            # Gemini may return empty content - use .text property if available
            final_text = response.content
            if not final_text and hasattr(response, 'text'):
                final_text = response.text
            if isinstance(final_text, list):
                # Extract text from content blocks
                final_text = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in final_text
                )

            # Ensure final_text is a string
            if not isinstance(final_text, str):
                final_text = str(final_text) if final_text else ""

            logger.info(f"Final text extracted: {len(final_text)} chars")

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
    """Tool node - executes tools and formats results."""
    logger.debug("→ Tool node executing...")

    tool_calls = state.get("tool_calls", [])
    messages = state.get("messages", [])
    tool_call_count = state.get("tool_call_count", 0)

    # Increment tool call counter
    tool_call_count += len(tool_calls)
    state["tool_call_count"] = tool_call_count
    logger.debug(f"Tool call count: {tool_call_count}")

    tool_results = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["input"]
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
            "result": result,
        })

        logger.debug(f"Tool result: {result.get('count', 0)} ayahs found")

    # Format tool results
    tool_result_blocks = []
    for tr in tool_results:
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
