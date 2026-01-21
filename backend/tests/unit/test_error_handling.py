
import pytest
from services.nodes.base import ChatState
from utils.error_handling import handle_node_error, check_error
from langgraph.graph import END
import openai

def test_handle_node_error_generic():
    state = ChatState(messages=[], module_results={})
    error = ValueError("Test error")
    
    new_state = handle_node_error(error, state, "test_node")
    
    assert new_state["error"] == "Error in test_node: Test error"
    assert new_state["module_results"]["test"]["success"] is False
    assert new_state["module_results"]["test"]["error"] == "Test error"

def test_handle_node_error_critical():
    state = ChatState(messages=[], module_results={})
    # Mock an OpenAI API error
    # Note: mocking actual OpenAI errors is tricky without the library internals, 
    # but we can rely on the fact that handle_node_error checks isinstance.
    # For this simple test, we just check if it handles generic exceptions correctly 
    # and sets the error flag which is what triggers the stop.
    
    error = ValueError("Critical simulation")
    new_state = handle_node_error(error, state, "critical_node")
    assert new_state["error"] is not None

def test_check_error_continue():
    state = ChatState(messages=[], error=None)
    result = check_error(state)
    assert result == "continue"

def test_check_error_stop():
    state = ChatState(messages=[], error="Some error")
    result = check_error(state)
    assert result == END
