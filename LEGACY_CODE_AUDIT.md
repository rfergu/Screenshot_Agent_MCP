# Legacy Code Audit - Code Not Aligned with Updated Spec

**Date:** 2025-11-12
**Context:** After spec clarity fixes, identified code that doesn't align with current architecture

---

## Summary

After Phase 2 restructure (commit b7198a2) moved code into `src/agent/` and `src/screenshot_mcp/` packages, several legacy files remain in `src/` root. Additionally, one file has an outdated name that doesn't match the updated spec terminology.

---

## Issue 1: Legacy Files in src/ Root (Post-Phase 2 Restructure)

### 🔴 CRITICAL: Old Structure Files Still Present

After Phase 2 restructure created the new package structure, the old files were NOT deleted. The CLI now uses the new structure, but legacy files remain:

| Legacy File | New Location | Status | Action Needed |
|-------------|--------------|--------|---------------|
| `src/agent_client.py` | `src/agent/client.py` | ❌ Unused | Delete |
| `src/mcp_client_wrapper.py` | `src/screenshot_mcp/client_wrapper.py` | ❌ Unused | Delete |
| `src/mcp_tools.py` | `src/screenshot_mcp/tools/*.py` | ❌ Unused | Delete |
| `src/screenshot_mcp_server.py` | `src/screenshot_mcp/server.py` | ❌ Unused | Delete |

**Verification:**
```bash
# CLI uses NEW structure:
$ grep "from agent.client import" src/cli_interface.py
from agent.client import AgentClient

# Nobody imports OLD structure:
$ grep -r "from agent_client import" src/ --include="*.py"
# (no results)
```

**Why They Exist:**
Phase 2 restructure (Task T-030) copied files to new locations but didn't remove originals.

**Risk:**
- Confusion for developers (which file is canonical?)
- Code drift if someone edits the wrong file
- Import errors if old imports are accidentally used

**Recommendation:**
```bash
# Delete legacy files after verifying tests still pass
rm src/agent_client.py
rm src/mcp_client_wrapper.py
rm src/mcp_tools.py
rm src/screenshot_mcp_server.py
```

---

## Issue 2: Outdated Filename - `phi3_chat_client.py`

### 🟡 IMPORTANT: Filename Uses Deprecated Model Name

**File:** `src/phi3_chat_client.py`

**Problem:**
- Filename references "phi3" (old model)
- Spec now uses "Phi-4-mini" everywhere
- Class inside is correctly named `LocalFoundryChatClient`
- File docstring correctly describes Phi-4/Phi-4-mini

**Current State:**
```python
# File: src/phi3_chat_client.py
"""Local AI Foundry chat client for Microsoft Agent Framework.

Local models (Phi-4, Phi-4-mini) do NOT reliably support:
- Function/tool calling
- Screenshot analysis
...
"""

class LocalFoundryChatClient(BaseChatClient):
    """Local AI Foundry chat client - TESTING ONLY."""
```

