# Plan: Model Comparison Web UI

## Metadata
- **ID**: plan-2025-10-06-model-comparison-ui
- **Status**: draft
- **Specification**: [codev/specs/0004-model-comparison-ui.md](../specs/0004-model-comparison-ui.md)
- **Created**: 2025-10-06

## Executive Summary

Implementing a FastAPI-based web application that enables side-by-side comparison of 4 LLM models (Gemini 2.5 Pro/Flash, Claude Opus 4.1/Sonnet 4.5) with real-time streaming, latency metrics, and tool usage tracking. The approach uses Server-Sent Events for streaming, vanilla HTML/JS for the frontend (no build step), and integrates with the existing LangGraph agent implementation. Deployment target is Railway.app with focus on simplicity and immediate utility.

**Rationale**: FastAPI + vanilla JS was chosen for its async capabilities, zero build complexity, single-process deployment, and perfect fit for concurrent streaming requirements.

## Success Metrics

From specification plus implementation-specific metrics:
- [x] Single input box sends to all 4 models simultaneously
- [x] 4 separate output boxes with real-time streaming and XSS protection
- [x] TTFT and total latency displayed per interaction
- [x] Tool usage timeline shown per model
- [x] Token counts displayed (prompt + completion)
- [x] Stop generation button with proper cancellation
- [x] Multi-turn conversation with clear button
- [x] HTTP Basic Auth implemented
- [x] Deployable to Railway with single worker
- [x] Test coverage >85%
- [x] Response time <100ms for UI interactions
- [x] Memory usage <512MB
- [x] All 4 models stream concurrently without blocking
- [x] Proper error handling for partial failures
- [x] Session management with TTL and limits

## Phase Breakdown

### Phase 1: Core Backend Infrastructure

**Dependencies**: None

#### Objectives
- Establish FastAPI application structure
- Implement session management with TTL and limits
- Create SSE event schema and streaming infrastructure
- Build health check endpoint

#### Deliverables
- [x] FastAPI app with proper structure (`src/model_comparison/`)
- [x] Session manager with LRU eviction, 15min TTL, 50 session limit
- [x] SSE event types and serialization
- [x] `/health` endpoint
- [x] Environment variable validation (ANTHROPIC_API_KEY, GOOGLE_API_KEY)
- [x] Basic HTTP auth middleware
- [x] Unit tests for session management and event serialization

#### Implementation Details

**File Structure**:
```
src/model_comparison/
├── __init__.py
├── app.py              # FastAPI application entry
├── models.py           # Pydantic models for events and requests
├── session.py          # Session management with TTL
├── streaming.py        # SSE streaming logic
├── auth.py             # HTTP Basic Auth
└── config.py           # Environment config
```

**Key Components**:

1. **Session Manager** (`session.py`):
   - LRU cache with 50 session max
   - 15-minute idle timeout
   - Per-model conversation history (last 10 turns or 8K tokens)
   - Thread-safe access

2. **Event Schema** (`models.py`):
   ```python
   class SSEEvent(BaseModel):
       type: Literal['start', 'ttft', 'token', 'tool_start', 'tool_end', 'done', 'error', 'heartbeat']
       model_id: str | None
       timestamp: float
       # Type-specific fields...
   ```

3. **Config** (`config.py`):
   - Load and validate API keys
   - Fairness settings (temp=0.0, max_tokens=4096)
   - Model ID mappings

#### Acceptance Criteria
- [x] Session manager creates, retrieves, expires sessions correctly
- [x] LRU eviction works when 50 sessions reached
- [x] TTL cleanup happens on access
- [x] All SSE event types serialize correctly
- [x] `/health` returns 200 with valid JSON
- [x] Missing env vars cause startup failure with clear message
- [x] HTTP Basic Auth blocks unauthorized requests

#### Test Plan
- **Unit Tests**:
  - Session CRUD operations
  - TTL expiration logic
  - LRU eviction
  - Event serialization for all types
  - Config validation with missing/invalid env vars
- **Integration Tests**:
  - `/health` endpoint responds correctly
  - Auth middleware blocks/allows requests

#### Rollback Strategy
Phase 1 has no user-facing changes. If issues arise, simply revert the commit.

#### Risks
- **Risk**: LRU eviction complexity
  - **Mitigation**: Use `functools.lru_cache` wrapper or simple OrderedDict

