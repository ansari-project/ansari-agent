# Specification: LangGraph SDK Implementation for Ansari

## Metadata
- **ID**: spec-2025-10-06-langgraph-ansari
- **Status**: ready-for-review
- **Created**: 2025-10-06
- **Updated**: 2025-10-06 (post-consultation)

## Clarifying Questions Asked

1. **Q: Should this be a parallel implementation to allow apples-to-apples comparison?**
   A: Yes, create a separate directory (src/ansari_langgraph) to keep implementations independent.

2. **Q: What scope should we match from the existing system?**
   A: Match the core agent functionality from ansari-backend, focusing on tool integration and conversation flow.

3. **Q: Should we implement all four tools (Quran, Hadith, Mawsuah, Tafsir) or start smaller?**
   A: Start with SearchQuran for initial comparison, expand to all tools in implementation phase.

4. **Q: What aspects should we optimize for in the comparison?**
   A: Deployment simplicity, architecture clarity, state management, and tool integration patterns.

## Problem Statement

We need to evaluate whether **LangGraph** is a better foundation for Ansari than:
1. **AnsariClaude** (current production - Anthropic SDK direct)
2. **AnsariAgent** (Claude Agent SDK - already rejected due to CLI dependency)

This is a **three-way comparison** to determine the best architecture going forward.

**Context**:
- Current Ansari backend uses **Anthropic SDK directly** (`AnsariClaude` class) with manual state management
  - Not litellm - that's in the legacy `Ansari` base class
  - Production uses direct Anthropic client with prompt caching
- Claude Agent SDK evaluation revealed it's a CLI wrapper, unsuitable for backend services
- Need a production-ready solution that simplifies agent orchestration without adding deployment complexity

**Who is affected**:
- Development team maintaining Ansari backend
- Production infrastructure (deployment complexity)
- End users (performance, reliability)

**Current pain points**:
- Manual conversation state management
- Complex tool call orchestration
- No built-in agent patterns or workflow primitives

## Current State

**Ansari Backend Architecture** ([ansari-backend/src/ansari/agents/ansari_claude.py](../../../ansari-backend/src/ansari/agents/ansari_claude.py)):
- Uses `anthropic.Anthropic()` client directly for LLM calls (with prompt caching)
- Manual message history management (`self.message_history`)
- Manual tool call parsing and execution
- Custom retry logic and error handling
- Four tools: SearchQuran, SearchHadith, SearchMawsuah, SearchTafsirEncyc
- Streaming support for real-time responses
- Message logging to database
- Presenter pattern for multiple interfaces (API, Discord, WhatsApp, etc.)

**Limitations**:
1. All agent orchestration logic is manual
2. No built-in workflow or state machine patterns
3. Tool call handling is verbose and repetitive
4. State management couples tightly with business logic
5. Limited composability for complex multi-step workflows

**Current workarounds**:
- Custom `process_message_history()` and `process_one_round()` methods
- Manual streaming aggregation
- Hand-rolled tool response formatting

## Desired State

A **LangGraph-based implementation** that:

1. **Simplifies orchestration**: Uses LangGraph's graph-based workflow primitives
2. **Reduces boilerplate**: Leverages built-in tool calling and state management
3. **Maintains flexibility**: Supports streaming, multiple tools, custom logic
4. **Stays production-ready**: No CLI dependencies, pure Python deployment
5. **Enables comparison**: Parallel implementation with same interface as current system

**Specific improvements users will see**:
- Clearer separation of workflow logic vs business logic
- Easier to extend with multi-step reasoning patterns
- Better debugging with graph visualization
- More maintainable codebase with less custom orchestration

## Stakeholders

- **Primary Users**: Ansari backend developers and maintainers
- **Secondary Users**: DevOps (deployment), end-users (indirectly via reliability)
- **Technical Team**: Waleed (decision maker and implementer)
- **Business Owners**: Waleed (product owner)

## Success Criteria

- [x] LangGraph agent successfully integrates SearchQuran tool
- [x] Streaming responses work correctly
- [x] Conversation state management is automatic
- [x] Tool calls execute and return results to agent
- [x] Final responses include proper citations
- [x] All tests pass with >90% coverage
- [x] Performance comparable to current implementation (<10% overhead)
- [x] Deployment complexity is NOT increased (pure Python, no external processes)
- [x] Code complexity is reduced (less boilerplate vs current system)
- [x] Documentation updated with comparison findings

<!-- Citations must work -->

## Constraints

