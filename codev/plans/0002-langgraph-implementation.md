# Plan: LangGraph SDK Implementation for Ansari

## Metadata
- **ID**: plan-2025-10-06-langgraph-ansari
- **Status**: draft
- **Specification**: [codev/specs/0002-langgraph-implementation.md](../specs/0002-langgraph-implementation.md)
- **Created**: 2025-10-06

## Executive Summary

This plan implements a **gated, fail-fast evaluation** of LangGraph as a replacement for the current AnsariClaude implementation. We'll build a parallel implementation (`src/ansari_langgraph/`) using LangGraph's StateGraph pattern with minimal nodes, comparing it quantitatively against both AnsariClaude (production) and AnsariAgent (rejected SDK).

**Approach**: Hybrid StateGraph with minimal nodes (3-node architecture: agent → tool_executor → finalize) as recommended in the specification. This balances LangGraph's value demonstration with implementation simplicity.

**Decision Gates**: Four fail-fast gates with clear rejection criteria ensure we don't waste time on an incompatible solution.

## Success Metrics

From specification, plus implementation-specific additions:

- [x] **GATE 0 (30 min)**: LangGraph verified as pure Python, async tools work, 3-node graph created
- [x] **GATE 1 (4 hours)**: Tool integration working with citations preserved
- [x] **GATE 2 (1 day)**: Streaming functional, performance overhead <10%
- [x] **GATE 3 (2 days)**: All comparison metrics collected, decision made
- [x] Test coverage >90% (matching ansari-backend standards)
- [x] Quantitative metrics captured: cyclomatic complexity, latency, maintainability index
- [x] Comparison harness runs identical prompts across all three implementations
- [x] Documentation complete with recommendation

## Phase Breakdown

### GATE 0: Hello-World PoC (30 minutes)

**Dependencies**: None

#### Objectives
- **Document LangGraph dependencies** - what gets installed, any servers/services needed
- Confirm async httpx-based tools work with LangGraph
- Create minimal 3-node StateGraph skeleton
- **DECISION POINT**: Reject if requires server/service infrastructure or async incompatibility

#### Deliverables
- [ ] `pyproject.toml` updated with LangGraph dependencies (pinned versions)
- [ ] `src/ansari_langgraph/__init__.py` created
- [ ] `src/ansari_langgraph/poc.py` - minimal hello-world graph
- [ ] Verification script proving async httpx works in LangGraph node

#### Implementation Details

**Files to Create**:
```
src/ansari_langgraph/
├── __init__.py
├── poc.py          # Hello-world 3-node graph
├── state.py        # State model definition
└── langgraph.json  # LangGraph configuration (if required)
```

**Note**: Will verify if LangGraph requires specific file structure or configuration files.

**Minimal StateGraph Structure**:
```python
from langgraph.graph import StateGraph
from typing import TypedDict

class AgentState(TypedDict):
    messages: list[dict]
    tool_calls: list[dict] | None
    final_response: str | None

# Three nodes:
# 1. agent_node: calls LLM, detects tool_use
# 2. tool_node: executes tool (async httpx test)
# 3. finalize_node: formats final response

# Router: if tool_use -> tool_node, else -> finalize_node
```

**Dependencies to Add**:
```bash
uv add langgraph langchain-anthropic anthropic
uv add --dev radon  # for complexity metrics
```

#### Acceptance Criteria
- [ ] `uv sync` completes without requiring Node.js or external binaries
- [ ] Sample async httpx call executes successfully within a LangGraph node
- [ ] 3-node graph compiles and can be visualized
- [ ] No CLI subprocess spawning detected

#### Test Plan
- **Manual Verification**: Check `uv.lock` for suspicious dependencies
- **Integration Test**: Run hello-world graph end-to-end with async httpx call
- **Inspection**: Verify LangGraph execution doesn't spawn subprocesses

#### Rollback Strategy
If GATE 0 fails: Delete `src/ansari_langgraph/`, remove LangGraph from dependencies, update spec status to "rejected", proceed to review phase documenting blocker.

#### Risks
- **Risk**: LangGraph requires unexpected runtime dependencies
  - **Mitigation**: Check dependency tree immediately, test in clean environment
- **Risk**: Async httpx incompatibility with LangGraph
  - **Mitigation**: Test with simple httpx GET request first

---

### GATE 1: Tool Integration (4 hours)

**Dependencies**: GATE 0 passed