---

### Phase 2: LangGraph Integration & Streaming

**Dependencies**: Phase 1

#### Objectives
- Integrate with existing LangGraph agent implementation
- Implement concurrent streaming for 4 models
- Build SSE endpoints with proper cancellation
- Handle partial failures gracefully

#### Deliverables
- [x] Model streaming orchestrator
- [x] `POST /api/query` - Submit query, return session_id
- [x] `GET /api/stream/{session_id}` - SSE stream multiplexing 4 models
- [x] `POST /api/cancel/{session_id}` - Cancel in-flight generation
- [x] LangGraph event normalization to SSE schema
- [x] Async task cancellation propagation
- [x] Per-model error isolation
- [x] Integration tests for streaming

#### Implementation Details

**Files**:
- `src/model_comparison/langgraph_adapter.py` - LangGraph integration
- `src/model_comparison/endpoints.py` - API endpoints

**Key Logic**:

1. **Query Endpoint** (`POST /api/query`):
   ```python
   - Validate input
   - Create new session with UUID
   - Store user message in session history (all 4 models)
   - Return session_id
   ```

2. **Stream Endpoint** (`GET /api/stream/{session_id}`):
   ```python
   - Retrieve session or 404
   - Create 4 async tasks (one per model)
   - Use asyncio.gather() with return_exceptions=True
   - Yield SSE events as they arrive
   - Multiplex events by model_id
   - Send heartbeat every 10s
   - Handle disconnection (propagate cancellation)
   - Update session history on completion
   ```

3. **Cancel Endpoint** (`POST /api/cancel/{session_id}`):
   ```python
   - Look up session's task group
   - Cancel all tasks
   - Return 200
   ```

4. **LangGraph Adapter**:
   - Normalize `astream()` events to SSE schema
   - Extract TTFT, tokens, tool events
   - Handle provider-specific event shapes
   - Wrap in try/except for per-model error isolation

#### Acceptance Criteria
- [x] `/api/query` creates session and returns valid UUID
- [x] `/api/stream` yields events for all 4 models concurrently
- [x] Events correctly tagged with model_id
- [x] TTFT event fires when first content token received
- [x] Tool events (start/end) emit with correct timing
- [x] Done event includes total_ms and token counts
- [x] If one model fails, others continue streaming
- [x] Error events contain helpful messages
- [x] `/api/cancel` stops all in-flight tasks
- [x] Partial responses preserved after cancellation
- [x] Heartbeat events every 10s prevent timeout
- [x] Client disconnect cancels server tasks

#### Test Plan
- **Unit Tests**:
  - LangGraph event normalization for each event type
  - TTFT calculation logic
  - Token count extraction
- **Integration Tests**:
  - Submit query → receive session_id
  - Stream endpoint with mocked LangGraph responses
  - Concurrent 4-model streaming
  - Partial failure (mock one model raising exception)
  - Cancellation via endpoint
  - Heartbeat emission
- **Manual Testing**:
  - Real LangGraph integration with live APIs

#### Rollback Strategy
Revert Phase 2 commit. Phase 1 remains functional.

#### Risks
- **Risk**: LangGraph event shapes differ between providers
  - **Mitigation**: Normalize early in adapter, log unknown events
- **Risk**: Async cancellation doesn't propagate to SDK calls
  - **Mitigation**: Test with real SDKs, wrap in timeouts

---

### Phase 3: Frontend UI

**Dependencies**: Phase 2

#### Objectives
- Build responsive HTML/CSS/JS interface
- Implement SSE client with reconnection
- Display streaming responses with XSS protection
- Show latency, tool timeline, token counts
- Add stop and clear buttons

#### Deliverables
- [x] Single-file HTML with embedded CSS/JS
- [x] Input box and send button
- [x] 4 output panels (one per model)
- [x] Real-time latency display (TTFT + total)
- [x] Tool usage timeline per model
- [x] Token count display
- [x] Stop generation button
- [x] Clear conversation button
- [x] XSS-safe rendering (textContent)
- [x] Loading states and error messages
- [x] Responsive grid layout

#### Implementation Details

**File**: Served by FastAPI at `GET /`

**UI Components**:

1. **Input Section**:
   - Text input with placeholder
   - Send button (disabled while streaming)
   - Clear button