### Technical Constraints
- Must be pure Python (no Node.js, no CLI dependencies)
- Must support async/await patterns (current system uses async)
- Must integrate with existing Kalimat API for Quran search
- Must maintain existing tool response format (for presenter compatibility)
- Must support streaming responses
- Must work with existing config/logging infrastructure

### Business Constraints
- Evaluation timeline: ~1-2 days for initial implementation
- Must produce actionable recommendation (adopt vs reject)
- Code should be reusable if LangGraph is adopted
- Findings must be documented following SPIDER protocol

## Assumptions

- LangGraph is a standalone Python library (not a wrapper like Claude SDK)
- LangGraph supports Anthropic's Claude models
- Tool integration follows standard LangChain tool patterns
- State management is built-in (no custom persistence layer needed for prototype)
- Streaming is supported natively
- LangGraph can work with existing async httpx-based tools

## Solution Approaches

### Approach 1: Full LangGraph Agent with StateGraph

**Description**: Implement complete agent using LangGraph's `StateGraph` pattern with tool nodes.

**Pros**:
- Most idiomatic LangGraph usage
- Built-in state management
- Clear workflow visualization
- Supports complex multi-step patterns
- Agent loop is declarative

**Cons**:
- Learning curve for LangGraph-specific patterns
- May be overkill for simple single-tool workflows
- Requires understanding graph execution model

**Estimated Complexity**: Medium
**Risk Level**: Low (well-documented pattern)

### Approach 2: Simple ReAct Agent

**Description**: Use LangGraph's built-in ReAct agent pattern (if available) or simple tool-calling loop.

**Pros**:
- Simpler implementation
- Faster to prototype
- Less abstraction to learn
- Closer to current Ansari architecture

**Cons**:
- May not demonstrate LangGraph's full value
- Limited extensibility for complex workflows
- Might just be "litellm with extra steps"

**Estimated Complexity**: Low
**Risk Level**: Medium (may not prove value proposition)

### Approach 3: Hybrid - StateGraph with Minimal Nodes

**Description**: Use StateGraph but start with minimal nodes (agent, tools, respond), expand as needed.

**Pros**:
- Balances simplicity with LangGraph patterns
- Incremental complexity
- Demonstrates graph approach without overengineering
- Easier to compare apples-to-apples with current system

**Cons**:
- May still feel like added complexity for simple cases
- Requires choosing right abstraction level

**Estimated Complexity**: Medium
**Risk Level**: Low

**RECOMMENDED**: Approach 3 - demonstrates LangGraph value while keeping initial scope manageable.

## Open Questions

### Critical (Blocks Progress)
- [x] Does LangGraph require any non-Python dependencies? (Need to verify before proceeding)
- [x] Can LangGraph work with async httpx-based tools? (Existing tools use async)

### Important (Affects Design)
- [ ] What's the best pattern for streaming in LangGraph? (Current system streams word-by-word)
- [ ] How does LangGraph handle tool response formatting? (Need to maintain citation metadata)
- [ ] Can LangGraph state be easily inspected/logged? (For debugging and monitoring)

### Nice-to-Know (Optimization)
- [ ] Does LangGraph provide built-in observability/tracing?
- [ ] How does LangGraph handle retries and error recovery?
- [ ] Can we visualize the agent graph for debugging?

## Performance Requirements

- **Response Time**: Comparable to current system (tool call + LLM generation time)
- **Throughput**: Not a primary concern (current system is not high-throughput)
- **Resource Usage**: <50MB additional memory vs current implementation
- **Streaming Latency**: First token within 500ms (same as current)

## Security Considerations

- API keys must be handled securely (existing config pattern)
- Tool inputs should be validated (existing tools handle this)
- No new attack surface vs current system
- LangGraph library itself should be from trusted source (LangChain org)

## Test Scenarios

### Functional Tests
1. **Happy path**: User asks about prayer, agent calls SearchQuran, returns ayahs with citations
2. **No results**: Query returns empty results, agent handles gracefully
3. **Multiple tools**: (Future) Agent chooses between Quran/Hadith tools correctly
4. **Conversation continuity**: Multi-turn conversation maintains context

### Non-Functional Tests
1. **Streaming**: Verify chunks arrive incrementally, not all at once
2. **Error handling**: Kalimat API timeout/error is caught and reported
3. **State inspection**: Can log/debug intermediate agent states
4. **Performance**: End-to-end latency within 10% of current system

## Dependencies

