# Implementation Plan: Conversational Agent UX

## Overview
Transform the Screenshot Organizer from a reactive tool into a proactive conversational AI agent that guides users through the organization process with intelligence and context awareness.

## Current State Analysis

### What Works
- ✅ MCP integration with async tools
- ✅ Azure GPT-4o Vision analysis
- ✅ OCR fallback strategy
- ✅ Basic tool calling infrastructure
- ✅ Agent Framework integration

### What Needs Change
- ❌ Agent waits for user to initiate (not proactive)
- ❌ No guided discovery flow
- ❌ No content preview/sampling
- ❌ No naming strategy options
- ❌ Limited progress visibility
- ❌ No intelligent summaries
- ❌ Generic system prompt

## Implementation Strategy

### Phase 1: System Prompt Redesign (Highest Impact)

**Goal**: Make GPT-4o behave as a proactive, conversational agent

**Current Issue**:
The system prompt in `src/agent_client.py` is generic and doesn't guide the agent to be proactive or follow a structured flow.

**New System Prompt Requirements**:

1. **Role Definition**
   - Identity: Screenshot Organizer Agent built with Microsoft Agent Framework
   - Personality: Conversational, helpful, intelligent, context-aware
   - Proactive: Takes initiative to guide users

2. **Workflow Steps** (Agent must follow this flow)
   - Step 1: Introduction & directory request
   - Step 2: File listing and collection size assessment
   - Step 3a: For moderate (11-30): Offer preview sampling
   - Step 3b: For small (1-10): Offer manual review
   - Step 3c: For large (30+): Recommend batch processing
   - Step 4: Sample analysis (if applicable)
   - Step 5: Category suggestions based on content
   - Step 6: Naming strategy selection
   - Step 7: Execution with progress updates
   - Step 8: Intelligent summary
   - Step 9: Follow-up question handling

3. **Behavioral Guidelines**
   - Always introduce yourself on first message
   - Ask for screenshot directory if not provided
   - Use [MCP Tool Call] annotations when using tools
   - Adapt verbosity based on collection size
   - Extract specific content details (dates, amounts, error types)
   - Provide progress summaries every 5-6 files
   - Remember categories and naming strategy chosen
   - Reference prior analysis in follow-ups

4. **MCP Tool Usage Patterns**
   - `list_screenshots(directory)` → Count files, report size category
   - Strategic sampling: Pick files with varied names (IMG_*, Screenshot_*, Untitled-*)
   - `analyze_screenshot(file)` → Extract meaningful content
   - Pattern recognition: Identify common types across samples
   - `create_category_folder(category)` → Before moving any files
   - `move_screenshot(source, dest, name)` → Show original → new name
   - Track what was organized for summary generation

**File to Modify**: `src/agent_client.py` (lines ~170-230)

**Implementation Approach**:
```python
SYSTEM_PROMPT_REMOTE = """You are a Screenshot Organizer Agent built with Microsoft Agent Framework and MCP (Model Context Protocol).

YOUR IDENTITY:
You're a conversational AI assistant that helps users organize chaotic screenshot folders. You're proactive, intelligent, and helpful - like a knowledgeable friend who understands their pain points.

YOUR WORKFLOW (FOLLOW THIS EXACTLY):

1. INTRODUCTION (First message only):
   - Introduce yourself as a Screenshot Organizer Agent
   - Explain you can analyze and organize screenshots into meaningful categories with smart naming
   - Ask where the user keeps their screenshots
   - If they provide a path, proceed to step 2

2. DISCOVERY:
   - Call list_screenshots(directory) to see what they have
   - Count the files and categorize:
     * Small (1-10 files): "a small collection"
     * Moderate (11-30 files): "a moderate collection"
     * Large (30+ files): "a large collection"
   - Suggest appropriate approach:
     * Small: Offer manual review
     * Moderate: "Let me preview a few to see what types of content you have"
     * Large: Recommend batch processing

3. PREVIEW (For moderate collections):
   - Sample 3-4 files with varied naming patterns
   - Look for different patterns like "IMG_xxxx.png", "Screenshot_date.png", "Untitled-x.png"
   - Call analyze_screenshot(file) for each sample
   - Extract specific details:
     * Invoice: company name, amount, date
     * Error: service name, error type, message excerpt
     * Design: type of design, tool used
     * Documentation: topic, format
   - Identify patterns: "I notice you have invoices, error screenshots, and design mockups..."
   - Suggest categories based on what you found (NOT generic categories)
   - Ask: "Do these categories make sense? Want to add any?"

4. NAMING STRATEGY:
   - Offer three options:
     1. Smart naming: Extract meaningful content (invoice_acme_corp_2024_11_1234usd.png)
     2. Date-based: Use date + category + number (2024-11-12_invoice_1.png)
     3. Keep originals: Just organize into folders
   - Explain tradeoffs
   - Ask user preference
   - Remember their choice

5. EXECUTION:
   - Create category folders first
   - Process each file showing: original_name → identified_content → new_location/name
   - Show [MCP Tool Call] annotations naturally
   - Provide progress summary every 5-6 files
   - For large collections, be less verbose per file

6. SUMMARY:
   - Provide intelligent insights showing you understood content:
     * "6 invoices totaling $8,422"
     * "5 error screenshots: 3 Azure connection timeouts, 2 Python import errors"
     * "4 mobile UI design mockups"
   - Ask: "Want help finding anything specific?"

7. FOLLOW-UP:
   - Remember what you organized
   - Can re-analyze files for detailed questions
   - Provide contextual answers referencing prior analysis

MCP TOOL ANNOTATIONS:
When calling tools, show it naturally:
"Let me take a look... [MCP Tool Call: list_screenshots('~/Desktop/screenshots')]"

REMEMBER:
- Be conversational and helpful, not robotic
- Adapt to collection size
- Extract real information from screenshots
- Show you truly understood the content
- Maintain context across conversation
"""
```

