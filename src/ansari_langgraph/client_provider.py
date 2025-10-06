"""Singleton LLM client provider with caching."""

import logging
from functools import lru_cache
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from ansari_agent.utils import config
from ansari_langgraph.tools import search_quran

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def get_llm_with_tools(model: str):
    """Get a cached, tool-bound LLM instance.

    This function uses LRU cache to ensure singleton instances of each LLM client.
    Clients are created once and reused across all requests.

    Args:
        model: Model identifier (Anthropic or Gemini model name)

    Returns:
        LangChain runnable (LLM bound with tools)
    """
    logger.debug(f"Creating LLM client for {model}")

    is_gemini = model.startswith("gemini")

    if is_gemini:
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=config.GOOGLE_API_KEY,
            # Let model use its default max_output_tokens
            temperature=0,
            streaming=True,
        )
    else:
        llm = ChatAnthropic(
            model=model,
            api_key=config.ANTHROPIC_API_KEY,
            default_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            # Let model use its default max_tokens
            temperature=0,
            streaming=True,
        )

    logger.debug(f"Binding tools to {model}")
    return llm.bind_tools([search_quran])