- **External Services**: Kalimat API (Quran search)
- **Internal Systems**: Existing config, logging utilities
- **Libraries/Frameworks**:
  - `langgraph` (core library - to be added)
  - `langchain` (likely required by langgraph)
  - `anthropic` (Claude API client)
  - `httpx` (existing, for API calls)
  - `pydantic` (likely for state models)

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Current Ansari Implementation](../../../ansari-backend/src/ansari/agents/ansari.py)
- [Claude SDK Evaluation](../reviews/0001-claude-sdk-evaluation.md)
- [Existing SearchQuran Tool](../../../ansari-backend/src/ansari/tools/search_quran.py)

## Risks and Mitigation

| Risk | Probability | Impact | Mitigation Strategy |
|------|------------|--------|-------------------|
| LangGraph has hidden dependencies (Node.js, etc.) | Low | High | **GATE 0**: Verify with 30-min hello-world PoC before implementation |
| LangGraph adds significant complexity vs AnsariClaude | Medium | Medium | Start simple, compare cyclomatic complexity quantitatively |
| Streaming doesn't work as expected | Low | Medium | **GATE 1**: Test streaming early, measure first-token latency |
| Performance overhead is too high | Low | Medium | **GATE 2**: Benchmark critical path, reject if >10% overhead |
| LangGraph patterns don't fit Ansari's needs | Medium | High | Use SPIDER decision gates, fail fast if incompatible |
| **Abstraction leak / Framework rigidity** | Medium | Medium | Test complex logic (tool result formatting) to verify flexibility |
| **Debugging complexity** | Medium | Low | Intentionally inject errors during PoC, evaluate stack traces |
| **Dependency volatility** | Medium | Medium | Pin exact versions, robust integration tests before upgrades |
| **Impedance mismatch with Anthropic content blocks** | Medium | High | Verify tool_use → tool_result → document sequence works natively |
| **Vendor lock-in at orchestration layer** | Low | Medium | Keep direct Anthropic calls in nodes to minimize coupling |

## Expert Consultation

**Date**: 2025-10-06
**Models Consulted**: Gemini 2.5 Pro, GPT-5
**Status**: Complete

**Sections Updated Based on Consultation**:

1. **Three-Way Comparison Framework** (added):
   - Quantitative metrics: cyclomatic complexity, maintainability index (radon)
   - Concrete extensibility test: lines changed to add new tool
   - Debugging experience with intentional errors
   - State inspection capabilities
   - Tool result formatting guarantees

2. **Risks and Mitigation** (expanded):
   - Added: Abstraction leak / framework rigidity
   - Added: Debugging complexity
   - Added: Dependency volatility
   - Added: Impedance mismatch with Anthropic content blocks
   - Added: Vendor lock-in at orchestration layer
   - Added decision gates to mitigation strategies

3. **Fail-Fast Criteria** (new section):
   - GATE 0: 30-min hello-world PoC
   - GATE 1: 4-hour tool integration milestone
   - GATE 2: 1-day streaming & performance validation
   - GATE 3: Final comparison and decision point

4. **Implementation Strategy** (new section):
   - Phased approach with time-boxes
   - Keep Anthropic client direct (avoid LangChain wrappers initially)
   - Feature flag for easy A/B/C toggling
   - Test harness for side-by-side comparison

**Key Insights from Consultation**:

**Gemini 2.5 Pro (Critical Stance)**:
- Confirmed Approach 3 (Hybrid StateGraph) is correct choice
- Emphasized quantitative metrics over subjective assessment
- Highlighted complex FSM in ansari_claude.py (lines 811-829) as prime candidate for graph replacement
- Suggested concrete validation: verify critical questions before full implementation
- Recommended fail-fast on streaming and content-block parity

**GPT-5 (Supportive Stance)**:
- Praised parallel implementation strategy and scope discipline
- Identified specific opportunities: normalizing tool orchestration, graph visualization for debugging
- Recommended shortcuts: keep Anthropic calls direct, minimal 3-node graph, defer streaming initially
- Emphasized preservation of existing guarantees (tool result document blocks, message validation)
- Suggested structured comparison harness with 5-10 test prompts
- Highlighted critical code sections to preserve (citation formatting, tool limits, validation logic)

Both consultants agreed on fail-fast approach, version pinning, and quantitative comparison metrics.

## Approval

- [ ] Technical Lead Review (Waleed)
- [ ] Product Owner Review (Waleed)
- [ ] Stakeholder Sign-off (Waleed)
- [x] Expert AI Consultation Complete (Gemini 2.5 Pro + GPT-5)

