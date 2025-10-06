"""Model pricing utilities with tool cost support."""

# Pricing per million tokens (as of 2025-10)
# Source: https://www.anthropic.com/pricing and https://ai.google.dev/pricing

ANTHROPIC_PRICING = {
    "claude-sonnet-4-20250514": {
        "input": 3.00,  # $3.00 per MTok
        "output": 15.00,  # $15.00 per MTok
    },
    "claude-sonnet-4-5-20250929": {  # Correct model ID
        "input": 3.00,  # $3.00 per MTok
        "output": 15.00,  # $15.00 per MTok
    },
    "claude-opus-4-20250514": {
        "input": 15.00,  # $15.00 per MTok
        "output": 75.00,  # $75.00 per MTok
    },
}

GEMINI_PRICING = {
    "gemini-2.5-pro": {
        "input": 1.25,  # $1.25 per MTok
        "output": 5.00,  # $5.00 per MTok
    },
    "gemini-2.5-flash": {
        "input": 0.075,  # $0.075 per MTok
        "output": 0.30,  # $0.30 per MTok
    },
}

# Tool usage costs (estimated tokens)
TOOL_COSTS = {
    "search_quran": {
        "input_overhead": 200,   # Tokens for tool definition/schema
        "output_overhead": 500,  # Tokens for typical response with citations
    }
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int, tool_calls: int = 0) -> dict:
    """Calculate cost for a model based on actual token usage.

    The token counts provided already include ALL tokens (including tool usage)
    as reported by the LLM's usage_metadata.

    Args:
        model: Model identifier
        input_tokens: Actual number of input tokens from LLM usage_metadata
        output_tokens: Actual number of output tokens from LLM usage_metadata
        tool_calls: Number of tool calls made (for display only)

    Returns:
        Dict with detailed cost breakdown
    """
    # Token counts already include everything - no overhead to add

    # Get pricing
    pricing = None
    if model in ANTHROPIC_PRICING:
        pricing = ANTHROPIC_PRICING[model]
    elif model in GEMINI_PRICING:
        pricing = GEMINI_PRICING[model]

    if pricing:
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
            "tokens_in": input_tokens,
            "tokens_out": output_tokens,
            "tool_calls": tool_calls,
        }

    # Unknown model
    return {
        "input_cost": 0,
        "output_cost": 0,
        "total_cost": 0,
        "tokens_in": input_tokens,
        "tokens_out": output_tokens,
        "tool_calls": tool_calls,
        "error": f"No pricing for model {model}"
    }


def format_cost(cost: float) -> str:
    """Format cost for display.

    Args:
        cost: Cost in USD

    Returns:
        Formatted cost string
    """
    if cost >= 0.01:
        return f"${cost:.4f}"
    else:
        return f"${cost:.6f}"
