# Specification: Model Comparison Web UI

## Metadata
- **ID**: spec-2025-10-06-model-comparison-ui
- **Status**: draft
- **Created**: 2025-10-06

## Clarifying Questions Asked

**Q1: What models should be compared?**
A: Gemini 2.5 Pro, Gemini 2.5 Flash, Claude Opus 4.1, and Claude Sonnet 4.5

**Q2: What latency metrics should be displayed?**
A: Time to first token (TTFT) and total response latency per interaction

**Q3: Should conversations be persisted?**
A: No, multi-turn conversations supported in memory only (session-based)

**Q4: What tool usage information should be shown?**
A: Real-time display of which tool the model is currently using

**Q5: What deployment target?**
A: Railway.app for easy deployment and hosting

**Q6: Should the UI support streaming responses?**
A: Yes, real-time streaming for all 4 models simultaneously

**Q7: What about conversation history management?**
A: No need to save/export conversations, just maintain context during active session

**Q8: Should there be any model configuration options?**
A: No, use default configurations for fair comparison

## Problem Statement

Developers and users need a practical way to compare the performance, capabilities, and behavior of different LLM backends (Gemini and Claude models) side-by-side in real-world conversational scenarios. Currently, testing requires running separate queries against each model individually, making it difficult to assess differences in latency, tool usage patterns, and response quality.

This comparison tool is critical for:
- **Backend selection decisions**: Choosing the right model for Ansari
- **Performance benchmarking**: Understanding real-world latency differences
- **Tool usage analysis**: Observing which models use tools more effectively
- **Quality assessment**: Comparing response quality across models

## Current State

Currently, to compare models we must:
1. Run separate CLI commands for each model
2. Manually track timing with external tools
3. Review logs to understand tool usage
4. Switch between different terminal windows
5. Lose context when switching between models

**Limitations**:
- No visual side-by-side comparison
- Manual timing is error-prone
- Tool usage visibility is poor
- Cannot easily test multi-turn behavior across models
- Difficult to share comparisons with team members

## Desired State

A simple, deployable web interface that:
1. Accepts a single user input
2. Streams responses from all 4 models simultaneously
3. Shows real-time latency metrics (TTFT and total)
4. Displays current tool usage for each model
5. Maintains conversation context for multi-turn interactions
6. Provides clear visual separation between models
7. Works on Railway with minimal configuration

**User Experience**:
- User types one question
- All 4 models respond in parallel in separate output boxes
- Latency appears as responses stream
- Tool usage updates in real-time
- User can continue conversation with all models maintaining context

## Stakeholders

- **Primary Users**: Development team evaluating model backends
- **Secondary Users**: Product stakeholders reviewing model capabilities
- **Technical Team**: DevOps for Railway deployment, developers for maintenance
- **Business Owners**: Project lead making technology decisions

## Success Criteria

- [x] Single input box sends to all 4 models simultaneously
- [x] 4 separate output boxes, one per model
- [x] Real-time streaming of responses with XSS protection
- [x] TTFT and total latency displayed per interaction
- [x] Tool usage timeline shown per model (not just current tool)
- [x] Token counts displayed per model (prompt + completion)
- [x] Stop generation button to cancel in-flight requests
- [x] Multi-turn conversation support with maintained context
- [x] Clear conversation button to reset session
- [x] Basic authentication (HTTP Basic Auth minimum)
- [x] Deployable to Railway with simple configuration
- [x] Responsive UI that works on desktop browsers
- [x] All tests pass with >85% coverage
- [x] Performance: Handle concurrent streaming from 4 models
- [x] Documentation includes Railway deployment instructions

## Constraints

### Technical Constraints
- Must use existing LangGraph agent implementation
- Must support streaming from Gemini and Claude models
- Must work with Railway's Python runtime
- Limited to web technologies (no desktop app)
- Must handle API rate limits gracefully

### Business Constraints
- Timeline: Should be functional for immediate model evaluation
- Budget: Use free/low-cost hosting on Railway
- Simplicity: No complex authentication or user management needed

