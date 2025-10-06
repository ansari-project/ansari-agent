# LLM Model Comparison

Compare 4 LLM models side-by-side with real-time streaming, latency tracking, and tool usage visualization.

## Features

- **4 Models**: Gemini 2.5 Pro, Gemini 2.5 Flash, Claude Opus 4.1, Claude Sonnet 4.5
- **Real-time Streaming**: See responses as they're generated
- **Latency Metrics**: TTFT (Time to First Token) and total response time
- **Tool Tracking**: Visualize which tools each model uses
- **Token Counts**: Input and output token tracking
- **Multi-turn Conversations**: Session-based chat history
- **Responsive UI**: Works on desktop, tablet, and mobile

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Set Up Environment Variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required variables:
- `ANTHROPIC_API_KEY` - Your Anthropic API key for Claude models
- `GOOGLE_API_KEY` - Your Google AI API key for Gemini models

Optional variables (for HTTP Basic Auth):
- `MODEL_COMPARISON_AUTH_USERNAME` - Default: `admin`
- `MODEL_COMPARISON_AUTH_PASSWORD` - Leave blank to disable auth

### 3. Run the Server

```bash
PYTHONPATH=src uv run uvicorn model_comparison.app:app --host 0.0.0.0 --port 8000
```

### 4. Open in Browser

Navigate to: http://localhost:8000

## Usage

1. **Enter a question** in the text box
2. **Click Send** or press Ctrl+Enter
3. **Watch all 4 models** respond in real-time
4. **Compare** their speed, quality, and tool usage
5. **Continue the conversation** or click Clear to start fresh

## Authentication

By default, authentication is **disabled** for easy local development.

To enable HTTP Basic Auth:
1. Set `MODEL_COMPARISON_AUTH_PASSWORD` in your `.env` file
2. Restart the server
3. You'll be prompted for credentials when accessing the UI

## Railway Deployment

### Prerequisites

1. Railway account: https://railway.app
2. API keys for Anthropic and Google AI

### Deploy Steps

1. **Create new project** in Railway
2. **Connect your repository**
3. **Set environment variables** in Railway dashboard:
   - `ANTHROPIC_API_KEY`
   - `GOOGLE_API_KEY`
   - `MODEL_COMPARISON_AUTH_PASSWORD` (recommended for production)
4. **Deploy** - Railway will automatically detect the `railway.toml` configuration

Railway will:
- Build using Nixpacks
- Run health checks on `/health`
- Auto-restart on failures
- Use a single worker (required for in-memory sessions)

## Architecture

- **Backend**: FastAPI with async/await
- **Streaming**: Server-Sent Events (SSE)
- **Session Management**: In-memory with LRU eviction (15 min TTL)
- **Concurrency**: asyncio.TaskGroup for parallel model streaming
- **Frontend**: Single-page HTML/CSS/JS (no build step)

## API Endpoints

- `GET /` - Main UI
- `GET /health` - Health check (for Railway)
- `POST /api/query` - Submit query, get session_id
- `GET /api/stream/{session_id}` - SSE stream with model responses
- `POST /api/cancel/{session_id}` - Cancel in-flight generation
- `GET /debug` - Debug UI for SSE event inspection (auth required if enabled)
- `GET /debug/memory` - Memory usage stats (auth required if enabled)

## Development

### Run Tests

```bash
PYTHONPATH=src uv run pytest
```

### Check Code Quality

```bash
# Complexity analysis
radon cc src/model_comparison -a

# Line count
cloc src/model_comparison
```

### Debug SSE Streaming

Open http://localhost:8000/debug to see raw SSE events.

## Troubleshooting

### "ModuleNotFoundError: No module named 'model_comparison'"

Make sure to set `PYTHONPATH=src` before running:
```bash
PYTHONPATH=src uv run uvicorn model_comparison.app:app
```

### "ANTHROPIC_API_KEY environment variable is required"

Create a `.env` file with your API keys (see Step 2 in Quick Start).

### Models not streaming

Check that both API keys are valid and have sufficient quota.

### Railway timeout errors

The server has a 25-second timeout per model. Very long responses may be truncated.

## License

This is an exploratory prototype for evaluating LLM model comparison approaches.
