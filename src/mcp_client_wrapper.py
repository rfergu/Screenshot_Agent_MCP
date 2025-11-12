"""MCP Client Wrapper - Embedded component for Agent Framework WITH MCP Client Integration.

Architecture: This is the EMBEDDED MCP Client inside Agent Framework

This module provides the bridge between Microsoft Agent Framework and MCP server.
It is embedded INSIDE AgentClient, demonstrating the unified architecture:

  Agent Framework (Brain)
    ↓ embeds
  MCPClientWrapper (THIS MODULE - embedded MCP client)
    ↓ manages subprocess + stdio transport
  MCP Server (subprocess)
    ↓ provides
  Low-level file operation tools

The wrapper:
1. Starts MCP server as a subprocess
2. Creates MCP client session via stdio transport
3. Exposes tools as synchronous functions for Agent Framework
4. Handles async/sync conversion
5. Manages server lifecycle (start, stop, cleanup)

This demonstrates Model Context Protocol (MCP) integration with Agent Framework.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from utils.logger import get_logger

logger = get_logger(__name__)


class MCPClientWrapper:
    """Embedded MCP client for Agent Framework WITH MCP Client Integration.

    This class is EMBEDDED inside AgentClient and serves as the bridge between
    Agent Framework (Brain) and MCP Server (Hands).

    Responsibilities:
    - Manages MCP server subprocess lifecycle
    - Provides synchronous tool wrappers for Agent Framework
    - Handles stdio transport communication with MCP server
    - Converts async MCP protocol to sync function calls for Agent

    In the unified architecture, this is the "MCP Client Wrapper" layer that
    sits between the Agent Framework and the MCP server subprocess.
    """

    def __init__(self):
        """Initialize MCP client wrapper."""
        self.session: Optional[ClientSession] = None
        self.read_stream = None
        self.write_stream = None
        self._server_task = None
        self._event_loop = None
        logger.info("MCPClientWrapper initialized")

    async def start(self):
        """Start MCP server and create client session."""
        logger.info("Starting MCP server subprocess...")

        # Get project root
        project_root = Path(__file__).parent.parent

        # Configure MCP server parameters
        # Pass current environment to subprocess so it has access to Azure credentials
        server_params = StdioServerParameters(
            command=sys.executable,  # Use same Python interpreter
            args=["-m", "src", "server"],
            cwd=str(project_root),
            env=dict(os.environ)  # Pass parent's environment variables
        )

        # Start MCP server and create session
        try:
            # Create stdio client
            self._stdio_client = stdio_client(server_params)
            self.read_stream, self.write_stream = await self._stdio_client.__aenter__()

            # Create session
            self.session = ClientSession(self.read_stream, self.write_stream)
            await self.session.__aenter__()

            # Initialize session
            await self.session.initialize()

            logger.info("MCP client session started and initialized")

        except Exception as e:
            logger.error(f"Failed to start MCP client: {e}")
            raise

    async def stop(self):
        """Stop MCP server and close client session."""
        logger.info("Stopping MCP client session...")

        try:
            if self.session:
                await self.session.__aexit__(None, None, None)

            if self._stdio_client:
                await self._stdio_client.__aexit__(None, None, None)

            logger.info("MCP client session stopped")

        except Exception as e:
            logger.error(f"Error stopping MCP client: {e}")

    async def call_tool_async(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool asynchronously.

        Args:
            name: Tool name
            arguments: Tool arguments dictionary

        Returns:
            Tool result as dictionary

        Raises:
            RuntimeError: If session not started
            ValueError: If tool call fails
        """
        if not self.session:
            raise RuntimeError("MCP session not started. Call start() first.")

        logger.debug(f"Calling MCP tool: {name} with args: {arguments}")

        try:
            result = await self.session.call_tool(name, arguments)

            # Parse result from TextContent
            if hasattr(result, 'content') and result.content:
                content_text = result.content[0].text
                logger.debug(f"Tool {name} raw content: {repr(content_text)}")

                # Check if content is empty
                if not content_text or not content_text.strip():
                    logger.error(f"Tool {name} returned empty content")
                    return {"error": "Tool returned empty response", "success": False}

                try:
                    data = json.loads(content_text)
                    logger.debug(f"Tool {name} returned: {data}")
                    return data
                except json.JSONDecodeError as json_err:
                    logger.error(f"JSON decode error for tool {name}: {json_err}")
                    logger.error(f"Raw content was: {repr(content_text)}")
                    return {"error": f"Invalid JSON response: {str(json_err)}", "success": False}
            else:
                logger.error(f"Tool {name} returned unexpected format: {result}")
                return {"error": "Unexpected result format", "success": False}

        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}", exc_info=True)
            return {"error": str(e), "success": False}

    # ========================================================================
    # SYNCHRONOUS TOOL WRAPPERS (for Agent Framework)
    # ========================================================================

    def list_screenshots(
        self,
        directory: str,
        recursive: bool = False,
        max_files: Optional[int] = None
    ) -> Dict[str, Any]:
        """List screenshot files in a directory.

        Args:
            directory: Absolute path to directory to scan
            recursive: Whether to scan subdirectories
            max_files: Maximum number of files to return

        Returns:
            Dictionary with files list and metadata
        """
        return self._run_async(
            self.call_tool_async(
                "list_screenshots",
                {
                    "directory": directory,
                    "recursive": recursive,
                    "max_files": max_files
                }
            )
        )

    def analyze_screenshot(
        self,
        file_path: str,
        force_vision: bool = False
    ) -> Dict[str, Any]:
        """Analyze screenshot content using OCR or vision model.

        Returns raw analysis data without categorization decisions.

        Args:
            file_path: Absolute path to screenshot file
            force_vision: Skip OCR and use vision model directly

        Returns:
            Dictionary with extracted_text, vision_description, etc.
        """
        return self._run_async(
            self.call_tool_async(
                "analyze_screenshot",
                {
                    "file_path": file_path,
                    "force_vision": force_vision
                }
            )
        )

    def get_categories(self) -> Dict[str, Any]:
        """Get list of available screenshot categories.

        Returns:
            Dictionary with categories list and metadata
        """
        return self._run_async(
            self.call_tool_async("get_categories", {})
        )

    def categorize_screenshot(
        self,
        text: str,
        available_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Suggest category based on text using keyword matching (fallback).

        Args:
            text: Text content to categorize
            available_categories: List of valid category names

        Returns:
            Dictionary with suggested_category, confidence, matched_keywords
        """
        return self._run_async(
            self.call_tool_async(
                "categorize_screenshot",
                {
                    "text": text,
                    "available_categories": available_categories
                }
            )
        )

    def create_category_folder(
        self,
        category: str,
        base_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a category folder for organizing screenshots.

        Args:
            category: Category name (e.g., 'code', 'errors')
            base_dir: Base directory for organization (optional)

        Returns:
            Dictionary with folder_path, created, success
        """
        return self._run_async(
            self.call_tool_async(
                "create_category_folder",
                {
                    "category": category,
                    "base_dir": base_dir
                }
            )
        )

    def move_screenshot(
        self,
        source_path: str,
        dest_folder: str,
        new_filename: Optional[str] = None,
        keep_original: bool = True
    ) -> Dict[str, Any]:
        """Move (or copy) a screenshot file to a destination folder.

        Args:
            source_path: Absolute path to source file
            dest_folder: Absolute path to destination folder
            new_filename: New filename (without extension)
            keep_original: If True, copy instead of move

        Returns:
            Dictionary with original_path, new_path, operation, success
        """
        return self._run_async(
            self.call_tool_async(
                "move_screenshot",
                {
                    "source_path": source_path,
                    "dest_folder": dest_folder,
                    "new_filename": new_filename,
                    "keep_original": keep_original
                }
            )
        )

    def generate_filename(
        self,
        original_filename: str,
        category: str,
        text: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a descriptive filename for a screenshot (simple utility).

        Args:
            original_filename: Original filename
            category: Category name
            text: Optional extracted text
            description: Optional description

        Returns:
            Dictionary with suggested_filename, extension, timestamp
        """
        return self._run_async(
            self.call_tool_async(
                "generate_filename",
                {
                    "original_filename": original_filename,
                    "category": category,
                    "text": text,
                    "description": description
                }
            )
        )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _run_async(self, coro):
        """Run an async coroutine and return result synchronously.

        This allows Agent Framework (which may be sync) to call async MCP tools.

        Args:
            coro: Async coroutine to run

        Returns:
            Result from coroutine
        """
        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop running, create new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # If we're already in an async context, use the existing loop
        if loop.is_running():
            # Create a task and return a future
            # This is tricky - we can't block in an async context
            # For now, raise an error - caller should use async methods
            raise RuntimeError(
                "Cannot use synchronous tool methods from async context. "
                "Use call_tool_async() instead."
            )
        else:
            # We're in a sync context, run the coroutine
            return loop.run_until_complete(coro)


# ============================================================================
# GLOBAL MCP CLIENT INSTANCE
# ============================================================================

_mcp_client: Optional[MCPClientWrapper] = None


async def get_mcp_client() -> MCPClientWrapper:
    """Get or create global MCP client instance.

    Returns:
        MCPClientWrapper instance

    Raises:
        RuntimeError: If client fails to start
    """
    global _mcp_client

    if _mcp_client is None:
        _mcp_client = MCPClientWrapper()
        await _mcp_client.start()
        logger.info("Global MCP client created and started")

    return _mcp_client


async def stop_mcp_client():
    """Stop global MCP client if running."""
    global _mcp_client

    if _mcp_client:
        await _mcp_client.stop()
        _mcp_client = None
        logger.info("Global MCP client stopped")


# ============================================================================
# AGENT FRAMEWORK TOOL WRAPPERS
# ============================================================================

def get_agent_framework_tools(mcp_client: MCPClientWrapper) -> List[Dict[str, Any]]:
    """Get MCP tools formatted for Agent Framework.

    Args:
        mcp_client: MCPClientWrapper instance

    Returns:
        List of tool dictionaries for Agent Framework
    """
    from typing import Annotated
    from pydantic import Field

    tools = []

    # Tool 1: list_screenshots
    async def list_screenshots_tool(
        directory: Annotated[str, Field(description="Absolute path to directory to scan")],
        recursive: Annotated[bool, Field(description="Scan subdirectories")] = False,
        max_files: Annotated[Optional[int], Field(description="Max files to return")] = None
    ) -> Dict[str, Any]:
        """List screenshot files in a directory."""
        args = {"directory": directory, "recursive": recursive}
        # Only include max_files if explicitly set (MCP SDK rejects None for optional int)
        if max_files is not None:
            args["max_files"] = max_files
        return await mcp_client.call_tool_async("list_screenshots", args)

    tools.append({
        "function": list_screenshots_tool,
        "name": "list_screenshots",
        "description": "List screenshot files in a directory without analyzing them"
    })

    # Tool 2: analyze_screenshot
    async def analyze_screenshot_tool(
        file_path: Annotated[str, Field(description="Absolute path to screenshot file")],
        force_vision: Annotated[bool, Field(description="Use vision model directly")] = False
    ) -> Dict[str, Any]:
        """Analyze screenshot content using OCR or vision model."""
        return await mcp_client.call_tool_async("analyze_screenshot", {
            "file_path": file_path,
            "force_vision": force_vision
        })

    tools.append({
        "function": analyze_screenshot_tool,
        "name": "analyze_screenshot",
        "description": "Extract text/content from screenshot without categorizing"
    })

    # Tool 3: get_categories
    async def get_categories_tool() -> Dict[str, Any]:
        """Get list of available screenshot categories."""
        return await mcp_client.call_tool_async("get_categories", {})

    tools.append({
        "function": get_categories_tool,
        "name": "get_categories",
        "description": "Get available categories with descriptions and keywords"
    })

    # Tool 4: create_category_folder
    async def create_category_folder_tool(
        category: Annotated[str, Field(description="Category name")],
        base_dir: Annotated[Optional[str], Field(description="Base directory")] = None
    ) -> Dict[str, Any]:
        """Create a category folder for organizing screenshots."""
        args = {"category": category}
        # Only include base_dir if explicitly set
        if base_dir is not None:
            args["base_dir"] = base_dir
        return await mcp_client.call_tool_async("create_category_folder", args)

    tools.append({
        "function": create_category_folder_tool,
        "name": "create_category_folder",
        "description": "Create a folder for a screenshot category"
    })

    # Tool 5: move_screenshot
    async def move_screenshot_tool(
        source_path: Annotated[str, Field(description="Source file path")],
        dest_folder: Annotated[str, Field(description="Destination folder path")],
        new_filename: Annotated[Optional[str], Field(description="New filename without extension")] = None,
        keep_original: Annotated[bool, Field(description="Copy instead of move")] = True
    ) -> Dict[str, Any]:
        """Move or copy a screenshot file to a destination folder."""
        args = {
            "source_path": source_path,
            "dest_folder": dest_folder,
            "keep_original": keep_original
        }
        # Only include new_filename if explicitly set
        if new_filename is not None:
            args["new_filename"] = new_filename
        return await mcp_client.call_tool_async("move_screenshot", args)

    tools.append({
        "function": move_screenshot_tool,
        "name": "move_screenshot",
        "description": "Move or copy a screenshot file to organize it"
    })

    logger.info(f"Created {len(tools)} Agent Framework tool wrappers")
    return tools
