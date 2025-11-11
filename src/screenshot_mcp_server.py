"""MCP server for screenshot organization using local AI processing."""

import asyncio
import json
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_tools import MCPToolHandlers
from utils.config import load_config
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class ScreenshotMCPServer:
    """MCP server providing screenshot analysis and organization tools."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize MCP server with tool handlers.

        Args:
            config: Optional configuration dictionary. If None, loads from default config.
        """
        self.config = config or load_config()
        self.server = Server("screenshot-organizer-mcp")
        self.handlers = MCPToolHandlers(self.config)

        logger.info("ScreenshotMCPServer initialized")

    def register_tools(self):
        """Register all MCP tools with their schemas."""

        # Tool 1: analyze_screenshot
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available MCP tools."""
            return [
                Tool(
                    name="analyze_screenshot",
                    description="Analyze a screenshot using OCR or vision model to determine its category and suggest a filename",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Absolute path to the screenshot file"
                            },
                            "force_vision": {
                                "type": "boolean",
                                "description": "Force use of vision model even if OCR would be sufficient",
                                "default": False
                            }
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="batch_process",
                    description="Process all screenshots in a folder, analyzing and categorizing each one",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "folder": {
                                "type": "string",
                                "description": "Path to the folder containing screenshots"
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Process subfolders recursively",
                                "default": False
                            },
                            "max_files": {
                                "type": "integer",
                                "description": "Maximum number of files to process",
                                "minimum": 1,
                                "maximum": 1000
                            },
                            "organize": {
                                "type": "boolean",
                                "description": "Automatically organize files after analysis",
                                "default": False
                            }
                        },
                        "required": ["folder"]
                    }
                ),
                Tool(
                    name="organize_file",
                    description="Move and rename a screenshot file based on its category",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source_path": {
                                "type": "string",
                                "description": "Current path of the file to organize"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["code", "errors", "documentation", "design", 
                                       "communication", "memes", "other"],
                                "description": "Category for organization"
                            },
                            "new_filename": {
                                "type": "string",
                                "description": "New filename for the file (without extension)"
                            },
                            "archive_original": {
                                "type": "boolean",
                                "description": "Keep a copy of the original file in archive",
                                "default": False
                            },
                            "base_path": {
                                "type": "string",
                                "description": "Base path for organized files"
                            }
                        },
                        "required": ["source_path", "category", "new_filename"]
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
            logger.info(f"Tool called: {name} with arguments: {arguments}")

            try:
                if name == "analyze_screenshot":
                    result = self.handlers.analyze_screenshot(
                        path=arguments["path"],
                        force_vision=arguments.get("force_vision", False)
                    )
                elif name == "batch_process":
                    result = self.handlers.batch_process(
                        folder=arguments["folder"],
                        recursive=arguments.get("recursive", False),
                        max_files=arguments.get("max_files"),
                        organize=arguments.get("organize", False)
                    )
                elif name == "organize_file":
                    result = self.handlers.organize_file(
                        source_path=arguments["source_path"],
                        category=arguments["category"],
                        new_filename=arguments["new_filename"],
                        archive_original=arguments.get("archive_original", False),
                        base_path=arguments.get("base_path")
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