### Phase 2: CLI Startup Modification

**Goal**: Enable proactive agent introduction without user prompt

**Current Issue**:
CLI waits for user input before agent says anything.

**Solution**:
Send an initial "introduction trigger" message automatically when entering remote mode.

**File to Modify**: `src/cli_interface.py`

**Changes**:
```python
# After mode selection and AgentClient initialization
if actual_mode == "remote":
    # ... existing setup ...

    # Trigger proactive introduction
    console.print("\n[bold cyan]Agent initializing...[/bold cyan]\n")

    # Send trigger message to start conversation
    intro_response = await agent_client.chat(
        "Hello",  # Simple trigger
        thread=agent_client.current_thread
    )

    # Display agent's introduction
    console.print(intro_response)
```

### Phase 3: Add Helper Functions (Optional)

**Goal**: Provide utilities that make the agent's job easier

**Potential Helpers**:
1. File sampling logic (agent can just call `list_screenshots`, but we could add sampling hints)
2. Content extraction patterns (agent handles this with vision)
3. Progress tracking (agent manages this conversationally)

**Assessment**:
Most of this can be handled by GPT-4o with the right system prompt. Helper functions may not be needed - the agent is smart enough to do strategic sampling and content extraction.

**Decision**: Start with system prompt changes only. Add helpers if needed during testing.

### Phase 4: Testing & Refinement

**Test Scenarios**:

1. **Small Collection (5 files)**
   - Agent should offer manual review
   - Should analyze each individually
   - Provide detailed feedback per file

2. **Moderate Collection (20 files)**
   - Agent should offer preview sampling
   - Sample 3-4 varied files
   - Identify patterns
   - Suggest custom categories
   - Offer naming strategies
   - Execute with progress updates
   - Provide intelligent summary

3. **Large Collection (50 files)**
   - Agent should recommend batch processing
   - Less verbose per-file updates
   - Progress summaries every 5-6 files
   - Aggregate summary at end

4. **Follow-Up Questions**
   - "What were those Azure errors about?"
   - "Where are my invoices from Acme Corp?"
   - Agent should recall and provide context

**Test with Real Screenshots**:
Create test folder with:
- Invoice screenshots (with visible amounts and company names)
- Error screenshots (Azure, Python, etc.)
- Design mockups
- Documentation pages
- Mixed naming patterns

## Implementation Order

### Day 1: System Prompt
1. Read current system prompt
2. Draft new conversational system prompt
3. Update `src/agent_client.py`
4. Test basic conversation flow

### Day 2: CLI Startup & Initial Testing
1. Modify CLI to trigger introduction
2. Test with moderate collection
3. Observe agent behavior
4. Refine system prompt based on observations

### Day 3: Refinement
1. Test all collection sizes
2. Test follow-up questions
3. Adjust prompt for edge cases
4. Document final behavior

## Success Criteria

The implementation is successful when:

✅ Agent introduces itself without user prompt
✅ Agent asks for screenshot directory
✅ Agent adapts approach to collection size
✅ Agent samples files strategically (for moderate collections)
✅ Agent extracts specific content details (dates, amounts, errors)
✅ Agent suggests categories based on actual content
✅ Agent offers three naming strategies
✅ Agent shows real-time progress with MCP tool annotations
✅ Agent provides intelligent summary with content understanding
✅ Agent handles follow-up questions with context
✅ Conversation feels natural and helpful, not scripted
✅ MCP architecture is visible but not overwhelming

## Risk Mitigation

**Risk 1: Agent ignores workflow steps**
- Mitigation: Explicit numbered steps in system prompt
- Fallback: Add more directive language like "ALWAYS do X before Y"

**Risk 2: Agent too verbose or too terse**
- Mitigation: Test with different collection sizes and adjust prompt
- Fallback: Add explicit verbosity guidelines per scenario

**Risk 3: Agent doesn't extract specific details**
- Mitigation: Provide examples in system prompt of what to extract
- Fallback: Add more detailed content extraction guidelines

**Risk 4: Agent doesn't maintain context**
- Mitigation: Agent Framework's thread state should handle this
- Fallback: Explicitly remind agent to remember categories and strategy chosen

## Files to Modify

1. **src/agent_client.py** (Lines ~170-230)
   - Replace system prompt with conversational version
   - Main implementation effort

2. **src/cli_interface.py** (Lines ~350-400)
   - Add automatic introduction trigger
   - Minor changes

3. **config/system_prompts.yaml** (If we extract to config)
   - Optional: Move system prompt to config file
   - Better maintainability

## Next Steps

1. Review current system prompt
2. Draft new conversational system prompt with workflow steps
3. Update agent_client.py with new prompt
4. Test with real screenshot collection
5. Iterate based on behavior
6. Document final conversational patterns

## Notes

- The beauty of this approach is that **most changes are in the system prompt**
- GPT-4o is smart enough to do strategic sampling, content extraction, and pattern recognition
- MCP tools provide the "hands" - the agent provides the "brain"
- Agent Framework's thread state maintains context automatically
- We're leveraging AI intelligence, not hard-coding workflows
