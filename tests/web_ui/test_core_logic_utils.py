import pytest
from web_ui.core_logic import _is_tool_call_json


class TestCoreLogicUtils:
    """Tests for core logic utility functions."""

    def test_is_tool_call_json_detects_tool_call(self):
        """Test that _is_tool_call_json detects tool call JSON."""
        tool_call_json = '''
        {
            "name": "code_assistant_tool",
            "arguments": {
                "code_description": "Create a Python function",
                "current_code_context": ""
            }
        }
        '''
        
        assert _is_tool_call_json(tool_call_json) is True

    def test_is_tool_call_json_ignores_regular_content(self):
        """Test that _is_tool_call_json ignores regular content."""
        regular_content = "Here's a Python function for you:\n\ndef fibonacci(n):\n    if n <= 1:\n        return n"
        
        assert _is_tool_call_json(regular_content) is False

    def test_is_tool_call_json_ignores_empty_content(self):
        """Test that _is_tool_call_json ignores empty content."""
        assert _is_tool_call_json("") is False
        assert _is_tool_call_json("   ") is False
        assert _is_tool_call_json(None) is False

    def test_is_tool_call_json_ignores_invalid_json(self):
        """Test that _is_tool_call_json ignores invalid JSON."""
        invalid_json = '{"name": "test", "arguments": invalid}'
        
        assert _is_tool_call_json(invalid_json) is False

    def test_is_tool_call_json_ignores_non_tool_json(self):
        """Test that _is_tool_call_json ignores non-tool JSON."""
        non_tool_json = '{"message": "Hello", "status": "success"}'
        
        assert _is_tool_call_json(non_tool_json) is False

    def test_is_tool_call_json_detects_various_tool_formats(self):
        """Test that _is_tool_call_json detects various tool call formats."""
        # Format 1: Standard tool call
        tool_call_1 = '{"name": "my_tool", "arguments": {"param": "value"}}'
        assert _is_tool_call_json(tool_call_1) is True
        
        # Format 2: With tool in name
        tool_call_2 = '{"name": "code_assistant_tool", "arguments": {}}'
        assert _is_tool_call_json(tool_call_2) is True
        
        # Format 3: Different structure but has tool indicators
        tool_call_3 = '{"tool_name": "test", "arguments": {"code": "python"}}'
        # This should be False since it doesn't have exact "name" field
        assert _is_tool_call_json(tool_call_3) is False