#### Objectives
- Integrate SearchQuran tool with full citation preservation
- Implement tool_use → tool_result → document block sequence (Anthropic's content-block semantics)
- Reuse existing ansari-backend tool formatting logic
- **DECISION POINT**: Reject if content-block semantics or citation formatting incompatible

#### Deliverables
- [ ] `src/ansari_langgraph/agent.py` - Main AnsariLangGraph class
- [ ] `src/ansari_langgraph/nodes.py` - Agent, tool, finalize node implementations
- [ ] `src/ansari_langgraph/tools.py` - Tool adapter for SearchQuran
- [ ] `tests/test_langgraph_tool_integration.py` - Tool call verification
- [ ] Working end-to-end query returning ayahs with citations

#### Implementation Details

**Files to Create/Modify**:
```
src/ansari_langgraph/
├── agent.py        # AnsariLangGraph class (matches AnsariClaude interface)
├── nodes.py        # Node functions: agent_step, tool_exec, finalize
├── tools.py        # Tool adapters
├── state.py        # Extended state model
└── graph.py        # StateGraph construction

tests/
└── test_langgraph_tool_integration.py
```

**Key Design Decisions**:

1. **Keep Anthropic Client Direct**:
   - Use `anthropic.Anthropic()` directly in agent_step node
   - Avoid LangChain LLM wrappers initially to isolate LangGraph value
   - Reuse ansari-backend's client initialization pattern

2. **Reuse Existing Validation**:
   - Import `_validate_message_history` from ansari_claude.py
   - Import `_fix_tool_use_result_relationship` logic
   - Preserve tool result formatting guarantees (≥1 document block)

3. **State Model**:
```python
class AnsariState(TypedDict):
    messages: list[dict]           # Anthropic message format
    tool_calls: list[dict] | None  # Pending tool calls
    tool_results: list[dict]       # Tool execution results
    citations: list[dict]          # Extracted citations
    final_response: str | None     # Final text response
    stop_reason: str | None        # Anthropic stop_reason
```

4. **Node Implementations**:
   - **agent_step**: Call Anthropic API, parse response, extract tool_calls
   - **tool_exec**: Execute SearchQuran, format tool_result + document blocks
   - **finalize**: Format final response with citations

5. **Router Logic**:
```python
def route_after_agent(state: AnsariState) -> str:
    if state["stop_reason"] == "tool_use":
        return "tool_exec"
    return "finalize"
```

#### Acceptance Criteria
- [ ] Query "Tell me about prayer in Islam" triggers SearchQuran
- [ ] Tool result includes ≥1 document block with citation metadata
- [ ] Citations appear in final response matching ansari-backend format
- [ ] Message history validates correctly (tool_use → tool_result relationship)
- [ ] No errors when running same query as ansari-backend test

#### Test Plan
- **Unit Tests**:
  - Node functions work independently
  - State transitions are correct
  - Tool adapter formats results correctly
- **Integration Tests**:
  - End-to-end query with tool call
  - Citation extraction and formatting
  - Message validation logic
- **Manual Testing**:
  - Compare output with ansari-backend for identical query
  - Inspect message_history structure

#### Rollback Strategy
If GATE 1 fails: Document exact impedance mismatch, preserve code for reference, update spec to "rejected", proceed to review phase.

#### Risks
- **Risk**: LangGraph fights Anthropic's content-block structure
  - **Mitigation**: Test exact tool_use → tool_result sequence early
- **Risk**: Citation metadata gets lost in state transitions
  - **Mitigation**: Add state logging at every node boundary
- **Risk**: Complex formatting logic doesn't fit into nodes cleanly
  - **Mitigation**: Allow nodes to call helper functions from ansari-backend

---

### GATE 2: Streaming & Performance (4 hours)

**Dependencies**: GATE 1 passed

#### Objectives
- Implement word-by-word streaming using `astream_events`
- Measure first-token latency and end-to-end performance
- Compare with AnsariClaude baseline
- **DECISION POINT**: Reject if streaming broken or >10% performance overhead

#### Deliverables
- [ ] Streaming support via `astream_events` method
- [ ] `tests/test_langgraph_streaming.py` - Streaming verification
- [ ] `benchmarks/compare_performance.py` - Side-by-side latency comparison
- [ ] Performance report: first-token latency, end-to-end latency, overhead %

#### Implementation Details

**Streaming Strategy**:

1. **Phase 2a: Non-Streaming First (2 hours)**:
   - Validate graph orchestration with `stream=False` in Anthropic calls
   - Ensure correct execution flow before adding streaming complexity
   - Measure baseline performance

2. **Phase 2b: Enable Streaming (2 hours)**:
   - Use LangGraph's `astream_events()` for event-based streaming
   - Filter events to extract content deltas
   - Forward chunks to match current streaming interface

**Implementation**:
```python
async def stream_query(self, message: str):
    """Stream response chunks."""
    async for event in self.graph.astream_events(
        {"messages": [{"role": "user", "content": message}]},
        version="v1"
    ):
        # Filter for content chunks
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content
```

**Performance Measurement**:
```python
# benchmarks/compare_performance.py
import time
from ansari_claude import AnsariClaude
from ansari_langgraph import AnsariLangGraph

queries = [
    "Tell me about prayer",
    "What does the Quran say about charity?",
    # ... 5-10 test queries
]

for impl in [AnsariClaude, AnsariLangGraph]:
    for query in queries:
        start = time.time()
        first_token_time = None

        async for chunk in impl.stream_query(query):
            if first_token_time is None:
                first_token_time = time.time() - start

        end_to_end = time.time() - start
        # Log metrics
```

#### Acceptance Criteria
- [ ] Streaming works: chunks arrive incrementally, not all at once
- [ ] First-token latency measured and comparable to AnsariClaude
- [ ] End-to-end latency overhead <10% vs AnsariClaude
- [ ] No streaming-related errors or incomplete responses
- [ ] Chunk cadence feels natural (no large gaps)

#### Test Plan
- **Unit Tests**: Event filtering logic works correctly
- **Integration Tests**:
  - Complete response assembled correctly from chunks
  - No chunks lost or duplicated
- **Performance Tests**:
  - Run 10 queries through both implementations
  - Statistical comparison (mean, p95 latency)
- **Manual Testing**: Subjective streaming experience

#### Rollback Strategy
If streaming fails: Document issue, consider if non-streaming LangGraph still valuable, update decision accordingly.

#### Risks
- **Risk**: LangGraph's event stream is too granular/noisy
  - **Mitigation**: Build robust event filtering early
- **Risk**: Streaming adds unacceptable latency
  - **Mitigation**: Profile and identify bottleneck, consider if architectural
- **Risk**: Events don't map cleanly to Anthropic's streaming format
  - **Mitigation**: Document impedance mismatch for decision

---

### GATE 3: Comparison & Metrics (4 hours)

**Dependencies**: GATE 2 passed

#### Objectives
- Collect all quantitative comparison metrics
- Run structured comparison harness across all three implementations
- Generate comparison report with recommendation
- **DECISION POINT**: Adopt, reject, or defer based on evidence

#### Deliverables
- [ ] Ad-hoc comparison scripts in `tmp/` (run directly, not committed)
- [ ] `codev/reviews/0002-langgraph-implementation.md` - Comparison report
- [ ] Decision: Adopt/Reject/Defer with clear rationale

#### Implementation Details

**Comparison Harness**:
```python
# benchmarks/comparison_harness.py
import json
from dataclasses import dataclass, asdict

@dataclass
class ComparisonMetrics:
    implementation: str
    query: str
    first_token_latency_ms: float
    end_to_end_latency_ms: float
    token_count: int
    tool_calls: list[str]
    citations_count: int
    message_history_size: int
    errors: list[str]

# Test prompts covering:
# - Happy path (tool call needed)
# - No results
# - Multi-turn conversation
# - Error handling (simulated API timeout)

results = []
for impl in [AnsariClaude, AnsariAgent, AnsariLangGraph]:
    for query in test_queries:
        metrics = run_query_and_measure(impl, query)
        results.append(metrics)

# Save to JSON for analysis
with open("comparison_results.json", "w") as f:
    json.dump([asdict(r) for r in results], f, indent=2)
```

**Complexity Analysis**:
```bash
# benchmarks/complexity_analysis.sh
#!/bin/bash

echo "=== Code Complexity Comparison ==="

echo "\n--- AnsariClaude ---"
radon cc -s -a ../ansari-backend/src/ansari/agents/ansari_claude.py
radon mi ../ansari-backend/src/ansari/agents/ansari_claude.py

echo "\n--- AnsariLangGraph ---"
radon cc -s -a src/ansari_langgraph/
radon mi src/ansari_langgraph/

echo "\n--- Lines of Code ---"
cloc ../ansari-backend/src/ansari/agents/ansari_claude.py
cloc src/ansari_langgraph/
```

**Extensibility Test**:
- Document exact steps to add a hypothetical "SearchHadith" tool to each implementation
- Count: files changed, lines added, complexity of changes

**Comparison Report Structure** (codev/reviews/0002-langgraph-implementation.md):
1. Executive Summary (Recommendation)
2. Quantitative Metrics (tables, charts)
3. Qualitative Assessment (maintainability, debugging experience)
4. Three-Way Comparison (AnsariClaude vs AnsariAgent vs AnsariLangGraph)
5. Decision Rationale
6. Next Steps

#### Acceptance Criteria
- [ ] All metrics collected and documented
- [ ] Comparison harness runs successfully on all implementations
- [ ] Clear recommendation with supporting evidence
- [ ] No outstanding questions about LangGraph fit

#### Test Plan
- **Validation**: Run harness 3 times to ensure consistency
- **Review**: Cross-check metrics with manual observations
- **Documentation**: Ensure findings are reproducible

#### Rollback Strategy
N/A - This is the final decision phase. If inconclusive, recommendation is "defer."

#### Risks
- **Risk**: Results are mixed (some metrics better, some worse)
  - **Mitigation**: Prioritize metrics (deployment simplicity > minor performance differences)
- **Risk**: Not enough data to make confident decision
  - **Mitigation**: Add more test scenarios or extend evaluation timeline

---

## Dependency Map

```
GATE 0 (30 min)     Verify dependencies, async support
     ↓
GATE 1 (4 hours)    Tool integration with citations
     ↓
GATE 2 (4 hours)    Streaming & performance
     ↓
GATE 3 (4 hours)    Comparison & decision
     ↓
Review Phase        Document findings
```

**Total Timeline**: 12.5 hours (1.5-2 days) if all gates pass

**Failure Paths**: Any gate can trigger early rejection and immediate jump to Review phase

## Resource Requirements

### Development Resources
- **Engineers**: Waleed (solo implementation)
- **Environment**: Local development with API access to:
  - Anthropic API (Claude 3.5 Sonnet)
  - Kalimat API (Quran search)

### Infrastructure
- No new infrastructure required (prototype evaluation)
- Uses existing ansari-backend config and API keys
- Feature flag environment variable: `ANSARI_IMPL=langgraph`

## Integration Points

### External Systems
- **Anthropic API**:
  - Integration Type: Direct HTTP API via `anthropic` Python SDK
  - Phase: GATE 1
  - Fallback: Reject LangGraph if incompatible

- **Kalimat API** (Quran search):
  - Integration Type: HTTP REST API via httpx
  - Phase: GATE 1
  - Fallback: N/A (already proven working)

### Internal Systems
- **ansari-backend tools** (SearchQuran):
  - Integration Type: Import and reuse existing tool classes
  - Phase: GATE 1
  - Fallback: Create minimal tool adapter if import incompatible

- **ansari-backend validation logic**:
  - Integration Type: Import helper functions
  - Phase: GATE 1
  - Fallback: Reimplement if necessary, but document extra complexity

## Risk Analysis

### Technical Risks

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| LangGraph has hidden dependencies | Low | High | GATE 0 verification | Waleed |
| Content-block impedance mismatch | Medium | High | Test exact sequence in GATE 1 | Waleed |
| Streaming incompatibility | Low | Medium | Phased approach (non-streaming first) | Waleed |
| Performance overhead too high | Low | Medium | Early benchmarking, profiling if needed | Waleed |
| Abstraction leak (complex logic doesn't fit) | Medium | Medium | Test tool formatting early | Waleed |
| Debugging complexity | Medium | Low | Intentional error injection test | Waleed |

### Schedule Risks

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Gate blockers delay timeline | Medium | Low | Fail-fast gates prevent sunk cost | Waleed |
| Scope creep (trying all 4 tools) | Low | Medium | Stick to SearchQuran only per spec | Waleed |
| Perfect-seeking delays decision | Low | Low | Time-box each gate strictly | Waleed |

## Validation Checkpoints

1. **After GATE 0**:
   - Verify dependency tree is clean (no Node.js, no binaries)
   - Async httpx confirmed working
   - Decision: Continue or reject

2. **After GATE 1**:
   - Tool integration working correctly
   - Citations preserved end-to-end
   - Message validation passing
   - Decision: Continue or reject

3. **After GATE 2**:
   - Streaming functional and performant
   - Performance metrics within acceptable range
   - Decision: Continue or reject

4. **After GATE 3**:
   - All comparison metrics collected
   - Recommendation clear
   - Decision: Adopt, reject, or defer

## Monitoring and Observability

### Metrics to Track (During Implementation)
- **Build Time**: Time spent at each gate (for SPIDER review)
- **Code Volume**: Lines of code added/changed
- **Test Coverage**: Percentage (target >90%)
- **Cyclomatic Complexity**: Per module and average

### Metrics to Track (In Comparison)
- **Performance**:
  - First-token latency (ms, p50/p95)
  - End-to-end latency (ms, p50/p95)
  - Memory usage (MB peak)
  - Token count (if available)
- **Correctness**:
  - Citation count (should match across implementations)
  - Message history structure (diff with AnsariClaude)
  - Tool call arguments (exact match expected)
- **Maintainability**:
  - Cyclomatic complexity (lower is better)
  - Maintainability index (higher is better)
  - Lines to add new tool (fewer is better)

### Logging Requirements
- **Development**: DEBUG level for graph execution, state transitions
- **Testing**: INFO level with structured JSON logs for metric extraction
- **Comparison**: Capture full message histories for diffing

### Alerting
N/A (prototype evaluation, not production deployment)

## Documentation Updates Required

- [x] Specification document (already created)
- [ ] Implementation notes (real-time during gates)
- [ ] Comparison report (GATE 3 deliverable)
- [ ] API documentation (only if adopting LangGraph)
- [ ] Architecture diagrams (update if LangGraph adopted)

## Post-Implementation Tasks

### If LangGraph Adopted:
- [ ] Expand to all 4 tools (Hadith, Mawsuah, Tafsir)
- [ ] Performance validation in staging environment
- [ ] Migration plan from AnsariClaude to AnsariLangGraph
- [ ] Load testing with production-like traffic
- [ ] Integration with existing presenters (API, Discord, WhatsApp)
- [ ] Rollout plan (feature flag, gradual rollout)

### If LangGraph Rejected:
- [ ] Archive prototype code for reference
- [ ] Document rejection rationale clearly
- [ ] Update CLAUDE.md with findings
- [ ] Consider alternative solutions (if needed)

## Expert Review

**Status**: Pending (will consult after plan draft)

## Approval

- [ ] Technical Lead Review (Waleed)
- [ ] Expert AI Consultation Complete

## Change Log

| Date | Change | Reason | Author |
|------|--------|--------|--------|
| 2025-10-06 | Initial draft | Spec approved, moving to Plan phase | Claude |

## Notes

### Critical Design Decisions

1. **Keep Anthropic Client Direct**:
   - Rationale: Isolates LangGraph value from LangChain abstractions
   - Allows direct comparison with AnsariClaude's API usage
   - Reduces variables in evaluation

2. **Reuse ansari-backend Logic**:
   - Validation: `_validate_message_history`, `_fix_tool_use_result_relationship`
   - Formatting: Tool result document blocks, citation extraction
   - Rationale: Proves LangGraph doesn't require rewriting everything

3. **Separate Codebases for Clean Comparison**:
   - Keep implementations completely separate
   - No shared code or feature flags
   - Enables true apples-to-apples comparison of architecture and complexity
4. **Streaming as Separate Phase**:
   - Validate orchestration first with `stream=False`
   - De-risks dual complexity (graph + streaming)
   - Clear failure point if streaming incompatible

### Comparison to Claude Agent SDK Evaluation

**Similarities**:
- Gated approach with fail-fast criteria
- Focus on production viability (dependencies, deployment)
- Quantitative metrics emphasis

**Differences**:
- **More rigorous**: 4 gates vs previous ad-hoc approach
- **Quantitative focus**: Cyclomatic complexity, radon metrics, structured comparison
- **Three-way comparison**: Explicit comparison across all candidates
- **Shorter timeline**: 12.5 hours vs ~5.5 hours (but more structured)

### Open Questions (To Resolve During Implementation)

1. **Multi-step workflows**: How much easier is it to add complex workflows? (extensibility test in GATE 3)
2. **LangSmith integration**: Worth exploring for observability? (defer to post-adoption if adopted)
