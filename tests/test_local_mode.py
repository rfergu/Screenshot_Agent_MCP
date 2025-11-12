"""Tests for local mode chat client."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_framework._types import ChatMessage, Role
from azure.ai.inference.models import UserMessage, SystemMessage, AssistantMessage
from phi3_chat_client import LocalFoundryChatClient

# Test endpoint to use (avoids auto-detection in tests)
TEST_ENDPOINT = "http://127.0.0.1:5272/v1/chat/completions"


class TestMessageConversion:
    """Test message conversion for LocalFoundryChatClient."""

    def test_convert_string_message(self):
        """Test converting a simple string to inference format."""
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)
        result = client._convert_to_inference_messages("Hello world")

        assert len(result) == 1
        assert isinstance(result[0], UserMessage)
        assert result[0].content == "Hello world"

    def test_convert_chat_message_user(self):
        """Test converting ChatMessage with user role."""
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)
        msg = ChatMessage(role=Role.USER, text="What is 5+5?")

        result = client._convert_to_inference_messages(msg)

        assert len(result) == 1
        assert isinstance(result[0], UserMessage)
        assert result[0].content == "What is 5+5?"

    def test_convert_chat_message_system(self):
        """Test converting ChatMessage with system role."""
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)
        msg = ChatMessage(role=Role.SYSTEM, text="You are a helpful assistant.")

        result = client._convert_to_inference_messages(msg)

        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are a helpful assistant."

    def test_convert_chat_message_assistant(self):
        """Test converting ChatMessage with assistant role."""
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)
        msg = ChatMessage(role=Role.ASSISTANT, text="I can help you with that.")

        result = client._convert_to_inference_messages(msg)

        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)
        assert result[0].content == "I can help you with that."

    def test_convert_message_list(self):
        """Test converting a list of different message types."""
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)
        messages = [
            ChatMessage(role=Role.SYSTEM, text="You are helpful."),
            ChatMessage(role=Role.USER, text="What is 5+5?"),
            "Another question",
        ]

        result = client._convert_to_inference_messages(messages)

        assert len(result) == 3
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], UserMessage)
        assert isinstance(result[2], UserMessage)
        assert result[0].content == "You are helpful."
        assert result[1].content == "What is 5+5?"
        assert result[2].content == "Another question"

    def test_convert_dict_messages(self):
        """Test converting dict messages (legacy format)."""
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]

        result = client._convert_to_inference_messages(messages)

        assert len(result) == 2
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], UserMessage)

    def test_convert_empty_text(self):
        """Test handling of empty text."""
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)
        msg = ChatMessage(role=Role.USER, text=None)

        result = client._convert_to_inference_messages(msg)

        assert len(result) == 1
        assert isinstance(result[0], UserMessage)
        assert result[0].content == ""


class TestErrorHandling:
    """Test error handling when server is not running."""

    @pytest.mark.asyncio
    async def test_server_not_running_returns_helpful_error(self):
        """Test that a helpful error message is returned when server is down.

        This test should PASS even when server is not running - it verifies
        the error handling works correctly.
        """
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)

        # Only run this test if server is NOT running
        if client._check_server_connection():
            pytest.skip("AI Foundry server IS running - this test is for when it's down")

        # Try to get a response when server is down
        response = await client.get_response("What is 5 + 5?")

        # Should get a ChatResponse with helpful error message, not an exception
        assert response is not None
        assert response.text is not None
        assert "AI Foundry server" in response.text
        assert "foundry service start" in response.text or "foundry run phi-4" in response.text
        assert "foundry model load phi-4" in response.text or "foundry run phi-4" in response.text
        assert "--mode remote" in response.text


@pytest.mark.integration
class TestLocalModeIntegration:
    """Integration tests for local mode (requires AI Foundry server running)."""

    @pytest.mark.asyncio
    async def test_simple_chat_query(self):
        """Test a simple chat query against local server.

        Requires: foundry run phi-4
        This test will be skipped if server is not running.
        """
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)

        # Check if server is accessible
        if not client._check_server_connection():
            pytest.skip("AI Foundry server not running (foundry run phi-4)")

        # Simple math query
        response = await client.get_response("What is 5 + 5?")

        assert response is not None
        assert response.text is not None
        assert len(response.text) > 0
        assert "10" in response.text.lower()

    @pytest.mark.asyncio
    async def test_conversation_context(self):
        """Test multi-turn conversation with context.

        Requires: foundry run phi-4
        This test will be skipped if server is not running.
        """
        client = LocalFoundryChatClient(endpoint=TEST_ENDPOINT)

        if not client._check_server_connection():
            pytest.skip("AI Foundry server not running (foundry run phi-4)")

        # Multi-turn conversation
        messages = [
            ChatMessage(role=Role.SYSTEM, text="You are a helpful assistant."),
            ChatMessage(role=Role.USER, text="My favorite color is blue."),
            ChatMessage(role=Role.ASSISTANT, text="That's nice! Blue is a great color."),
            ChatMessage(role=Role.USER, text="What is my favorite color?"),
        ]

        response = await client.get_response(messages)

        assert response is not None
        assert "blue" in response.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