## Assumptions

- API keys for Anthropic and Google are configured via environment variables
- LangGraph agent implementation supports streaming
- Railway supports Python web applications with SSE (Server-Sent Events)
- Users have modern browsers with JavaScript enabled
- Network latency to AI providers is acceptable for comparison purposes

## Solution Approaches

### Approach 1: FastAPI + Vanilla HTML/JS (RECOMMENDED)

**Description**: FastAPI backend with Server-Sent Events (SSE) for streaming, simple HTML/JS frontend embedded in the app.

**Pros**:
- Lightweight and fast
- Native async support perfect for concurrent streaming
- SSE is simple and works well for one-way streaming
- No build step or complex frontend tooling
- Easy Railway deployment
- Single Python process

**Cons**:
- Less polished UI compared to React/Vue
- Manual DOM manipulation in JavaScript
- No component reusability

**Estimated Complexity**: Low
**Risk Level**: Low

### Approach 2: FastAPI + React Frontend

**Description**: FastAPI backend with separate React SPA frontend.

**Pros**:
- Modern, polished UI
- Component-based architecture
- Better state management
- Reusable for future features

**Cons**:
- Requires build step (npm/webpack)
- More complex deployment (serve static + API)
- Overkill for simple comparison UI
- Longer development time

**Estimated Complexity**: Medium
**Risk Level**: Low

### Approach 3: Gradio Interface

**Description**: Use Gradio for rapid UI prototyping.

**Pros**:
- Extremely fast to implement
- Built-in components
- Auto-generates UI from functions

**Cons**:
- Limited customization for latency/tool display
- Harder to show 4 concurrent streams
- Less control over layout
- Not designed for this specific use case

**Estimated Complexity**: Very Low
**Risk Level**: Medium (may not meet all requirements)

### Approach 4: Streamlit

**Description**: Use Streamlit for dashboard-style UI.

**Pros**:
- Fast prototyping
- Good for data display
- Built-in layouts

**Cons**:
- Streamlit's execution model not ideal for concurrent streaming
- Refresh/rerun behavior can be problematic
- Less control over real-time updates
- Overkill for simple input/output

**Estimated Complexity**: Low
**Risk Level**: Medium

## Recommended Approach

**Approach 1: FastAPI + Vanilla HTML/JS**

This approach best balances simplicity, performance, and meeting all requirements. FastAPI's async capabilities are perfect for concurrent model streaming, and SSE provides real-time updates without WebSocket complexity.

## Open Questions

### Critical (Blocks Progress)
- [x] Do we have access to all 4 models via LangGraph? (Answered: Yes, via existing implementation)
- [x] Can LangGraph agent stream responses? (Answered: Yes, via astream)
- [x] Should there be a "stop generation" button? (Answered: YES - REQUIRED for cost control and UX)

### Important (Affects Design)
- [x] Should we show token counts? (Answered: YES - critical for cost comparison)
- [ ] Should we add cost tracking per model? (Optional - can add later)
- [ ] Do we need request/response logging? (Optional for v1)

### Nice-to-Know (Optimization)
- [ ] Should we add export/share functionality later?
- [ ] Would it be useful to show response diffs?
- [ ] Should we add visualization for tool call graphs?

## Performance Requirements

- **Response Time**:
  - UI should be responsive (<100ms for user interactions)
  - Streaming should start within 2s of API response
- **Throughput**: Support 4 concurrent model streams
- **Resource Usage**:
  - <512MB memory (Railway free tier compatible)
  - Minimal CPU when idle
- **Availability**: Best effort (development tool, not production service)

## Security Considerations

- **API keys**: Stored as environment variables (ANTHROPIC_API_KEY, GOOGLE_API_KEY)
- **Authentication**: HTTP Basic Auth required (minimal barrier against URL leaks)
- **XSS Protection**: All model outputs rendered as text, not HTML (use textContent, not innerHTML)
- **Output Sanitization**: If markdown rendering added, must use sanitized library
- **No user data persistence**: Session data cleared on disconnect
- **No sensitive information in logs**: Redact API keys and user queries from logs
- **Railway environment variable management**: For secrets
- **CORS**: Same-origin only (no cross-origin access needed)

