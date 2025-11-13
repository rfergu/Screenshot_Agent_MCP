"""MCP Server - The "Hands" in Agent Framework WITH MCP Client Integration.

Architecture: This is the MCP SERVER (subprocess) in the unified architecture

This server runs as a SUBPROCESS accessed by the embedded MCP client in Agent Framework.
It provides "dumb" file operation tools that return facts, not decisions.

Unified Architecture:
  Agent Framework (Brain - GPT-4)
    ↓ embeds
  MCP Client Wrapper (embedded)
    ↓ stdio transport
  MCP Server (THIS MODULE - subprocess)
    ↓ mediates
  File System

The MCP server provides low-level tools that:
- Return facts and data (not decisions)
- Execute file operations
- Handle protocol communication
- Mediate ALL file system access

The Agent Framework (GPT-4) provides the intelligence:
- Decides categories
- Creates descriptive filenames
- Orchestrates workflow
- Understands content and intent

This demonstrates separation of concerns: Brain (Agent) vs Hands (MCP Server).
"""

import asyncio
import json
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from screenshot_mcp import tools as mcp_tools
from utils.config import load_config
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class ScreenshotMCPServer:
    """MCP server subprocess providing low-level file operation tools.

    This server runs as a subprocess, accessed via stdio transport by the
    embedded MCP client in Agent Framework.

    Role in Architecture:
    - Provides 7 low-level file operation tools
    - Returns facts and data (not intelligent decisions)
    - Mediates ALL file system access
    - Communicates via MCP protocol (stdio)

    The Agent Framework (Brain) makes decisions; this server (Hands) executes them.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize MCP server.

        Args:
            config: Optional configuration dictionary. If None, loads from default config.
        """
        self.config = config or load_config()
        self.server = Server("screenshot-organizer-mcp")

        logger.info("ScreenshotMCPServer initialized")

    def register_tools(self):
        """Register all low-level MCP tools with their schemas."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available MCP tools."""
            return [
                Tool(
                    name="list_screenshots",
                    description="List screenshot files in a directory. Returns raw file information without analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "Absolute path to directory to scan for screenshots"
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Scan subdirectories recursively",
                                "default": False
                            },
                            "max_files": {
                                "type": "integer",
                                "description": "Maximum number of files to return",
                                "minimum": 1
                            }
                        },
                        "required": ["directory"]
                    }
                ),
                Tool(
                    name="analyze_screenshot",
                    description="Analyze screenshot content using OCR or vision model. Returns RAW analysis data (text, description) without making categorization decisions.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Absolute path to screenshot file to analyze"
                            },
                            "force_vision": {
                                "type": "boolean",
                                "description": "Skip OCR and use vision model directly",
                                "default": False
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="get_categories",
                    description="Get list of available screenshot categories with descriptions and keywords.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="categorize_screenshot",
                    description="Suggest category based on text content using keyword matching. This is a simple fallback - the Agent should make the final decision using its intelligence.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text content to categorize"
                            },
                            "available_categories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of valid category names (optional)"
                            }
                        },
                        "required": ["text"]
                    }
                ),
                Tool(
                    name="create_category_folder",
                    description="Create a category folder for organizing screenshots. Simple folder creation operation.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Category name (e.g., 'code', 'errors')"
                            },
                            "base_dir": {
                                "type": "string",
                                "description": "Base directory for organization (uses config default if not provided)"
                            }
                        },
                        "required": ["category"]
                    }
                ),
                Tool(
                    name="move_screenshot",
                    description="Move (or copy) a screenshot file to a destination folder. Simple file operation - the Agent decides destination and filename.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source_path": {
                                "type": "string",
                                "description": "Absolute path to source file"
                            },
                            "dest_folder": {
                                "type": "string",
                                "description": "Absolute path to destination folder"
                            },
                            "new_filename": {
                                "type": "string",
                                "description": "New filename (without extension). If None, keeps original name"
                            },
                            "keep_original": {
                                "type": "boolean",
                                "description": "If True, copy instead of move",
                                "default": True
                            }
                        },
                        "required": ["source_path", "dest_folder"]
                    }
                ),
                Tool(
                    name="generate_filename",
                    description="Generate a descriptive filename for a screenshot. Simple utility - the Agent can use its own intelligence for better names.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "original_filename": {
                                "type": "string",
                                "description": "Original filename"
                            },
                            "category": {
                                "type": "string",
                                "description": "Category name"
                            },
                            "text": {
                                "type": "string",
                                "description": "Optional extracted text for generating descriptive name"
                            },
                            "description": {
                                "type": "string",
                                "description": "Optional description for generating descriptive name"
                            }
                        },
                        "required": ["original_filename", "category"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls from MCP clients.

            Args:
                name: Name of the tool to call.
                arguments: Tool arguments.

            Returns:
                List of TextContent responses.
            """
            logger.debug(f"Tool called: {name} with arguments: {arguments}")

            try:
                result = None

                if name == "list_screenshots":
                    result = mcp_tools.list_screenshots(
                        directory=arguments["directory"],
                        recursive=arguments.get("recursive", False),
                        max_files=arguments.get("max_files")
                    )
                elif name == "analyze_screenshot":
                    result = mcp_tools.analyze_screenshot(
                        file_path=arguments["file_path"],
                        force_vision=arguments.get("force_vision", False)
                    )
                elif name == "get_categories":
                    result = mcp_tools.get_categories()
                elif name == "categorize_screenshot":
                    result = mcp_tools.categorize_screenshot(
                        text=arguments["text"],
                        available_categories=arguments.get("available_categories")
                    )
                elif name == "create_category_folder":
                    result = mcp_tools.create_category_folder(
                        category=arguments["category"],
                        base_dir=arguments.get("base_dir")
                    )
                elif name == "move_screenshot":
                    result = mcp_tools.move_screenshot(
                        source_path=arguments["source_path"],
                        dest_folder=arguments["dest_folder"],
                        new_filename=arguments.get("new_filename"),
                        keep_original=arguments.get("keep_original", True)
                    )
                elif name == "generate_filename":
                    result = mcp_tools.generate_filename(
                        original_filename=arguments["original_filename"],
                        category=arguments["category"],
                        text=arguments.get("text"),
                        description=arguments.get("description")
                    )
                else:
                    raise ValueError(f"Unknown tool: {name}")

                # Return result as JSON text content
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            except FileNotFoundError as e:
                logger.error(f"File not found error in {name}: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"File not found: {str(e)}"})
                )]
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Tool execution failed: {str(e)}"})
                )]

        logger.info("All MCP tools registered")

    async def run(self):
        """Run the MCP server using stdio transport."""
        logger.info("Starting MCP server with stdio transport")

        # Register tools
        self.register_tools()

        # Run server with stdio
        async with stdio_server() as (read_stream, write_stream):
            logger.info("MCP server running on stdio")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point for MCP server."""
    # Setup logging
    setup_logging()
    logger.info("Screenshot MCP Server starting...")

    # Load configuration
    config = load_config()
    logger.info(f"Configuration loaded: {config.get('organization', {}).get('base_folder')}")

    # Create and run server
    server = ScreenshotMCPServer(config)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
