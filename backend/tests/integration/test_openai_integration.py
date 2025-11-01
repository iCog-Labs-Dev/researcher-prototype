# integration_test.py
import os
import pytest
from graph_builder import create_chat_graph
from unittest.mock import AsyncMock, patch
from config import DEFAULT_MODEL

@pytest.fixture
def sample_state():
    return {
        "messages": [],
        "user_id": "test_user",
        "thread_id": "test_thread", 
        "model": DEFAULT_MODEL,
        "temperature": 0.0,  # Use 0 for deterministic results
        "max_tokens": 20
    }

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key found")
def test_openai_integration():
    """Test that the chat graph works with the real OpenAI API when key is available."""
    graph = create_chat_graph()
    state = {
        "messages": [
            {"role": "user", "content": "Say 'This is a test' and nothing else"}
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 20,
    }
    result = graph.invoke(state)

    assert "messages" in result
    assert len(result["messages"]) == 2
    assert result["messages"][1]["role"] == "assistant"
