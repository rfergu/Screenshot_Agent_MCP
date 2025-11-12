"""Agent Framework client components.

This package contains the Agent Framework client implementation for screenshot organization.

Components:
- client: Main AgentClient class with embedded MCP client
- prompts: System prompts for remote (production) and local (testing) modes
- modes: Mode detection and chat client initialization logic
"""

from .client import AgentClient

__all__ = ["AgentClient"]