## Test Scenarios

### Functional Tests
1. **Single turn interaction**
   - User submits question
   - All 4 models respond
   - Latency metrics appear
   - Tool usage displays correctly

2. **Multi-turn conversation**
   - User asks follow-up question
   - Models maintain context
   - Conversation history persists in session
   - Responses build on previous context

3. **Concurrent streaming**
   - All 4 models stream simultaneously
   - No blocking between models
   - UI updates smoothly
   - Tool usage changes reflect in real-time

4. **Error handling**
   - API timeout → graceful error message
   - Rate limit → clear error display
   - Invalid input → helpful feedback
   - Network error → retry suggestion

4. **Cancellation**
   - User clicks stop button → streams cancel
   - Partial responses remain visible
   - No residual tool calls after cancellation

5. **XSS Protection**
   - Model output containing `<script>` tags renders as text
   - No JavaScript execution from model responses

6. **Partial failure**
   - One model API fails → other 3 continue streaming
   - Failed model shows clear error message
   - No impact on working models

7. **Authentication**
   - Unauthenticated access → 401 response
   - Valid credentials → access granted

### Non-Functional Tests
1. **Performance test**
   - 4 concurrent streams complete successfully
   - Memory usage stays under 512MB
   - No memory leaks over 100 interactions (extended from 10)

2. **Load test**
   - Handle 5 concurrent users (20 streams total)
   - Responses remain responsive
   - No connection pool exhaustion

3. **Event schema tests**
   - All event types emit correct structure
   - Events correctly tagged with model_id
   - TTFT measured consistently across models
   - Token counts accurate

4. **Session lifecycle tests**
   - Session expires after 15 min idle
   - History truncates at 10 turns or 8K tokens
   - LRU eviction works when 50 session limit reached

5. **Railway deployment test**
   - App deploys successfully
   - Environment variables load correctly
   - Port binding works ($PORT)
   - Health check passes
   - Single worker configuration
   - SSE keepalive prevents timeouts

## Dependencies

### External Services
- Anthropic API (Claude models)
- Google Generative AI API (Gemini models)

### Internal Systems
- LangGraph agent implementation
- Ansari tool integrations (Quran, Hadith, Mawsuah search)

### Libraries/Frameworks
- FastAPI (web framework)
- uvicorn (ASGI server)
- sse-starlette (Server-Sent Events)
- LangGraph (agent framework)
- pydantic (data validation)

## References