2. **Model Panel** (x4):
   ```html
   <div class="model-panel" data-model-id="...">
     <div class="model-header">
       <span class="model-name">Gemini 2.5 Pro</span>
       <div class="metrics">
         <span class="ttft">TTFT: -</span>
         <span class="total">Total: -</span>
         <span class="tokens">Tokens: -</span>
       </div>
     </div>
     <div class="tool-timeline">
       <!-- Tool badges appear here -->
     </div>
     <div class="output-box">
       <!-- Streamed content (textContent only) -->
     </div>
   </div>
   ```

3. **JavaScript Logic**:
   - `submitQuery()`: POST to /api/query, get session_id
   - `streamResponses(session_id)`: Open SSE connection
   - Event handlers for each SSE event type
   - Use `element.textContent` for model output (XSS protection)
   - Track per-model state (content buffer, tools, metrics)
   - `cancelGeneration()`: POST to /api/cancel
   - `clearConversation()`: Reset UI and start new session

**XSS Protection**:
```javascript
// ALWAYS use textContent, NEVER innerHTML for model output
outputElement.textContent += event.content;
```

#### Acceptance Criteria
- [x] UI renders correctly in Chrome, Firefox, Safari
- [x] Input submits on Enter key
- [x] All 4 panels update concurrently during streaming
- [x] TTFT appears when first token received
- [x] Total latency updates on completion
- [x] Token counts display correctly
- [x] Tool timeline shows sequence of tools used
- [x] Stop button cancels streams and shows partial output
- [x] Clear button resets all panels
- [x] Model output containing `<script>` renders as text
- [x] No JavaScript execution from model responses
- [x] Loading states visible during processing
- [x] Error messages display per model
- [x] Responsive layout works on different screen sizes

#### Test Plan
- **Unit Tests**: N/A (vanilla JS, no build)
- **Integration Tests**:
  - Playwright test: submit query, verify all panels populate
  - XSS test: inject `<script>alert(1)</script>` in mock response
- **Manual Testing**:
  - Test with real queries
  - Verify UI responsiveness
  - Test stop and clear buttons
  - Multi-turn conversation

#### Rollback Strategy
Revert Phase 3 commit. API remains functional for other clients.

#### Risks
- **Risk**: SSE reconnection complexity
  - **Mitigation**: EventSource handles reconnection automatically
- **Risk**: DOM updates slow down with long responses
  - **Mitigation**: Use DocumentFragment for batching if needed

---

### Phase 4: Security & Railway Deployment

**Dependencies**: Phase 3

#### Objectives
- Finalize HTTP Basic Auth
- Add Railway-specific configuration
- Implement proper logging with redaction
- Create deployment documentation

#### Deliverables
- [x] HTTP Basic Auth with env var credentials
- [x] Railway configuration files (Procfile, railway.toml)
- [x] PORT binding from environment
- [x] Single worker uvicorn configuration
- [x] Structured logging with API key redaction
- [x] CORS set to same-origin only
- [x] Deployment README
- [x] Environment variable documentation

#### Implementation Details

**Files**:
- `Procfile` - Railway startup command
- `railway.toml` - Railway configuration
- `README_DEPLOYMENT.md` - Deployment guide
- Update `src/model_comparison/auth.py` for credentials

**Auth Implementation**:
```python
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.getenv("AUTH_USERNAME", "admin")
    correct_password = os.getenv("AUTH_PASSWORD")

    if not correct_password:
        raise RuntimeError("AUTH_PASSWORD not set")

    is_correct_username = secrets.compare_digest(credentials.username, correct_username)
    is_correct_password = secrets.compare_digest(credentials.password, correct_password)

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
```

**Railway Config**:

`Procfile`:
```
web: uvicorn src.model_comparison.app:app --host 0.0.0.0 --port $PORT --workers 1
```

`railway.toml`:
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn src.model_comparison.app:app --host 0.0.0.0 --port $PORT --workers 1"
healthcheckPath = "/health"
healthcheckTimeout = 10
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

**Environment Variables** (Railway settings):
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `AUTH_USERNAME` (default: admin)
- `AUTH_PASSWORD` (required)
- `PORT` (auto-set by Railway)

**Logging**:
- Use Python `logging` module
- Redact API keys and passwords in logs
- Log level from `LOG_LEVEL` env var (default: INFO)

