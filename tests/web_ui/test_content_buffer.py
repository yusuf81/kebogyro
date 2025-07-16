"""Tests for ContentBuffer class in core_logic.py."""

import pytest
from web_ui.core_logic import ContentBuffer


class TestContentBuffer:
    """Tests for ContentBuffer class."""

    def test_content_buffer_init(self):
        """Test ContentBuffer initialization."""
        buffer = ContentBuffer()
        assert buffer.buffer == ""
        assert buffer.max_buffer_size == 2000
        
        # Test custom max size
        buffer = ContentBuffer(max_buffer_size=500)
        assert buffer.max_buffer_size == 500

    def test_add_chunk_normal_content(self):
        """Test adding normal content chunks."""
        buffer = ContentBuffer()
        
        content, should_filter = buffer.add_chunk("Hello world")
        assert content == "Hello world"
        assert should_filter is False

    def test_add_chunk_empty_content(self):
        """Test adding empty content."""
        buffer = ContentBuffer()
        
        content, should_filter = buffer.add_chunk("")
        assert content == ""
        assert should_filter is False
        
        content, should_filter = buffer.add_chunk(None)
        assert content == ""
        assert should_filter is False

    def test_add_chunk_filters_complete_tool_call_json(self):
        """Test that complete tool call JSON is filtered."""
        buffer = ContentBuffer()
        
        tool_call_json = '''
        {
            "name": "code_assistant_tool",
            "arguments": {
                "code_description": "Create a Python function",
                "current_code_context": ""
            }
        }
        '''
        
        content, should_filter = buffer.add_chunk(tool_call_json)
        assert content == ""
        assert should_filter is True

    def test_add_chunk_filters_accumulated_tool_call_json(self):
        """Test that accumulated tool call JSON is filtered."""
        buffer = ContentBuffer()
        
        # Add chunks that together form tool call JSON
        chunk1 = '{"name": "code_assistant_tool"'
        chunk2 = ', "arguments": {"code_description": "test"'
        chunk3 = ', "current_code_context": ""}}'
        
        # First chunk should be buffered (not yielded)
        content1, should_filter1 = buffer.add_chunk(chunk1)
        assert content1 == ""
        assert should_filter1 is False
        
        # Second chunk should be buffered
        content2, should_filter2 = buffer.add_chunk(chunk2)
        assert content2 == ""
        assert should_filter2 is False
        
        # Third chunk completes the JSON and should trigger filtering
        content3, should_filter3 = buffer.add_chunk(chunk3)
        assert content3 == ""
        assert should_filter3 is True
        
        # Buffer should be cleared after filtering
        assert buffer.buffer == ""

    def test_add_chunk_handles_mixed_content(self):
        """Test handling of mixed content with tool patterns."""
        buffer = ContentBuffer()
        
        # Add content with tool patterns but not JSON structure
        content1, should_filter1 = buffer.add_chunk("The code_description is")
        assert content1 == "The code_description is"  # No JSON structure, not buffered
        assert should_filter1 is False
        
        # Add more content that doesn't complete JSON
        content2, should_filter2 = buffer.add_chunk(" about creating a function")
        assert content2 == " about creating a function"  # Normal content
        assert should_filter2 is False

    def test_add_chunk_buffer_size_limit(self):
        """Test buffer size limit handling."""
        buffer = ContentBuffer(max_buffer_size=50)
        
        # Add short normal content first
        short_content = "hello world"
        content1, should_filter1 = buffer.add_chunk(short_content)
        
        # Should return the content since it doesn't have tool patterns
        assert content1 == short_content
        assert should_filter1 is False
        
        # Buffer should be empty after yielding
        assert buffer.buffer == ""
        
        # Test that max_buffer_size is respected for buffered content
        buffer.buffer = "x" * 60  # Manually set buffer to exceed max size
        buffer.add_chunk("y")
        assert len(buffer.buffer) <= buffer.max_buffer_size

    def test_contains_tool_call_pattern(self):
        """Test _contains_tool_call_pattern method."""
        buffer = ContentBuffer()
        
        # Test various tool patterns with JSON structure
        assert buffer._contains_tool_call_pattern('"name"') is True
        assert buffer._contains_tool_call_pattern('"arguments"') is True
        assert buffer._contains_tool_call_pattern('{"name": "code_assistant_tool"}') is True
        assert buffer._contains_tool_call_pattern('"code_description"') is True
        assert buffer._contains_tool_call_pattern('"current_code_context"') is True
        
        # Test case insensitive with JSON structure
        assert buffer._contains_tool_call_pattern('{"name": "CODE_ASSISTANT_TOOL"}') is True
        assert buffer._contains_tool_call_pattern('"NAME"') is True
        
        # Test content without tool patterns or JSON structure
        assert buffer._contains_tool_call_pattern('hello world') is False
        assert buffer._contains_tool_call_pattern('function test() {}') is False
        assert buffer._contains_tool_call_pattern('code_assistant_tool') is False  # No JSON structure

    def test_reset_buffer(self):
        """Test buffer reset functionality."""
        buffer = ContentBuffer()
        
        # Add some content to buffer
        buffer.add_chunk('{"name": "test"')
        assert buffer.buffer != ""
        
        # Reset buffer
        buffer.reset()
        assert buffer.buffer == ""

    def test_partial_json_accumulation(self):
        """Test that partial JSON is accumulated correctly."""
        buffer = ContentBuffer()
        
        # Simulate streaming partial JSON
        chunks = [
            '{',
            '"name": "code_assistant_tool",',
            '"arguments": {',
            '"code_description": "test",',
            '"current_code_context": ""',
            '}',
            '}'
        ]
        
        for i, chunk in enumerate(chunks):
            content, should_filter = buffer.add_chunk(chunk)
            
            # All chunks should be buffered (no content yielded) until complete JSON is detected
            if i < len(chunks) - 1:
                # Not the last chunk - should be buffered
                assert content == ""
                assert should_filter is False
            else:
                # Last chunk completes JSON - should be filtered
                assert content == ""
                assert should_filter is True

    def test_normal_content_after_tool_patterns(self):
        """Test that normal content is yielded after tool patterns."""
        buffer = ContentBuffer()
        
        # Add content with tool pattern and JSON structure
        content1, should_filter1 = buffer.add_chunk('"name"')
        assert content1 == ""  # Has JSON structure and tool pattern, buffered
        assert should_filter1 is False
        
        # Add normal content (should not match tool patterns)
        content2, should_filter2 = buffer.add_chunk(' is important')
        assert content2 == '"name" is important'  # Full buffered content
        assert should_filter2 is False

    def test_markdown_streaming_chunks_are_filtered(self):
        """Test that markdown wrapped tool call JSON is filtered when streamed in chunks."""
        buffer = ContentBuffer()
        
        # Simulate streaming chunks for markdown wrapped tool call
        chunks = [
            '```', 'json', '\n', 
            '{\n  "name": "code_assistant_tool",\n  "arguments": {\n    "code_description": "test"\n  }\n}',
            '\n```'
        ]
        
        yielded_content = []
        filtered = False
        for chunk in chunks:
            content, should_filter = buffer.add_chunk(chunk)
            if content and not should_filter:
                yielded_content.append(content)
            elif should_filter:
                # Filtering should happen when we have complete tool call JSON
                filtered = True
                break
        
        # Should yield nothing since entire content is filtered
        assert ''.join(yielded_content) == ""
        
        # Buffer should be empty after filtering
        assert buffer.buffer == ""
        
        # Should have triggered filtering
        assert filtered is True

    def test_partial_markdown_detection(self):
        """Test that partial markdown is detected correctly."""
        buffer = ContentBuffer()
        
        # Start with markdown
        content1, should_filter1 = buffer.add_chunk('```')
        assert content1 == ""  # Should be buffered
        assert should_filter1 is False
        
        # Add language specifier
        content2, should_filter2 = buffer.add_chunk('json')
        assert content2 == ""  # Should be buffered
        assert should_filter2 is False
        
        # Add newline
        content3, should_filter3 = buffer.add_chunk('\n')
        assert content3 == ""  # Should be buffered
        assert should_filter3 is False
        
        # Add some normal content - should still be buffered because we're in markdown
        content4, should_filter4 = buffer.add_chunk('hello world')
        assert content4 == ""  # Should be buffered
        assert should_filter4 is False