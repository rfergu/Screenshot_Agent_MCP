"""MCP tools for screenshot organization.

Low-level file operation tools for MCP server subprocess.

Architecture: These tools are provided by the MCP SERVER in the unified architecture:
  Agent Framework (Brain) → makes decisions
  MCP Client Wrapper (embedded) → protocol bridge
  MCP Server (subprocess) → provides THESE TOOLS
  File System → accessed via these tools

Tool Philosophy - "Dumb Tools, Smart Agent":
- Tools return FACTS and DATA (not decisions)
- Tools execute FILE OPERATIONS (no intelligence)
- Agent Framework (GPT-4) makes INTELLIGENT DECISIONS:
  * Categorization (based on content understanding)
  * Descriptive filenames (creative, context-aware)
  * Workflow orchestration (multi-step operations)

This demonstrates separation of concerns in Agent Framework WITH MCP Client Integration.
"""

from .list_screenshots import list_screenshots
from .analyze_screenshot import analyze_screenshot
from .get_categories import get_categories
from .categorize_screenshot import categorize_screenshot
from .create_category_folder import create_category_folder
from .move_screenshot import move_screenshot
from .generate_filename import generate_filename

__all__ = [
    "list_screenshots",
    "analyze_screenshot",
    "get_categories",
    "categorize_screenshot",
    "create_category_folder",
    "move_screenshot",
    "generate_filename",
]