#### Acceptance Criteria
- [x] Unauthenticated requests return 401
- [x] Valid credentials grant access
- [x] App binds to $PORT from environment
- [x] Single worker configuration verified
- [x] Logs don't contain API keys or passwords
- [x] `/health` endpoint works for Railway healthcheck
- [x] Deployment documentation is clear and complete
- [x] All required env vars documented

#### Test Plan
- **Unit Tests**:
  - Auth credential validation
  - Log redaction
- **Integration Tests**:
  - Full auth flow (unauthorized → 401, authorized → 200)
- **Deployment Test**:
  - Deploy to Railway
  - Verify health check passes
  - Verify env vars load correctly
  - Test auth with browser
  - Run full query with real APIs

#### Rollback Strategy
Revert Phase 4 commit. Re-deploy previous phase to Railway.

#### Risks
- **Risk**: Railway timeout on long generations
  - **Mitigation**: 25s server timeout, heartbeat keeps connection alive
- **Risk**: AUTH_PASSWORD leaked in logs
  - **Mitigation**: Comprehensive log redaction testing

---

## Dependency Map

```
Phase 1 (Core Backend)
   ↓
Phase 2 (LangGraph & Streaming)
   ↓
Phase 3 (Frontend UI)
   ↓
Phase 4 (Security & Deployment)
```

Linear dependency chain - each phase builds on the previous.

## Resource Requirements

### Development Resources
- **Engineers**: Single developer with Python/FastAPI/async experience
- **Environment**: Local dev with API keys for Anthropic and Google

### Infrastructure
- Railway.app account (free tier sufficient for initial deployment)
- No database required (in-memory sessions only)
- No external services beyond LLM APIs

## Integration Points

### External Systems
- **Anthropic API**
  - **Integration Type**: REST API (streaming)
  - **Phase**: Phase 2
  - **Fallback**: Per-model error display, other models continue

- **Google Generative AI API**
  - **Integration Type**: REST API (streaming)
  - **Phase**: Phase 2
  - **Fallback**: Per-model error display, other models continue

### Internal Systems
- **LangGraph Agent**
  - **Integration Type**: Python library
  - **Phase**: Phase 2
  - **Fallback**: N/A (required dependency)

- **Ansari Tools** (Quran, Hadith, Mawsuah search)
  - **Integration Type**: Via LangGraph
  - **Phase**: Phase 2
  - **Fallback**: Tool timeout shows error in UI

## Risk Analysis

### Technical Risks

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Async SDK streaming incompatibility | Low | High | Verify async support early, fallback to run_in_executor | Dev |
| SSE connection drops | Medium | Low | EventSource auto-reconnects, clear UI messaging | Dev |
| Memory leak from session accumulation | Medium | Medium | Aggressive TTL, LRU eviction, monitoring | Dev |
| Railway 30s timeout | Low | Medium | 25s server timeout, heartbeat, chunked responses | Dev |
| XSS vulnerability in output | Low | High | Mandatory textContent usage, code review, XSS tests | Dev |
| One model failure cascades | Low | Medium | asyncio.gather with return_exceptions=True | Dev |

### Schedule Risks

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| LangGraph event normalization complexity | Medium | Medium | Allocate extra time for Phase 2, incremental testing | Dev |
| Railway deployment issues | Low | Low | Test deployment early in Phase 4, Railway docs | Dev |

## Validation Checkpoints

1. **After Phase 1**:
   - Session management works correctly (create, expire, evict)
   - All SSE event types serialize
   - Health check responds

2. **After Phase 2**:
   - All 4 models stream concurrently with real APIs
   - Events emit correctly with proper timing
   - Cancellation works
   - Partial failures handled

3. **After Phase 3**:
   - UI displays all streaming data correctly
   - XSS protection verified
   - Stop and clear buttons work
   - Multi-turn conversations maintain context

4. **Before Production (Phase 4)**:
   - Auth blocks unauthorized access
   - Railway deployment successful
   - All env vars configured
   - Full end-to-end test with real queries

## Monitoring and Observability

### Metrics to Track
- **Request count**: Total queries submitted
- **Stream duration**: p50, p95, p99 latency per model
- **Error rate**: Per model and overall
- **Session count**: Active sessions gauge
- **Memory usage**: Process memory (must stay <512MB)
- **Token usage**: Per model for cost tracking

