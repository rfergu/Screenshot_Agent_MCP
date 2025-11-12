"""Tests for local mode chat client."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_framework._types import ChatMessage, Role
from azure.ai.inference.models import UserMessage, SystemMessage, AssistantMessage
from phi3_chat_client import LocalFoundryChatClient


class TestMessageConversion:
    """Test message conversion for LocalFoundryChatClient."""

    def test_convert_string_message(self):
        """Test converting a simple string to inference format."""
        client = LocalFoundryChatClient()
        result = client._convert_to_inference_messages("Hello world")

        assert len(result) == 1
        assert isinstance(result[0], UserMessage)
        assert result[0].content == "Hello world"

    def test_convert_chat_message_user(self):
        """Test converting ChatMessage with user role."""
        client = LocalFoundryChatClient()
        msg = ChatMessage(role=Role.USER, text="What is 5+5?")

        result = client._convert_to_inference_messages(msg)

        assert len(result) == 1
        assert isinstance(result[0], UserMessage)
        assert result[0].content == "What is 5+5?"

    def test_convert_chat_message_system(self):
        """Test converting ChatMessage with system role."""
        client = LocalFoundryChatClient()
        msg = ChatMessage(role=Role.SYSTEM, text="You are a helpful assistant.")

        result = client._convert_to_inference_messages(msg)

        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are a helpful assistant."

    def test_convert_chat_message_assistant(self):
        """Test converting ChatMessage with assistant role."""
        client = LocalFoundryChatClient()
        msg = ChatMessage(role=Role.ASSISTANT, text="I can help you with that.")

        result = client._convert_to_inference_messages(msg)

        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)
        assert result[0].content == "I can help you with that."

    def test_convert_message_list(self):
        """Test converting a list of different message types."""
        client = LocalFoundryChatClient()
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
        client = LocalFoundryChatClient()
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
        client = LocalFoundryChatClient()
        msg = ChatMessage(role=Role.USER, text=None)

        result = client._convert_to_inference_messages(msg)

        assert len(result) == 1
        assert isinstance(result[0], UserMessage)
        assert result[0].content == ""


@pytest.mark.integration
class TestLocalModeIntegration:
    """Integration tests for local mode (requires AI Foundry server running)."""

    @pytest.mark.asyncio
    async def test_simple_chat_query(self):
        """Test a simple chat query against local server.

        Requires: foundry run phi-4
        This test will be skipped if server is not running.
        """
        client = LocalFoundryChatClient()

        # Check if server is accessible
        if not client._check_server_connection():
            pytest.skip("AI Foundry server not running (foundry run phi-4)")

        # Simple math query
        response = await client.get_response("What is 5 + 5?")

        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        assert "10" in response.content.lower()

    @pytest.mark.asyncio
    async def test_conversation_context(self):
        """Test multi-turn conversation with context.

        Requires: foundry run phi-4
        This test will be skipped if server is not running.
        """
        client = LocalFoundryChatClient()

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
        assert "blue" in response.content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