**Why It Matters:**
- Spec removed all Phi-3 references (commit c2b9191)
- Filename should match current model naming
- "LocalFoundry" is more accurate than "Phi3" (it's a generic local client)

**Imported By:**
- `src/agent/modes.py:53`: `from phi3_chat_client import LocalFoundryChatClient`

**Recommendation:**
```bash
# Rename file to match class name
mv src/phi3_chat_client.py src/local_foundry_chat_client.py

# Update import
sed -i '' 's/from phi3_chat_client import/from local_foundry_chat_client import/g' src/agent/modes.py
```

**Alternative:** Keep filename if changing imports is risky, but add comment:
```python
# File: src/phi3_chat_client.py
"""
LEGACY FILENAME: This file is named phi3_chat_client.py for historical reasons,
but supports any local AI Foundry model (Phi-4, Phi-4-mini, etc.)
The class name LocalFoundryChatClient is more accurate.
"""
```

---

## Issue 3: Package-Level Docstring Misrepresents Project

### 🟢 MINOR: Generic Package Description

**File:** `src/__init__.py`

**Current Content:**
```python
"""Screenshot Organizer package."""

__version__ = "0.1.0"
```

**Problem:**
- Says "Screenshot Organizer" (implies it's a screenshot app)
- Spec now emphasizes this is an "Agent Framework + MCP Demo"

**Recommendation:**
```python
"""Screenshot Agent: Microsoft Agent Framework + MCP Client Demo.

Demonstrates production AI agent patterns using:
- Microsoft Agent Framework for conversational orchestration
- Model Context Protocol (MCP) for standardized tool integration
- Azure OpenAI GPT-4 for reliable tool calling

The screenshot organization use case demonstrates multi-step tool orchestration.
"""

__version__ = "0.1.0"
```

---

## Issue 4: CLI Help Text Could Emphasize Demo Purpose

### 🟢 MINOR: CLI Description Generic

**File:** `src/cli_interface.py:234-238`

**Current:**
```python
@click.option(
    '--local',
    is_flag=True,
    default=False,
    help="Use local testing mode (Phi-4-mini, no tools). Default is remote mode (GPT-4, full capabilities)."
)
```

**Enhancement:**
```python
@click.option(
    '--local',
    is_flag=True,
    default=False,
    help="Use local testing mode (Phi-4-mini, no tools) to test Agent Framework setup. Default is remote mode (GPT-4, full MCP demo)."
)
```

---

## Prioritized Action Plan

### Phase 1: Remove Legacy Files (High Priority)
```bash
# Verify tests pass with new structure
pytest -v

# Remove old files
rm src/agent_client.py
rm src/mcp_client_wrapper.py
rm src/mcp_tools.py
rm src/screenshot_mcp_server.py

# Verify nothing broke
pytest -v
python -m src.cli_interface --help
```

**Risk:** Low (files are unused)
**Impact:** Prevents future confusion

### Phase 2: Rename phi3_chat_client.py (Medium Priority)
```bash
# Rename file
git mv src/phi3_chat_client.py src/local_foundry_chat_client.py

# Update import
sed -i '' 's/from phi3_chat_client import/from local_foundry_chat_client import/g' src/agent/modes.py

# Verify tests pass
pytest -v tests/test_local_mode.py tests/test_smoke_local.py
```

**Risk:** Medium (changes active import)
**Impact:** Aligns filename with spec terminology

### Phase 3: Update Package Docstrings (Low Priority)
```bash
# Update src/__init__.py
# Update CLI help text in src/cli_interface.py
```

**Risk:** None (cosmetic)
**Impact:** Reinforces demo purpose

---

## Validation After Cleanup

### Pre-Cleanup State
```bash
$ ls src/*.py | wc -l
8  # (includes 4 legacy files + 4 active files)
```

### Post-Cleanup Expected State
```bash
$ ls src/*.py
src/__init__.py
src/cli_interface.py
src/local_foundry_chat_client.py  # (renamed from phi3_chat_client.py)
src/session_manager.py

$ ls src/agent/*.py
src/agent/__init__.py
src/agent/client.py
src/agent/modes.py
src/agent/prompts.py

$ ls src/screenshot_mcp/*.py
src/screenshot_mcp/__init__.py
src/screenshot_mcp/client_wrapper.py
src/screenshot_mcp/server.py
```

---

## Tests to Run After Cleanup

```bash
# All unit tests
pytest -v

# Local mode specific
pytest tests/test_local_mode.py -v
pytest tests/test_smoke_local.py -v

# Integration tests
pytest tests/test_integration.py -v

# Manual smoke test
python -m src.cli_interface --help
python -m src.cli_interface --local  # (requires foundry service running)
```

---

## Related Documents

- **SPEC_CLARITY_FIXES.md** - Documented spec issues (Phi-3 references, local mode confusion)
- **specs/001-screenshot-organizer/spec.md** - Updated spec emphasizing demo purpose
- **TRACEABILITY.md** - Maps Phase 2 restructure (Task T-030, T-033)

---

*End of Legacy Code Audit*
