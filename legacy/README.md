# Legacy Code - Claude Agent SDK Implementation

## Status: DEPRECATED - For Reference Only

This directory contains the original Claude Agent SDK prototype that was evaluated and ultimately rejected for production use.

## Contents

- `ansari_agent/` - Original agent implementation using claude-agent-sdk
- `examples/` - Example scripts using the deprecated SDK approach
- `test_agent.py`, `test_search_quran.py` - Tests for the deprecated implementation

## Why Deprecated

After evaluation (see `/codev/reviews/0001-claude-sdk-evaluation.md`), the Claude Agent SDK was found unsuitable because:

1. **CLI Dependency**: Requires Claude Code CLI installed via npm
2. **Subprocess Architecture**: SDK spawns CLI subprocess, adding complexity
3. **Not a True SDK**: It's a wrapper around the Claude Code CLI, not a standalone SDK
4. **Deployment Complexity**: Requires Node.js in production environments

## Current Implementation

The project now uses:
- **LangGraph** for agent orchestration (see `src/ansari_langgraph/`)
- **Gemini** backend support (see `src/ansari_gemini/`)
- **Model Comparison UI** with FastAPI (see `src/model_comparison/`)

## Preservation Reason

This code is preserved for:
- Historical reference
- Potential future revisit if SDK matures
- Documentation of exploration path

## Note

Do not import or use this code in production. It requires `claude-agent-sdk==0.1.0` which should be removed from dependencies.