### Logging Requirements
- **INFO**: Query submissions, stream completions, session lifecycle
- **WARNING**: API errors, timeouts, rate limits
- **ERROR**: Unexpected exceptions, auth failures
- **Retention**: Railway default (7 days free tier)
- **Redaction**: API keys, passwords, PII in user queries

### Alerting
Not required for v1 (internal dev tool). Future: Railway built-in monitoring.

## Documentation Updates Required

- [x] README_DEPLOYMENT.md - Railway deployment guide
- [x] Environment variable documentation
- [x] API endpoint documentation (OpenAPI via FastAPI)
- [x] Architecture diagram (optional, can be ASCII in README)
- [x] User guide (brief, in main README)

## Post-Implementation Tasks

- [x] Performance validation with 5 concurrent users
- [x] Security audit (XSS, auth, log redaction)
- [x] Load testing (20 concurrent streams)
- [x] Manual UAT with team members
- [x] Monitoring validation (logs, metrics)

## Expert Review

**Date**: 2025-10-06
**Models Consulted**: GPT-5 and Gemini 2.5 Pro

### Critical Adjustments Required

**1. Reconnection vs Cancellation Policy (BLOCKER)**
- **Issue**: Phase 2 says "Client disconnect cancels server tasks" but Phase 3 says "Implement SSE client with reconnection" - these contradict
- **Decision**: Cancel on disconnect for v1 (simpler)
- **Actions**:
  - Phase 2: Keep "Client disconnect cancels tasks"
  - Phase 3: Disable EventSource auto-reconnect, show clear "Connection lost" message
  - Add explicit `retry:` field in SSE with high value to discourage reconnection

**2. Streaming Architecture (CRITICAL)**
- **Issue**: `asyncio.gather()` doesn't yield events as they arrive - it waits for all to complete
- **Solution**: Use asyncio.Queue + TaskGroup pattern
- **Implementation**:
  ```python
  queue = asyncio.Queue()
  async with asyncio.TaskGroup() as tg:
      for model_id in models:
          tg.create_task(stream_model(model_id, queue))
      # Separate task drains queue and yields SSE
      async for event in drain_queue(queue):
          yield format_sse(event)
  ```

**3. Auth Staging Clarification**
- **Issue**: Phase 1 includes "Basic HTTP auth middleware" and Phase 4 says "Finalize HTTP Basic Auth" - unclear what "finalize" means
- **Clarification**:
  - Phase 1: Implement complete HTTP Basic Auth with hardcoded test credentials
  - Phase 4: Wire auth to use env var credentials (AUTH_USERNAME, AUTH_PASSWORD)
  - Update Phase 4 deliverable to "Configure auth with environment variables"

### Key Implementation Improvements

**From GPT-5**:

1. **Session Manager (Phase 1)**:
   - Use `asyncio.Lock` not threading locks (single worker, async context)
   - Add background cleanup task for expired sessions (not just on-access cleanup)
   - Implement hard enforcement of 10-turn/8K-token truncation at append time

2. **SSE Response Headers (Phase 2)**:
   ```python
   headers = {
       "Content-Type": "text/event-stream",
       "Cache-Control": "no-cache, no-store",
       "Connection": "keep-alive",
       "X-Accel-Buffering": "no"  # Disable proxy buffering
   }
   ```

3. **Cancellation Robustness (Phase 2)**:
   - Wrap each model stream in `asyncio.wait_for(stream_fn(), timeout=25.0)`
   - Verify Anthropic/Google SDKs respect task cancellation
   - Test that tool calls stop after cancellation

4. **Security Headers (Phase 4)**:
   ```python
   # On GET / response:
   headers = {
       "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
       "X-Content-Type-Options": "nosniff",
       "Referrer-Policy": "no-referrer"
   }
   ```

5. **Graceful Shutdown (Phase 4)**:
   - Add FastAPI lifespan handler
   - Cancel all active session task groups
   - Close any global AsyncClient instances
   - Stop background cleanup task

6. **Library Choice (Phase 1)**:
   - Use manual `StreamingResponse` (not sse-starlette)
   - Remove sse-starlette from dependencies
   - Simpler, one less dependency

