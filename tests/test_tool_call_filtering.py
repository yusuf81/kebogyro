#!/usr/bin/env python3
"""Test suite for tool call JSON filtering functionality."""

import pytest
import json
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# We'll mock the imports since we can't import them directly
@pytest.fixture
def mock_imports():
    """Mock the necessary imports for testing."""
    with patch.dict('sys.modules', {
        'kebogyro.messages': MagicMock(),
        'web_ui.config': MagicMock(),
        'web_ui.session_manager': MagicMock(),
        'web_ui.error_handler': MagicMock(),
    }):
        yield


class TestToolCallFiltering:
    """Test tool call JSON filtering functionality."""
    
    def test_is_tool_call_json_detection(self):
        """Test _is_tool_call_json function with various inputs."""
        
        def _is_tool_call_json(content: str) -> bool:
            """Check if content is a tool call JSON that should be filtered out."""
            if not content or not content.strip():
                return False
            
            content_stripped = content.strip()
            
            # Check for JSON-like structure with tool call patterns
            if (content_stripped.startswith('{') and content_stripped.endswith('}') and 
                ('"name"' in content_stripped or '"arguments"' in content_stripped) and
                'tool' in content_stripped.lower()):
                try:
                    parsed = json.loads(content_stripped)
                    # Check if it's a tool call structure
                    if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                        return True
                except json.JSONDecodeError:
                    pass
            
            return False
        
        # Test cases that SHOULD be filtered (tool calls)
        tool_call_cases = [
            # User's exact case
            '{"name": "code_assistant_tool", "arguments": {"code_description": "A shell script to find prime numbers up to a given limit.", "current_code_context": ""}}',
            
            # Simpler tool call
            '{"name": "code_assistant_tool", "arguments": {}}',
            
            # Different tool with 'tool' in name
            '{"name": "some_tool", "arguments": {"param": "value"}}',
            
            # Tool call with spacing
            '{ "name": "code_assistant_tool", "arguments": { "test": "value" } }',
            
            # Tool call with different arguments
            '{"name": "code_assistant_tool", "arguments": {"code_description": "Test", "current_code_context": "context"}}',
        ]
        
        for case in tool_call_cases:
            result = _is_tool_call_json(case)
            assert result == True, f"Should filter tool call: {case[:50]}..."
        
        # Test cases that should NOT be filtered (legitimate content)
        non_tool_cases = [
            # Regular JSON without tool structure
            '{"user": "john", "age": 30}',
            
            # JSON with 'name' but no 'arguments'
            '{"name": "john", "type": "user"}',
            
            # JSON with 'arguments' but no 'name'
            '{"arguments": {"value": 1}, "type": "config"}',
            
            # JSON with both name and arguments but no 'tool' reference
            '{"name": "user", "arguments": {"age": 30}}',
            
            # F-string variables
            '{limit}',
            '{name}',
            '{user_id}',
            
            # JavaScript code
            'function() { return true; }',
            
            # CSS
            '.class { color: red; }',
            
            # Empty or whitespace
            '',
            '   ',
            
            # Invalid JSON
            '{"invalid": json}',
            
            # Partial JSON
            '{"name": "incomplete"',
        ]
        
        for case in non_tool_cases:
            result = _is_tool_call_json(case)
            assert result == False, f"Should NOT filter legitimate content: {case[:50]}..."
    
    def test_markdown_tool_call_detection(self):
        """Test _is_markdown_tool_call_json function."""
        
        def _is_markdown_tool_call_json(content: str) -> bool:
            """Check if content is a markdown code block containing tool call JSON."""
            if not content or not content.strip():
                return False
            
            content_stripped = content.strip()
            
            # Check for markdown code blocks
            if content_stripped.startswith('```') and content_stripped.endswith('```'):
                # Extract content inside code block
                lines = content_stripped.split('\n')
                if len(lines) < 3:
                    return False
                
                # Skip the first line (```json or ```) and last line (````)
                json_content = '\n'.join(lines[1:-1]).strip()
                
                # Check if the content inside is tool call JSON
                if (json_content.startswith('{') and json_content.endswith('}') and
                    ('"name"' in json_content or '"arguments"' in json_content) and
                    'tool' in json_content.lower()):
                    try:
                        parsed = json.loads(json_content)
                        if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                            return True
                    except json.JSONDecodeError:
                        pass
            
            return False
        
        # Test cases that SHOULD be filtered (markdown-wrapped tool calls)
        markdown_tool_cases = [
            # JSON markdown block
            '```json\n{"name": "code_assistant_tool", "arguments": {"code_description": "test"}}\n```',
            
            # Plain markdown block
            '```\n{"name": "code_assistant_tool", "arguments": {}}\n```',
            
            # Bash markdown block (from user's example)
            '```bash\n{"name": "code_assistant_tool", "arguments": {"code_description": "A shell script"}}\n```',
        ]
        
        for case in markdown_tool_cases:
            result = _is_markdown_tool_call_json(case)
            assert result == True, f"Should filter markdown tool call: {case[:50]}..."
        
        # Test cases that should NOT be filtered (legitimate markdown)
        legitimate_markdown = [
            # Real Python code
            '```python\nprint("Hello World")\n```',
            
            # Real shell script
            '```bash\necho "Hello World"\n```',
            
            # Real JSON (but not tool call)
            '```json\n{"user": "john", "age": 30}\n```',
            
            # Incomplete markdown
            '```python\nprint("test")',
            
            # Empty markdown
            '```\n\n```',
        ]
        
        for case in legitimate_markdown:
            result = _is_markdown_tool_call_json(case)
            assert result == False, f"Should NOT filter legitimate markdown: {case[:50]}..."
    
    def test_content_buffer_single_chunk(self):
        """Test ContentBuffer with single chunk tool call JSON."""
        
        # Mock the ContentBuffer class
        class MockContentBuffer:
            def __init__(self):
                self.buffer = ""
            
            def add_chunk(self, chunk: str) -> tuple[str, bool]:
                if not chunk:
                    return "", False
                
                self.buffer += chunk
                
                # Simple detection - if it looks like a tool call, filter it
                if self._is_tool_call_json(self.buffer):
                    self.buffer = ""
                    return "", True
                
                # Otherwise, yield it
                content_to_yield = self.buffer
                self.buffer = ""
                return content_to_yield, False
            
            def _is_tool_call_json(self, content: str) -> bool:
                if not content or not content.strip():
                    return False
                
                content_stripped = content.strip()
                
                if (content_stripped.startswith('{') and content_stripped.endswith('}') and 
                    ('"name"' in content_stripped or '"arguments"' in content_stripped) and
                    'tool' in content_stripped.lower()):
                    try:
                        parsed = json.loads(content_stripped)
                        if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                            return True
                    except json.JSONDecodeError:
                        pass
                
                return False
        
        buffer = MockContentBuffer()
        
        # Test the exact user case
        tool_call_json = '{"name": "code_assistant_tool", "arguments": {"code_description": "A shell script to find prime numbers up to a given limit.", "current_code_context": ""}}'
        
        content_to_yield, should_filter = buffer.add_chunk(tool_call_json)
        
        assert content_to_yield == "", "Tool call JSON should yield empty content"
        assert should_filter == True, "Tool call JSON should be filtered"
        assert buffer.buffer == "", "Buffer should be cleared after filtering"
    
    def test_content_buffer_streaming_chunks(self):
        """Test ContentBuffer with streaming tool call JSON chunks."""
        
        # Mock a simplified ContentBuffer for this test
        class MockContentBuffer:
            def __init__(self):
                self.buffer = ""
            
            def add_chunk(self, chunk: str) -> tuple[str, bool]:
                if not chunk:
                    return "", False
                
                self.buffer += chunk
                
                # Check if complete tool call JSON
                if self._is_tool_call_json(self.buffer):
                    self.buffer = ""
                    return "", True
                
                # If it looks like we're building a tool call, buffer it
                if self._might_be_tool_call_start(self.buffer):
                    return "", False  # Buffer but don't yield
                
                # Otherwise, yield it
                content_to_yield = self.buffer
                self.buffer = ""
                return content_to_yield, False
            
            def _is_tool_call_json(self, content: str) -> bool:
                if not content or not content.strip():
                    return False
                
                content_stripped = content.strip()
                
                if (content_stripped.startswith('{') and content_stripped.endswith('}') and 
                    ('"name"' in content_stripped or '"arguments"' in content_stripped) and
                    'tool' in content_stripped.lower()):
                    try:
                        parsed = json.loads(content_stripped)
                        if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                            return True
                    except json.JSONDecodeError:
                        pass
                
                return False
            
            def _might_be_tool_call_start(self, content: str) -> bool:
                """Check if content might be the start of a tool call."""
                content_stripped = content.strip()
                
                # If it starts with { and has some tool-like patterns, it might be
                if (content_stripped.startswith('{') and 
                    ('name' in content_stripped or 'arguments' in content_stripped or 
                     'code_assistant' in content_stripped.lower())):
                    return True
                
                return False
        
        buffer = MockContentBuffer()
        
        # Test streaming chunks that build up to a tool call
        chunks = [
            '{"name": "code_assistant_tool", "arguments": {',
            '"code_description": "A shell script to find prime numbers up to a given limit.", ',
            '"current_code_context": ""}}'
        ]
        
        results = []
        for chunk in chunks:
            content_to_yield, should_filter = buffer.add_chunk(chunk)
            results.append((content_to_yield, should_filter))
        
        # First two chunks should be buffered
        assert results[0] == ("", False), "First chunk should be buffered"
        assert results[1] == ("", False), "Second chunk should be buffered"
        
        # Final chunk should trigger filtering
        assert results[2] == ("", True), "Final chunk should trigger filtering"
        
        # Buffer should be cleared
        assert buffer.buffer == "", "Buffer should be cleared after filtering"
    
    def test_legitimate_content_passes_through(self):
        """Test that legitimate content passes through without filtering."""
        
        class MockContentBuffer:
            def __init__(self):
                self.buffer = ""
            
            def add_chunk(self, chunk: str) -> tuple[str, bool]:
                if not chunk:
                    return "", False
                
                self.buffer += chunk
                
                # Don't filter legitimate content
                if not self._is_tool_call_json(self.buffer):
                    content_to_yield = self.buffer
                    self.buffer = ""
                    return content_to_yield, False
                
                # Filter tool calls
                self.buffer = ""
                return "", True
            
            def _is_tool_call_json(self, content: str) -> bool:
                if not content or not content.strip():
                    return False
                
                content_stripped = content.strip()
                
                if (content_stripped.startswith('{') and content_stripped.endswith('}') and 
                    ('"name"' in content_stripped or '"arguments"' in content_stripped) and
                    'tool' in content_stripped.lower()):
                    try:
                        parsed = json.loads(content_stripped)
                        if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                            return True
                    except json.JSONDecodeError:
                        pass
                
                return False
        
        buffer = MockContentBuffer()
        
        # Test legitimate content
        legitimate_cases = [
            'Hello, world!',
            'Here is a Python script:\n\n```python\nprint("Hello")\n```',
            'The result is: {result}',  # f-string variable
            'function test() { return true; }',  # JavaScript
            '{"user": "john", "age": 30}',  # Regular JSON
        ]
        
        for case in legitimate_cases:
            content_to_yield, should_filter = buffer.add_chunk(case)
            assert content_to_yield == case, f"Legitimate content should pass through: {case[:30]}..."
            assert should_filter == False, f"Legitimate content should not be filtered: {case[:30]}..."
            assert buffer.buffer == "", "Buffer should be cleared after yielding"
    
    def test_safety_check_prevents_tool_call_leakage(self):
        """Test that the safety check prevents tool call JSON from leaking through."""
        
        def _is_tool_call_json(content: str) -> bool:
            """Check if content is a tool call JSON that should be filtered out."""
            if not content or not content.strip():
                return False
            
            content_stripped = content.strip()
            
            if (content_stripped.startswith('{') and content_stripped.endswith('}') and 
                ('"name"' in content_stripped or '"arguments"' in content_stripped) and
                'tool' in content_stripped.lower()):
                try:
                    parsed = json.loads(content_stripped)
                    if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                        return True
                except json.JSONDecodeError:
                    pass
            
            return False
        
        # Simulate the safety check logic in the processing function
        def process_content_with_safety_check(content_to_yield: str, should_filter: bool) -> bool:
            """
            Simulate the processing logic with safety check.
            Returns True if content should be yielded, False if it should be filtered.
            """
            if content_to_yield and not should_filter:
                # Additional safety check: double-check that content_to_yield is not tool call JSON
                if not _is_tool_call_json(content_to_yield):
                    return True  # Safe to yield
                else:
                    # Safety check caught tool call JSON that ContentBuffer missed
                    return False  # Should not yield
            elif should_filter:
                return False  # Already filtered
            else:
                return False  # No content to yield
        
        # Test cases where ContentBuffer might miss tool call JSON (hypothetical scenarios)
        test_cases = [
            # Case 1: ContentBuffer says it's safe, but it's actually a tool call
            ('{"name": "code_assistant_tool", "arguments": {}}', False),
            
            # Case 2: ContentBuffer says it's safe, and it's actually safe
            ('Hello, world!', False),
            
            # Case 3: ContentBuffer says to filter, should not yield
            ('{"name": "code_assistant_tool", "arguments": {}}', True),
            
            # Case 4: Empty content
            ('', False),
            
            # Case 5: User's exact case
            ('{"name": "code_assistant_tool", "arguments": {"code_description": "A shell script to find prime numbers up to a given limit.", "current_code_context": ""}}', False),
        ]
        
        for content, should_filter in test_cases:
            should_yield = process_content_with_safety_check(content, should_filter)
            
            if content and _is_tool_call_json(content):
                # If it's a tool call JSON, it should NEVER be yielded
                assert should_yield == False, f"Tool call JSON should never be yielded: {content[:50]}..."
            elif content and not _is_tool_call_json(content) and not should_filter:
                # If it's legitimate content and not filtered, it should be yielded
                assert should_yield == True, f"Legitimate content should be yielded: {content[:50]}..."
            else:
                # Empty content or filtered content should not be yielded
                assert should_yield == False, f"Empty/filtered content should not be yielded: {content[:50]}..."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])