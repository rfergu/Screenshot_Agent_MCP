# 📘 Screenshot Agent Blueprint

This blueprint contains everything you need to **rebuild the Screenshot Agent from specifications** - no code included, just the architectural vision and learnings.

## What's Inside

```
blueprint/
├── SPECHINT.md                      # 💡 START HERE - Tips & gotchas from the original build
├── README_BLUEPRINT.md              # You are here!
├── .specify/
│   └── memory/
│       └── constitution.md          # Non-negotiable principles (v2.1.0)
├── specs/
│   └── 001-screenshot-organizer/
│       ├── spec.md                  # Full functional specification
│       ├── plan.md                  # Implementation plan
│       ├── tasks.md                 # Detailed task breakdown
│       ├── data-model.md            # Data structures
│       ├── research.md              # Technology choices & rationale
│       ├── quickstart.md            # Quick start guide
│       └── contracts/
│           └── mcp-api-spec.json    # MCP tool contracts
├── HANDOFF.md                       # How to rebuild from spec (11 steps)
├── TRACEABILITY.md                  # Maps requirements → plan → code
├── MAINTAINERS.md                   # Governance & decision authority
└── README.md                        # Project overview
```

## How to Use This Blueprint

### Option 1: Rebuild From Scratch (Recommended for Learning)

Follow the SpecKit workflow:

1. **Read the Constitution** (`.specify/memory/constitution.md`)
   - Understand non-negotiable constraints
   - Note required technology stack (Article X)

2. **Study the Spec** (`specs/001-screenshot-organizer/spec.md`)
   - **Read SPECHINT.md first!** It'll save you hours
   - Understand the PRIMARY GOAL (Agent Framework + MCP demo)
   - Review user stories and functional requirements

3. **Review the Plan** (`specs/001-screenshot-organizer/plan.md`)
   - See how requirements map to architecture
   - Understand the "Brain vs Hands" pattern

4. **Follow HANDOFF.md**
   - 11-step process from clone to completion
   - Includes validation steps

### Option 2: Reference Implementation

If you have access to the original codebase, use `TRACEABILITY.md` to see how each spec requirement was implemented.

## Why No Code?

This blueprint is designed to:
- ✅ Test if the spec is truly "rebuild-ready"
- ✅ Serve as a portable architectural reference
- ✅ Enable spec-driven development practice
- ✅ Focus on WHAT to build, not HOW it was built

The implementation details are in the spec, plan, and tasks. The code is just one way to satisfy those requirements.

## Key Documents Explained

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **SPECHINT.md** | Practical tips & gotchas | **Read first!** Saves hours of debugging |
| **constitution.md** | Non-negotiable constraints | Before planning |
| **spec.md** | What to build | Start here for requirements |
| **plan.md** | How to structure it | Before coding |
| **HANDOFF.md** | Step-by-step rebuild | When actually building |
| **TRACEABILITY.md** | Requirements → code map | For validation |

## Success Criteria

You've successfully rebuilt when:
- ✅ All user stories (US-001 through US-009) work
- ✅ Constitution principles are satisfied
- ✅ TRACEABILITY.md requirements map to your code
- ✅ The agent demonstrates Agent Framework + MCP integration
- ✅ OCR-first processing works with Vision fallback

## Support & Questions

This is a demonstration project. If you're rebuilding:
- Reference SPECHINT.md for common issues
- Check TRACEABILITY.md for requirement mappings
- The spec should answer most questions!

## What You'll Build

A **production AI agent demonstration** showing:
- Microsoft Agent Framework for conversational orchestration
- Model Context Protocol (MCP) for standardized tool integration
- OCR-first processing with GPT-4o Vision fallback
- 7-phase conversational UX
- Unified architecture (Agent WITH embedded MCP, not separate)

**Use Case:** Screenshot organization (but the architecture is the real demo)

## Quick Start

```bash
# 1. Read these in order:
cat SPECHINT.md                                    # Tips first!
cat .specify/memory/constitution.md                # Constraints
cat specs/001-screenshot-organizer/spec.md         # Requirements

# 2. Follow the rebuild process:
cat HANDOFF.md                                     # 11-step guide

# 3. Validate against:
cat TRACEABILITY.md                                # Check your implementation
```

---

**Built Date:** 2025-11-12
**Constitution Version:** 2.1.0
**Spec Version:** See spec.md header

Good luck rebuilding! 🚀
