"""Model Context Protocol (MCP) components.

This package contains MCP integration for screenshot organization.

Architecture:
  Agent Framework (Brain) → src/agent/
    ↓ embeds
  MCP Client Wrapper → src/mcp/client_wrapper.py
    ↓ stdio transport
  MCP Server → src/mcp/server.py
    ↓ provides
  MCP Tools → src/mcp/tools/

Components:
- client_wrapper: MCPClientWrapper for managing MCP server subprocess
- server: MCP server providing file operation tools via stdio
- tools: Individual MCP tool implementations

Note: Import components directly from submodules to avoid circular imports
with the installed 'mcp' SDK package.
"""

# Do not import here to avoid circular import with installed 'mcp' package
# Import directly from submodules instead:
#   from mcp.client_wrapper import MCPClientWrapper
#   from mcp import tools
