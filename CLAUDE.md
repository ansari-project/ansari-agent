# Ansari-Agent Project Instructions for AI Agents

## Project Context

This is an exploratory project to evaluate the Claude Agent SDK for the next version of Ansari. The goal is to prototype and assess whether the SDK can replace or complement the current agent implementation in [ansari-backend](../ansari-backend).

## Codev Methodology

This project uses the Codev context-driven development methodology with the **SPIDER protocol**.

### Active Protocol
- **Protocol**: SPIDER (with multi-agent consultation)
- **Location**: [codev/protocols/spider/protocol.md](codev/protocols/spider/protocol.md)

### Directory Structure
```
ansari-agent/
├── codev/
│   ├── protocols/spider/    # Protocol documentation and templates
│   ├── specs/               # Feature specifications (WHAT to build)
│   ├── plans/               # Implementation plans (HOW to build)
│   ├── reviews/             # Reviews and lessons learned
│   └── resources/           # Reference materials
├── CLAUDE.md                # This file
└── [exploration code]       # Prototypes and experiments
```

### File Naming Convention

Use sequential numbering with descriptive names:
- Specification: `codev/specs/0001-feature-name.md`
- Plan: `codev/plans/0001-feature-name.md`
- Review: `codev/reviews/0001-feature-name.md`

## Core Workflow

1. **When building NEW features**: Start with the Specification phase
2. **Create exactly THREE documents per feature**: spec, plan, and lessons (all with same filename)
3. **Follow the SP(IDE)R phases**: Specify → Plan → (Implement → Defend → Evaluate) → Review
4. **Use multi-agent consultation** by default unless user says "without consultation"

### Multi-Agent Consultation

**DEFAULT BEHAVIOR**: Consultation is ENABLED by default with:
- **Gemini 2.5 Pro** (gemini-2.5-pro) for deep analysis
- **GPT-5** (gpt-5) for additional perspective

To disable: User must explicitly say "without multi-agent consultation"

**Consultation Checkpoints**:
1. **Specification Phase**: After draft and after human review
2. **Planning Phase**: After plan creation and after human review
3. **Implementation Phase**: After code implementation
4. **Defend Phase**: After test creation
5. **Evaluation Phase**: After evaluation completion
6. **Review Phase**: After review document

## Git Workflow

### 🚨 ABSOLUTE PROHIBITION: NEVER USE `git add -A` or `git add .` 🚨

**THIS IS A CRITICAL SECURITY REQUIREMENT - NO EXCEPTIONS**

**BANNED COMMANDS (NEVER USE THESE)**:
```bash
git add -A        # ❌ ABSOLUTELY FORBIDDEN
git add .         # ❌ ABSOLUTELY FORBIDDEN
git add --all     # ❌ ABSOLUTELY FORBIDDEN
```

**MANDATORY APPROACH - ALWAYS ADD FILES EXPLICITLY**:
```bash
# ✅ CORRECT - Always specify exact files
git add codev/specs/0001-feature.md
git add src/prototype.py
git add tests/test_prototype.py
```

**BEFORE EVERY COMMIT**:
1. Run `git status` to see what will be added
2. Add each file or directory EXPLICITLY by name
3. Never use shortcuts that could add unexpected files

### Commit Messages
```
[Spec 0001] Initial specification draft
[Plan 0001] Implementation plan with consultation
[Impl 0001] Working prototype
```

### Branch Naming
```
spider/0001-feature-name/spec
spider/0001-feature-name/plan
spider/0001-feature-name/implementation
```

## Project-Specific Context

### Related Repositories
- **Ansari Backend**: [../ansari-backend](../ansari-backend) - Current implementation using LiteLLM + Anthropic SDK
- **Codev**: [../codev](../codev) - The Codev methodology source repository

### Current Exploration Goals
1. Evaluate Claude Agent SDK for Ansari v.Next
2. Create working prototypes to assess feasibility
3. Document findings, comparisons, and recommendations
4. Determine migration path (if SDK is adopted)

### Key Technologies
- **Python**: Primary language (use `uv` for package management)
- **Claude Agent SDK**: Main technology being evaluated
- **Ansari Tools**: Quran, Hadith, Mawsuah search tools to be integrated

### Claude Agent SDK - Evaluation Result

**EVALUATION COMPLETE**: ❌ **NOT RECOMMENDED for Ansari Backend**

**Critical Finding**: The Claude Agent SDK v0.1.0 is a **wrapper around Claude Code CLI**, not a standalone SDK.

**Actual Architecture**:
```
Python SDK → Subprocess → Claude Code CLI → Anthropic API
```

**Requirements** (ALL required, not optional):
- Python 3.10+
- Anthropic API key
- **Node.js** (for CLI)
- **Claude Code CLI** (`npm install -g @anthropic-ai/claude-code`)

**Why It Doesn't Work for Ansari**:
1. Requires CLI subprocess (adds complexity)
2. Needs Node.js dependency (Python backend shouldn't need Node.js)
3. Extra process overhead (Python → CLI → API instead of Python → API)
4. Deployment complexity (must install and manage CLI in production)
5. No clear benefits over direct Anthropic SDK usage

**Recommendation**: Continue using Anthropic SDK directly (via litellm or direct)

**Use Case Where SDK Makes Sense**: Local development tools, interactive debugging, IDE integrations

**Evaluation Details**: See [codev/reviews/0001-claude-sdk-evaluation.md](codev/reviews/0001-claude-sdk-evaluation.md)

## Python Development Preferences

### Package Management
- Use **uv** for package management (NOT pip directly)
- Add dependencies with: `uv add package-name`
- Install with: `uv sync`

### File Organization
- Store exploratory/temporary code in `tmp/` directory
- Keep production prototypes in `src/` or root as appropriate
- Ensure `.gitignore` is configured

### Module Execution
- Set `PYTHONPATH=src` when needed
- Use `-m` flag for module execution: `PYTHONPATH=src python -m module.name`
- **NEVER** create runner scripts or wrapper scripts

## Important Notes

1. **ALWAYS check** [codev/protocols/spider/protocol.md](codev/protocols/spider/protocol.md) for detailed phase instructions
2. **Use provided templates** from `codev/protocols/spider/templates/`
3. **This is exploratory work** - experimentation is encouraged, but document findings
4. **Consult multi-agent** before presenting significant results to user
5. **Follow user's global preferences** in `~/.claude/CLAUDE.md` (especially git and Python preferences)

## For Detailed Instructions

**READ THE FULL PROTOCOL**: [codev/protocols/spider/protocol.md](codev/protocols/spider/protocol.md)

This contains:
- Detailed phase descriptions
- Required evidence for each phase
- Expert consultation requirements
- Templates and examples
- Best practices

---

*Remember: Context drives code. When in doubt, write more documentation rather than less.*
