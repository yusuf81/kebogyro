#!/usr/bin/env python3

"""Debug script to test tool call JSON filtering"""

import json
from web_ui.core_logic import _is_tool_call_json

# Test cases that should be filtered out
test_cases = [
    # The exact JSON from the user report
    """{
  "name": "code_assistant_tool",
  "arguments": {
    "code_description": "A function to calculate the calories of coffee based on its ingredients and serving size.",
    "current_code_context": ""
  }
}""",
    
    # Variations that might slip through
    '{"name": "code_assistant_tool", "arguments": {"code_description": "test", "current_code_context": ""}}',
    
    # Single line with tool in name
    '{"name": "some_tool", "arguments": {}}',
    
    # Test with different key order
    '{"arguments": {"test": "value"}, "name": "test_tool"}',
    
    # Valid content that should NOT be filtered
    "This is regular text content",
    "Here's a function: def add(a, b): return a + b",
    '{"data": "some json but not tool call"}',
    
    # Edge cases
    "",
    "   ",
    "{}",
    '{"name": "test"}',  # Missing arguments
    '{"arguments": {}}',  # Missing name
    '{"name": "test", "arguments": {}}',  # No "tool" keyword
]

print("Testing tool call JSON filtering:")
print("=" * 50)

for i, test_case in enumerate(test_cases):
    result = _is_tool_call_json(test_case)
    print(f"\nTest case {i+1}:")
    print(f"Input: {repr(test_case[:100])}")
    print(f"Is tool call JSON: {result}")
    print(f"Should be filtered: {result}")

print("\n" + "=" * 50)
print("Summary:")
print("- Cases 1-4 should be filtered (True)")
print("- Cases 5-7 should NOT be filtered (False)")
print("- Cases 8-12 are edge cases")