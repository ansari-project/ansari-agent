# Ansari Agent - Claude SDK Prototype

Prototype implementation of Ansari using Claude Agent SDK for evaluation purposes.

## Status

✅ **Working Prototype** - Successfully demonstrates:
- Claude Agent SDK integration
- SearchQuran tool integration
- Citation metadata preservation
- Multi-turn conversations with session management
- Concurrent user handling (one agent instance per user)

## Quick Start

### Prerequisites

- Python 3.13+
- Claude Code CLI installed (`npm install -g @anthropic-ai/claude-code`)
- API keys configured in `.env`

### Installation

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Add your API keys to .env
# ANTHROPIC_API_KEY=your_key
# KALIMAT_API_KEY=your_key
```

### Usage

**Simple Query:**

```python
from ansari_agent.core import AnsariAgent
import anyio

async def main():
    agent = AnsariAgent()
    await agent.connect()

    try:
        response = await agent.query("What does the Quran say about patience?")
        print(response)
    finally:
        await agent.disconnect()

anyio.run(main)
```

**Run Examples:**

```bash
# Simple single query
env PYTHONPATH=src uv run python examples/simple_query.py

# Multi-user simulation
env PYTHONPATH=src uv run python examples/multi_user_simulation.py
```

## Architecture

```
User → AnsariAgent → ClaudeSDKClient → Claude CLI → Anthropic API
                  ↓
            SearchQuran Tool → Kalimat API
```

### Key Components

- **AnsariAgent** ([src/ansari_agent/core/agent.py](src/ansari_agent/core/agent.py))
  - Wraps ClaudeSDKClient
  - Manages connection lifecycle
  - Provides simple query/stream interfaces

- **SearchQuran Tool** ([src/ansari_agent/tools/search_quran.py](src/ansari_agent/tools/search_quran.py))
  - SDK tool decorator pattern
  - Async Kalimat API integration
  - Returns structured content with citation metadata

## Multi-User Support

Each user requires:
- Separate `AnsariAgent` instance
- Unique `session_id` for conversation continuity
- Independent connection lifecycle

**Example:**

```python
# User 1
agent1 = AnsariAgent()
await agent1.connect()
response1 = await agent1.query("Question 1", session_id="user_1")

# User 2 (concurrent)
agent2 = AnsariAgent()
await agent2.connect()
response2 = await agent2.query("Question 2", session_id="user_2")
```

See [examples/multi_user_simulation.py](examples/multi_user_simulation.py) for full example.

## Testing

```bash
# Test SearchQuran tool
env PYTHONPATH=src uv run python tests/test_search_quran.py

# Test full agent
env PYTHONPATH=src uv run python tests/test_agent.py
```

## Evaluation Results

**What Works:**
- ✅ Tool integration (SearchQuran successfully integrated)
- ✅ Citation metadata preserved through tool calls
- ✅ Multi-turn conversations via session IDs
- ✅ Concurrent users (separate agent instances)
- ✅ Streaming responses

**Architecture Notes:**
- SDK requires Claude Code CLI (spawns subprocess per agent)
- Each agent instance = one CLI subprocess
- Session state managed via session_id parameter
- External conversation persistence still needed for production

**Full Evaluation:** See [codev/reviews/0001-claude-sdk-evaluation.md](codev/reviews/0001-claude-sdk-evaluation.md)

## Project Structure

```
ansari-agent/
├── src/ansari_agent/
│   ├── core/
│   │   └── agent.py          # Main agent implementation
│   ├── tools/
│   │   └── search_quran.py   # SearchQuran tool
│   └── utils/
│       ├── config.py          # Configuration management
│       └── logger.py          # Logging setup
├── tests/
│   ├── test_agent.py          # Agent integration tests
│   └── test_search_quran.py   # Tool tests
├── examples/
│   ├── simple_query.py        # Basic usage
│   └── multi_user_simulation.py  # Multi-user example
└── codev/
    ├── specs/                 # Feature specifications
    ├── plans/                 # Implementation plans
    └── reviews/               # Evaluation reviews
```

## Development

This project uses the Codev/SPIDER protocol for development:

- **Specification**: [codev/specs/0001-claude-sdk-evaluation.md](codev/specs/0001-claude-sdk-evaluation.md)
- **Plan**: [codev/plans/0001-claude-sdk-evaluation.md](codev/plans/0001-claude-sdk-evaluation.md)
- **Review**: [codev/reviews/0001-claude-sdk-evaluation.md](codev/reviews/0001-claude-sdk-evaluation.md)

## License

MIT
