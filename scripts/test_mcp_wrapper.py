#!/usr/bin/env python3
"""Test script for MCP client wrapper.

This script tests the MCP client wrapper to ensure it can:
1. Start MCP server as subprocess
2. Call tools via MCP protocol
3. Return results correctly
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_client_wrapper import MCPClientWrapper


async def test_wrapper():
    """Test MCP client wrapper functionality."""

    print("\n" + "="*70)
    print("MCP CLIENT WRAPPER TEST")
    print("="*70)

    # Create wrapper
    print("\n[1] Creating MCP client wrapper...")
    wrapper = MCPClientWrapper()
    print("✓ Wrapper created")

    try:
        # Start MCP session
        print("\n[2] Starting MCP server and session...")
        await wrapper.start()
        print("✓ MCP session started")

        # Test get_categories
        print("\n[3] Testing get_categories tool...")
        categories = await wrapper.call_tool_async("get_categories", {})
        print(f"✓ Found {len(categories.get('categories', []))} categories:")
        for cat in categories.get('categories', [])[:3]:
            print(f"   • {cat['name']}: {cat['description'][:50]}...")

        # Test list_screenshots
        print("\n[4] Testing list_screenshots tool...")
        test_dir = str(Path(__file__).parent.parent / "test_screenshots")
        files = await wrapper.call_tool_async(
            "list_screenshots",
            {"directory": test_dir, "recursive": False}
        )
        print(f"✓ Found {files.get('total_count', 0)} screenshots")
        if files.get('files'):
            for file in files['files'][:2]:
                print(f"   • {file['filename']} ({file['size_bytes']} bytes)")

        # Test create_category_folder
        print("\n[5] Testing create_category_folder tool...")
        result = await wrapper.call_tool_async(
            "create_category_folder",
            {"category": "test_category"}
        )
        print(f"✓ Folder: {result.get('folder_path')}")
        print(f"  Created: {result.get('created')}")

        print("\n" + "="*70)
        print("MCP CLIENT WRAPPER TEST COMPLETE ✓")
        print("="*70)
        print("\nAll MCP client wrapper functions working correctly!")
        print("Ready for Agent Framework integration.\n")

    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Stop MCP session
        print("\n[6] Stopping MCP session...")
        await wrapper.stop()
        print("✓ MCP session stopped")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_wrapper())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
