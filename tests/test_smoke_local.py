"""Smoke tests for local mode - assumes environment is set up correctly.

These tests are designed to fail loudly if the local environment isn't configured.
Unlike integration tests that skip gracefully, smoke tests expect:
- AI Foundry CLI installed
- Phi-4 model downloaded
- Inference server running (foundry run phi-4)

Run these tests to verify your local setup works end-to-end.
Skip with: pytest -m "not smoke"
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_framework._types import ChatMessage, Role
from phi3_chat_client import LocalFoundryChatClient


@pytest.mark.smoke
class TestLocalModeSmoke:
    """Smoke tests that FAIL if local environment isn't configured correctly."""

    @pytest.mark.asyncio
    async def test_local_server_is_running(self):
        """SMOKE TEST: Verify AI Foundry server is running.

        This test will FAIL (not skip) if the server is not running.
        Expected setup:
        - AI Foundry CLI installed: brew install azure/ai-foundry/foundry
        - Phi-4 downloaded: foundry model get phi-4
        - Server running: foundry run phi-4
        """
        client = LocalFoundryChatClient()

        # This should succeed, not skip
        assert client._check_server_connection(), (
            "AI Foundry server is not running!\n"
            "Start with: foundry run phi-4\n"
            "Or skip smoke tests with: pytest -m 'not smoke'"
        )

    @pytest.mark.asyncio
    async def test_simple_chat_completion(self):
        """SMOKE TEST: Verify simple chat completion works end-to-end.

        This test will FAIL if:
        - Server isn't running
        - Message conversion is broken
        - Response handling is broken
        """
        client = LocalFoundryChatClient()

        # Verify server is running first
        assert client._check_server_connection(), (
            "AI Foundry server is not running! Start with: foundry run phi-4"
        )

        # Simple math query
        response = await client.get_response("What is 5 + 5?")

        # Verify response structure
        assert response is not None, "Got None response"
        assert hasattr(response, 'text'), "ChatResponse missing .text attribute"
        assert response.text is not None, "Response text is None"
        assert len(response.text) > 0, "Response text is empty"

        # Verify response content makes sense
        assert "10" in response.text.lower() or "ten" in response.text.lower(), (
            f"Expected '10' or 'ten' in response, got: {response.text[:100]}"
        )

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self):
        """SMOKE TEST: Verify multi-turn conversation with context works.

        This tests that the message conversion handles all role types correctly.
        """
        client = LocalFoundryChatClient()

        assert client._check_server_connection(), (
            "AI Foundry server is not running! Start with: foundry run phi-4"
        )

        # Multi-turn conversation
        messages = [
            ChatMessage(role=Role.SYSTEM, text="You are a helpful assistant."),
            ChatMessage(role=Role.USER, text="My favorite color is blue."),
            ChatMessage(role=Role.ASSISTANT, text="That's nice! Blue is a great color."),
            ChatMessage(role=Role.USER, text="What is my favorite color?"),
        ]

        response = await client.get_response(messages)

        # Verify response
        assert response is not None, "Got None response"
        assert response.text is not None, "Response text is None"
        assert len(response.text) > 0, "Response text is empty"

        # Verify it remembered the context
        assert "blue" in response.text.lower(), (
            f"Expected 'blue' in response (context retention), got: {response.text[:100]}"
        )

    @pytest.mark.asyncio
    async def test_role_enum_conversion(self):
        """SMOKE TEST: Verify Role enum conversion doesn't break.

        This would catch the 'Role' object has no attribute 'lower' bug.
        """
        client = LocalFoundryChatClient()

        # Test all role types
        for role in [Role.USER, Role.SYSTEM, Role.ASSISTANT]:
            msg = ChatMessage(role=role, text="Test message")

            # This should not raise AttributeError
            result = client._convert_to_inference_messages(msg)

            assert len(result) == 1, f"Expected 1 message, got {len(result)}"
            assert result[0].content == "Test message", f"Content mismatch for {role}"


if __name__ == "__main__":
    # Run only smoke tests
    pytest.main([__file__, "-v", "-m", "smoke"])