- [LangGraph Streaming Documentation](https://langchain-ai.github.io/langgraph/how-tos/streaming/)
- [FastAPI SSE](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [Railway Python Deployment](https://docs.railway.app/guides/python)
- [codev/reviews/0002-langgraph-implementation.md](../reviews/0002-langgraph-implementation.md) - LangGraph evaluation

## Risks and Mitigation

| Risk | Probability | Impact | Mitigation Strategy |
|------|------------|--------|-------------------|
| API rate limits | Medium | Medium | Implement exponential backoff, show clear error messages |
| Railway timeout (30s) | Low | Medium | Ensure responses complete within 25s, add timeout handling |
| Concurrent stream complexity | Low | High | Use FastAPI's native async, test thoroughly |
| Memory usage on Railway | Low | Medium | Monitor memory, use streaming to minimize buffering |
| Model API changes | Low | High | Pin API versions, add version checks |

## API & Event Contract

### SSE Event Schema

All events follow this structure with `model_id` identifying the source:
- `gemini-2.5-pro`, `gemini-2.5-flash`, `claude-opus-4-20250514`, `claude-sonnet-4-5-20250929`

**Event Types**:

```typescript
// Stream initialization
{type: 'start', model_id: string, timestamp: number}

// Time to first token
{type: 'ttft', model_id: string, ttft_ms: number}

// Content streaming
{type: 'token', model_id: string, content: string}

// Tool usage
{type: 'tool_start', model_id: string, tool_name: string, timestamp: number}
{type: 'tool_end', model_id: string, tool_name: string, duration_ms: number}

// Completion
{type: 'done', model_id: string, total_ms: number, tokens_in: number, tokens_out: number}

// Errors
{type: 'error', model_id: string, error: string, retry_after_ms?: number}

// Keepalive (every 10s)
{type: 'heartbeat', timestamp: number}
```

### API Endpoints

- `POST /api/query` - Submit new query, returns session_id
- `GET /api/stream/{session_id}` - SSE stream for all 4 models
- `POST /api/cancel/{session_id}` - Cancel in-flight generation
- `GET /health` - Health check endpoint

### Fairness Configuration

To ensure fair comparison, all models use identical settings:
- **Temperature**: 0.0 (deterministic where possible)
- **Max tokens**: 4096
- **System prompt**: None (or identical minimal prompt)
- **Tools**: Identical tool registry (Quran, Hadith, Mawsuah search)
- **Stop sequences**: None

### Session Management

- **Session TTL**: 15 minutes idle timeout
- **Max sessions**: 50 concurrent sessions (LRU eviction)
- **History truncation**: Last 10 turns per model OR last 8K tokens
- **Memory limit**: 512MB total (Railway constraint)

## Expert Consultation

**Date**: 2025-10-06
**Models Consulted**: GPT-5 and Gemini 2.5 Pro

### Key Feedback Incorporated

**From GPT-5**:
1. **Event schema definition**: Added explicit SSE event contract (above)
2. **TTFT clarification**: Defined as time to first content token (not tool events)
3. **Fairness configuration**: Added explicit model configuration settings
4. **Session lifecycle**: Added TTL, max sessions, memory limits
5. **Cancellation mechanism**: Added `/cancel` endpoint requirement
6. **Testing expansion**: Enhanced test scenarios for event schema, cancellation, memory
7. **Railway deployment**: Single worker, PORT binding, keepalive requirements
8. **Async SDK confirmation**: Verified both Anthropic and Google SDKs support async streaming

**From Gemini 2.5 Pro**:
1. **Stop button priority**: Elevated from "nice-to-have" to core requirement
2. **Token counts**: Made required (critical for cost comparison)
3. **XSS protection**: Added textContent requirement, output sanitization
4. **Authentication**: Changed from "no auth" to HTTP Basic Auth minimum
5. **Tool timeline**: Changed from "current tool" to running tool log/timeline
6. **Partial failure handling**: Each model fails independently, others continue
7. **Clear conversation**: Added button to reset without page reload
8. **Connection interruption**: Graceful handling with clear user messaging
9. **Markdown rendering**: Noted as future enhancement with sanitization requirement

### Sections Updated

- **Success Criteria**: Added stop button, token counts, auth, XSS protection, clear button
- **Security Considerations**: Complete rewrite with XSS, auth, output sanitization
- **API & Event Contract**: New section with complete event schema
- **Session Management**: New section with limits and lifecycle
- **Fairness Configuration**: New section ensuring comparable results
- **Test Scenarios**: Expanded with event schema, cancellation, XSS, memory tests
- **Open Questions**: Resolved stop button and token count questions

## Approval

- [ ] Technical Lead Review
- [ ] Product Owner Review
- [ ] Stakeholder Sign-off
- [x] Expert AI Consultation Complete (First Round)
- [ ] Expert AI Consultation Complete (Second Round - after user feedback)

## Notes

This is a development tool to aid in backend selection for the Ansari project. It should prioritize functionality and ease of deployment over polish. The key value is enabling rapid, visual comparison of model behavior.

Future enhancements could include:
- Request/response logging
- Cost tracking
- Performance analytics dashboard
- Export/share functionality
- Additional models (GPT-4, etc.)
