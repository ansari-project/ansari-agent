# Ansari Agent - Multi-Model Islamic Knowledge Assistant

A high-performance model comparison interface for Islamic knowledge queries, supporting parallel execution of multiple LLMs with real-time streaming responses.

## Features

- **Multi-Model Support**: Compare responses from Claude (Opus, Sonnet) and Gemini (Pro, Flash) models side-by-side
- **Real-Time Streaming**: Token-by-token streaming for all models with SSE (Server-Sent Events)
- **Tool Integration**: Integrated Quran search capabilities via Kalimat API
- **Session Management**: Persistent conversation history with LRU eviction and TTL
- **Performance Optimized**: 3-9x faster response times through caching and pre-compilation
- **Secure**: HTTP Basic Auth protection with configurable credentials
- **Production Ready**: Deployed on Railway with health checks and monitoring

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (SPA)                   │
│            HTML + Vanilla JS + Marked.js            │
└─────────────────────────┬───────────────────────────┘
                          │ SSE
┌─────────────────────────┴───────────────────────────┐
│                  FastAPI Backend                     │
│                 model_comparison/                    │
├──────────────────────────────────────────────────────┤
│  ┌────────────────┐        ┌────────────────┐       │
│  │  LangGraph      │        │    Gemini      │       │
│  │  Integration    │        │   Integration  │       │
│  └────────┬────────┘        └────────┬───────┘       │
│           │                           │               │
│  ┌────────┴────────┐        ┌────────┴───────┐       │
│  │ Claude Models   │        │ Gemini Models  │       │
│  │ (Opus, Sonnet)  │        │ (Pro, Flash)   │       │
│  └─────────────────┘        └────────────────┘       │
└──────────────────────────────────────────────────────┘
                          │
                  ┌───────┴────────┐
                  │  Kalimat API   │
                  │ (Quran Search) │
                  └────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.13+
- API keys for Anthropic, Google, and Kalimat

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ansari-agent.git
cd ansari-agent

# Install dependencies with uv
uv sync

# Copy environment template
cp .env.example .env

# Add your API keys to .env:
# ANTHROPIC_API_KEY=your_key
# GOOGLE_API_KEY=your_key
# KALIMAT_API_KEY=your_key
```

### Running Locally

```bash
# Start the FastAPI server
PYTHONPATH=src uv run uvicorn model_comparison.app:app --reload

# Access the interface at http://localhost:8000
```

### Configuration

Key settings in `src/model_comparison/config.py`:
- `MAX_SESSIONS`: Maximum concurrent sessions (default: 50)
- `SESSION_TTL_SECONDS`: Session timeout (default: 1800)
- `MAX_HISTORY_TURNS`: Conversation history depth (default: 5)
- `WARM_UP_CLIENTS`: Pre-warm API clients on startup (default: true)

## API Endpoints

### Query Submission
```
POST /api/query
Authorization: Basic <credentials>
Content-Type: application/json

{
  "message": "What does the Quran say about patience?"
}

Response: {
  "session_id": "uuid-string"
}
```

### Streaming Responses
```
GET /api/stream/{session_id}
Authorization: Basic <credentials>
Accept: text/event-stream

Returns: Server-Sent Events stream with model responses
```

## Deployment

### Railway Deployment

The application is configured for Railway deployment with automatic builds:

```bash
# Deploy to Railway
railway up

# Set environment variables
railway variables set ANTHROPIC_API_KEY=your_key
railway variables set GOOGLE_API_KEY=your_key
railway variables set KALIMAT_API_KEY=your_key
```

See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for detailed deployment instructions.

## Performance

Optimizations implemented:
- **LLM Client Caching**: Singleton pattern with `@lru_cache` reduces initialization overhead
- **Graph Pre-compilation**: LangGraph instances compiled at startup
- **Connection Pooling**: Reused HTTP connections for API calls
- **Concurrent Execution**: `asyncio.TaskGroup` for parallel model queries

Results:
- Initial response time: 73-83 seconds
- Optimized response time: 8-29 seconds (3-9x improvement)
- TTFT (Time to First Token): <1 second for all models

## Project Structure

```
ansari-agent/
├── src/
│   ├── model_comparison/      # FastAPI application
│   │   ├── app.py             # Main application
│   │   ├── endpoints.py       # API routes
│   │   ├── streaming.py       # SSE utilities
│   │   ├── session.py         # Session management
│   │   └── langgraph_adapter.py # LangGraph integration
│   ├── ansari_langgraph/      # Claude integration
│   │   ├── agent.py           # LangGraph agent
│   │   ├── nodes.py           # Graph nodes
│   │   └── tools.py           # Tool definitions
│   └── ansari_gemini/         # Gemini integration
│       ├── agent.py           # Gemini agent
│       ├── nodes.py           # Graph nodes
│       └── tools.py           # Tool definitions
├── tests/                     # Test suite
├── legacy/                    # Deprecated Claude SDK code
└── codev/                     # Development documentation
    ├── specs/                 # Feature specifications
    ├── plans/                 # Implementation plans
    └── reviews/               # Code reviews
```

## Development

### Testing

```bash
# Run all tests
PYTHONPATH=src uv run pytest tests/ -v

# Run specific test
PYTHONPATH=src uv run pytest tests/test_langgraph_integration.py -v
```

### Adding a New Model

1. Create a new integration module in `src/`
2. Implement the agent following the LangGraph pattern
3. Add model configuration to `config.py`
4. Update `langgraph_adapter.py` to support the new model

## Contributing

This project follows the Codev/SPIDER protocol for development. See [codev/protocols/](codev/protocols/) for methodology details.

## License

MIT

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- Uses [Kalimat API](https://api.kalimat.dev) for Quran search
- Deployed on [Railway](https://railway.app)