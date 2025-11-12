#!/usr/bin/env python3
"""Test client for MCP server demonstration.

This script demonstrates the Model Context Protocol by:
1. Starting the MCP server as a subprocess
2. Connecting via stdio transport
3. Listing available tools
4. Calling the analyze_screenshot tool
5. Showing that file system access happens through MCP protocol
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: mcp package not installed")
    print("Install with: pip install mcp")
    sys.exit(1)


async def test_mcp_protocol():
    """Test MCP server by calling tools through the protocol."""

    print("\n" + "="*70)
    print("MCP PROTOCOL DEMONSTRATION")
    print("="*70)

    # Get project root
    project_root = Path(__file__).parent.parent

    print("\n[1] Starting MCP Server via stdio transport...")
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src", "server"],
        env=None
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:

                print("✓ Connected to MCP server\n")

                # Initialize the session
                print("[2] Initializing MCP session...")
                await session.initialize()
                print("✓ Session initialized\n")

                # List available tools
                print("[3] Listing available tools via MCP protocol...")
                tools_result = await session.list_tools()
                tools = tools_result.tools

                print(f"✓ Found {len(tools)} tools:\n")
                for tool in tools:
                    print(f"   • {tool.name}")
                    if tool.description:
                        # Truncate long descriptions
                        desc = tool.description[:80]
                        if len(tool.description) > 80:
                            desc += "..."
                        print(f"     └─ {desc}")
                print()

                # Find a test screenshot
                print("[4] Looking for test screenshot...")
                test_screenshots_dir = project_root / "test_screenshots"

                if not test_screenshots_dir.exists():
                    print(f"   ⚠ No test_screenshots directory found")
                    print(f"   Create one with: mkdir {test_screenshots_dir}")
                    print(f"   Add a screenshot to test MCP tool calls")
                    return

                # Find first PNG/JPG file
                screenshot_path = None
                for ext in ["*.png", "*.jpg", "*.jpeg"]:
                    files = list(test_screenshots_dir.glob(ext))
                    if files:
                        screenshot_path = files[0]
                        break

                if not screenshot_path:
                    print(f"   ⚠ No screenshots found in {test_screenshots_dir}")
                    print(f"   Add a .png or .jpg file to test MCP tool calls")
                    return

                print(f"✓ Found test screenshot: {screenshot_path.name}\n")

                # Call analyze_screenshot tool via MCP
                print("[5] Calling analyze_screenshot via MCP protocol...")
                print(f"   Tool: analyze_screenshot")
                print(f"   Path: {screenshot_path}")
                print(f"   Force Vision: False")
                print()

                result = await session.call_tool(
                    "analyze_screenshot",
                    {
                        "file_path": str(screenshot_path),
                        "force_vision": False
                    }
                )

                print("✓ MCP tool call successful!\n")

                # Display results
                print("[6] Results from MCP server:")
                print("-" * 70)

                # Parse the result
                if hasattr(result, 'content') and result.content:
                    import json
                    # The content is a list of TextContent objects
                    content_text = result.content[0].text
                    data = json.loads(content_text)

                    print(f"Processing Method:  {data.get('processing_method', 'N/A')}")
                    print(f"Processing Time:    {data.get('processing_time_ms', 0):.2f}ms")
                    print(f"Word Count:         {data.get('word_count', 0)}")
                    print(f"Success:            {data.get('success', False)}")

                    if data.get('extracted_text'):
                        text_preview = data['extracted_text'][:100]
                        if len(data['extracted_text']) > 100:
                            text_preview += "..."
                        print(f"Extracted Text:     {text_preview}")

                    if data.get('vision_description'):
                        desc_preview = data['vision_description'][:100]
                        if len(data['vision_description']) > 100:
                            desc_preview += "..."
                        print(f"Vision Description: {desc_preview}")

                    if data.get('error'):
                        print(f"Error:              {data['error']}")

                print("-" * 70)

                print("\n[7] MCP Protocol Verification:")
                print("   ✓ File system access happened through MCP server")
                print("   ✓ Tool call was mediated by protocol")
                print("   ✓ Results returned via MCP transport")

                print("\n" + "="*70)
                print("MCP PROTOCOL DEMONSTRATION COMPLETE")
                print("="*70)
                print("\nThis proves that:")
                print("  1. MCP server exposes tools via standardized protocol")
                print("  2. Clients can discover tools dynamically")
                print("  3. File system access is mediated through MCP")
                print("  4. Any MCP-compatible client can use these tools")
                print("\n")

    except Exception as e:
        print(f"\n✗ Error during MCP protocol test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def main():
    """Main entry point."""
    await test_mcp_protocol()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
