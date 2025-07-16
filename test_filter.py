#!/usr/bin/env python3
import json
import re

def _is_tool_call_json(content: str) -> bool:
    """Check if content is a tool call JSON that should be filtered out."""
    if not content or not content.strip():
        return False
    
    # Check for JSON-like structure with tool call patterns
    content = content.strip()
    if (content.startswith('{') and content.endswith('}') and 
        ('"name"' in content or '"arguments"' in content) and
        'tool' in content.lower()):
        try:
            parsed = json.loads(content)
            # Check if it's a tool call structure
            if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                return True
        except json.JSONDecodeError:
            pass
    
    return False

# Test with actual tool call JSON
test_json = """{
  "name": "code_assistant_tool",
  "arguments": {
    "code_description": "A function to calculate the calories of coffee based on its ingredients and serving size.",
    "current_code_context": ""
  }
}"""

print("Testing tool call JSON detection:")
print(f"Input: {test_json}")
print(f"Is tool call JSON: {_is_tool_call_json(test_json)}")
print(f"Should be filtered: {_is_tool_call_json(test_json)}")

# Test with normal content
normal_content = "Here's a JavaScript function for you:\n\nfunction calculateCalories() {\n  return 100;\n}"
print(f"\nNormal content: {normal_content}")
print(f"Is tool call JSON: {_is_tool_call_json(normal_content)}")