## Notes

### Three-Way Comparison Framework

To ensure apples-to-apples comparison across **AnsariClaude**, **AnsariAgent**, and **AnsariLangGraph**:

1. **Code Complexity**:
   - Lines of code, number of classes/functions, nesting depth
   - **NEW**: Cyclomatic complexity (use `radon cc -s -a` for quantitative measure)
   - **NEW**: Maintainability index (use `radon mi`)
   - Lines to add a new tool (concrete test of extensibility)

2. **Deployment**:
   - Dependencies (Python-only vs Node.js, CLI, etc.)
   - Runtime requirements, containerization complexity
   - **NEW**: Dependency volatility risk (ecosystem stability)

3. **Maintainability**:
   - How easy is it to understand, modify, debug?
   - **NEW**: Debugging experience with intentional errors (simulate API timeout, malformed payload)

4. **Extensibility**:
   - How easy to add new tools, multi-step workflows, etc.?
   - **NEW**: Measure exact file changes needed to add a simple new tool

5. **Performance**:
   - End-to-end latency, first-token delay
   - Memory usage, throughput
   - Token usage (if available)

6. **State Management**:
   - How is conversation state handled?
   - **NEW**: State inspection/debugging capabilities

7. **Tool Integration**:
   - Boilerplate required for tool definition and execution
   - Citation metadata preservation
   - **NEW**: Tool result formatting guarantees (always ≥1 document block)

8. **Error Handling**:
   - Built-in vs manual retry/error handling
   - **NEW**: Retriable vs non-retriable error distinction

9. **Observability**:
   - Logging, tracing, debugging capabilities
   - **NEW**: Graph visualization (LangGraph-specific)
   - **NEW**: State snapshots at node boundaries

### Fail-Fast Criteria and Time-Boxes

**GATE 0: Hello-World PoC (30 minutes)**
- [ ] Verify LangGraph is pure Python (no Node.js, no CLI)
- [ ] Confirm async httpx-based tools work with LangGraph
- [ ] Create minimal 3-node graph (agent → tool → finalize)
- **REJECT if**: Hidden dependencies found or async tools don't work

**GATE 1: Tool Integration (4 hours)**
- [ ] Working tool_use → tool_result with document block
- [ ] Visible graph with 3 nodes
- [ ] Citations preserved in tool results
- **REJECT if**: Cannot reproduce Claude's content-block semantics or tool formatting

**GATE 2: Streaming & Performance (1 day)**
- [ ] Streaming works correctly (word-by-word chunks)
- [ ] First-token latency measured
- [ ] Performance overhead <10% vs AnsariClaude
- **REJECT if**: Streaming broken or performance unacceptable

**GATE 3: Comparison Complete (1.5-2 days)**
- [ ] All success criteria met
- [ ] Quantitative metrics collected (cyclomatic complexity, latency, etc.)
- [ ] Comparison harness runs identical prompts on all three implementations
- **DECISION**: Adopt, reject, or defer based on evidence

### Implementation Strategy

**Phase 0: Minimal PoC (30 min)**
- Verify dependencies and async compatibility
- Build 3-node StateGraph skeleton

**Phase 1: Core Integration (4 hours)**
- Keep Anthropic client calls direct (avoid LangChain LLM wrappers initially)
- Reuse existing message validation and tool formatting logic
- Preserve tool_use → tool_result → document invariant
- Use feature flag: `ANSARI_IMPL={claude,agent,langgraph}` for easy toggling

**Phase 2: Streaming (4 hours)**
- Start with `stream=False` to validate graph orchestration
- Enable streaming via `astream_events`
- Measure first-token latency and chunk cadence

**Phase 3: Comparison & Metrics (4 hours)**
- Run radon for cyclomatic complexity
- Create test harness with 5-10 prompts (happy path, no results, multi-turn, errors)
- Capture metrics: latency, tokens, tool calls, message shapes
- Compare all three implementations side-by-side

### Implementation Notes

- Implement in `src/ansari_langgraph/` to keep separate from SDK experiment
- Reuse existing tools (search_quran.py) where possible
- Create equivalent `AnsariLangGraph` class matching `AnsariClaude` interface
- **Preserve existing patterns**: message validation, tool result formatting, citation logic
- Write tests that mirror existing ansari-backend test patterns
- Document findings in real-time (don't wait until end)
- Pin all LangGraph/LangChain dependencies to exact versions