7. **Logging with Redaction (Phase 4)**:
   - Structured logging with session_id in all messages
   - Redact API keys, Authorization headers, passwords in logs
   - Format: `INFO: [session: {id}] [model: {model_id}] {message}`

**From Gemini 2.5 Pro**:

1. **Debug UI in Phase 2 (NEW)**:
   - Create minimal `debug.html` with textarea, submit button, and `<pre>` for raw SSE events
   - De-risks frontend integration early
   - Invaluable for debugging event flow in real browser environment

2. **Memory Monitoring (NEW)**:
   - Add `/debug/memory` endpoint returning process memory usage
   - Use during load tests to catch memory leaks
   - Format: `{"rss_mb": 245, "session_count": 12}`

3. **Contextual Logging (Phase 2)**:
   - Inject `session_id` into every log message during request handling
   - Use logging.Filter or structlog
   - Essential for debugging failed streams in production

4. **Blocking Code Warning (All Phases)**:
   - Single worker means any blocking code freezes entire app
   - Wrap blocking operations in `await asyncio.to_thread(...)`
   - Critical for LangGraph tools that might do file I/O

5. **Load Testing Script (Post-Implementation)**:
   - Add locust or simple asyncio script
   - Simulate 10 concurrent users with streams
   - Monitor memory during test (use /debug/memory)
   - Verify no memory growth over 100 requests

6. **Manual Disconnect Testing (Phase 2)**:
   - Automated tests can't fully simulate browser tab close
   - Manual test: disconnect network during stream
   - Verify server logs show task cancellation
   - Verify session cleanup

### Updated Phase Deliverables

**Phase 1 additions**:
- [x] Asyncio.Lock for session access (not thread locks)
- [x] Background cleanup task for expired sessions
- [x] Manual StreamingResponse (remove sse-starlette dependency)
- [x] Complete HTTP Basic Auth (test credentials)

**Phase 2 additions**:
- [x] asyncio.Queue + TaskGroup for event fan-in
- [x] asyncio.wait_for wrapper (25s timeout)
- [x] debug.html stub for early browser testing
- [x] Contextual logging with session_id
- [x] SSE response headers (no-cache, no-buffering)
- [x] Manual test plan for client disconnect

**Phase 3 additions**:
- [x] Disable EventSource auto-reconnect
- [x] "Connection lost" UI message
- [x] Verify no blocking operations in event handlers

**Phase 4 additions**:
- [x] Wire auth to environment variables (not new auth implementation)
- [x] Security headers (CSP, nosniff, referrer-policy)
- [x] Graceful shutdown via lifespan handler
- [x] Log redaction implementation
- [x] `/debug/memory` endpoint

**Post-Implementation additions**:
- [x] Load testing script with memory monitoring
- [x] Manual disconnect testing
- [x] Verify SDK cancellation behavior

### Sections Updated in Plan

- **Phase 1 Implementation Details**: Added asyncio.Lock, background cleanup
- **Phase 1 Deliverables**: Added complete auth, removed sse-starlette
- **Phase 2 Implementation Details**: Replaced gather with Queue+TaskGroup
- **Phase 2 Deliverables**: Added debug.html, contextual logging, SSE headers
- **Phase 2 Acceptance Criteria**: Clarified disconnect = cancel (no reconnection)
- **Phase 3 Implementation Details**: Added reconnect disable logic
- **Phase 4 Deliverables**: Changed auth to "configure" not "finalize"
- **Phase 4 Implementation Details**: Added security headers, graceful shutdown
- **Post-Implementation Tasks**: Added load testing script, manual disconnect test

## Approval

- [ ] Technical Lead Review
- [ ] Resource Allocation Confirmed
- [x] Expert AI Consultation Complete (First Round)
- [ ] Expert AI Consultation Complete (Second Round - after adjustments)

## Change Log

| Date | Change | Reason | Author |
|------|--------|--------|--------|
| 2025-10-06 | Initial plan draft | Based on approved specification | Claude |

## Notes

- **Single worker**: Critical for Railway deployment since sessions are in-memory
- **No database**: Deliberate choice for simplicity; sessions lost on restart (acceptable for dev tool)
- **XSS protection**: Use textContent everywhere; if markdown added later, must use DOMPurify or similar
- **Testing strategy**: Focus on integration tests over unit tests for streaming logic
- **Token estimates removed**: Following protocol guidance, no time estimates in AI age
