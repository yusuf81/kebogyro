"""TDD tests for Outlines-based validation system."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
from pydantic import ValidationError

from web_ui.outlines_models import (
    ConfigValidationResult, 
    ToolCallResult, 
    ChatResponse,
    CodeAssistanceResponse,
    ContentFilterResult,
    StreamingChunk,
    MultiPathValidation,
    AgentStep,
    DebugInfo,
    ValidationMode
)


class TestConfigValidationResult:
    """Test ConfigValidationResult model."""
    
    def test_valid_config_creation(self):
        """Test creating valid configuration."""
        config = ConfigValidationResult(
            api_base="http://localhost:11434/v1",
            api_key="test-key",
            model_name="llama3",
            temperature=0.1,
            provider="ollama"
        )
        assert config.status == "valid"
        assert config.api_base == "http://localhost:11434/v1"
        assert config.temperature == 0.1
        assert config.errors == []
    
    def test_invalid_api_base_raises_error(self):
        """Test invalid API base raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidationResult(
                api_base="invalid-url",
                api_key="test-key",
                model_name="llama3",
                temperature=0.1,
                provider="ollama"
            )
        assert "API base must start with http:// or https://" in str(exc_info.value)
    
    def test_invalid_temperature_raises_error(self):
        """Test invalid temperature raises validation error."""
        with pytest.raises(ValidationError):
            ConfigValidationResult(
                api_base="http://localhost:11434/v1",
                api_key="test-key",
                model_name="llama3",
                temperature=3.0,  # Invalid: > 2.0
                provider="ollama"
            )
    
    def test_negative_temperature_raises_error(self):
        """Test negative temperature raises validation error."""
        with pytest.raises(ValidationError):
            ConfigValidationResult(
                api_base="http://localhost:11434/v1",
                api_key="test-key",
                model_name="llama3",
                temperature=-0.1,  # Invalid: < 0.0
                provider="ollama"
            )


class TestToolCallResult:
    """Test ToolCallResult model."""
    
    def test_successful_tool_call(self):
        """Test successful tool call result."""
        result = ToolCallResult(
            success=True,
            tool_name="code_generator",
            arguments={"language": "python", "task": "hello world"},
            result="print('Hello, World!')"
        )
        assert result.success is True
        assert result.tool_name == "code_generator"
        assert result.error is None
        assert result.is_filtered is False
    
    def test_failed_tool_call(self):
        """Test failed tool call result."""
        result = ToolCallResult(
            success=False,
            tool_name="code_generator",
            arguments={"language": "invalid"},
            error="Unsupported language"
        )
        assert result.success is False
        assert result.error == "Unsupported language"
        assert result.result is None
    
    def test_filtered_tool_call(self):
        """Test filtered tool call result."""
        result = ToolCallResult(
            success=True,
            tool_name="code_generator",
            arguments={"task": "test"},
            result="filtered content",
            is_filtered=True
        )
        assert result.is_filtered is True


class TestChatResponse:
    """Test ChatResponse model."""
    
    def test_normal_chat_response(self):
        """Test normal chat response."""
        response = ChatResponse(
            content="Hello, how can I help you?",
            is_complete=True
        )
        assert response.response_type == "normal"
        assert response.contains_code is False
        assert response.is_complete is True
    
    def test_code_chat_response(self):
        """Test chat response with code."""
        response = ChatResponse(
            content="Here's the code:\n```python\nprint('hello')\n```",
            is_complete=True,
            contains_code=True,
            response_type="code"
        )
        assert response.contains_code is True
        assert response.response_type == "code"
    
    def test_error_chat_response(self):
        """Test error chat response."""
        response = ChatResponse(
            content="An error occurred",
            is_complete=True,
            response_type="error"
        )
        assert response.response_type == "error"


class TestCodeAssistanceResponse:
    """Test CodeAssistanceResponse model."""
    
    def test_code_response_without_tools(self):
        """Test code response without tool calls."""
        response = CodeAssistanceResponse(
            content="Here's your code:",
            is_complete=True,
            response_type="code"
        )
        assert response.has_tool_calls is False
        assert response.tool_calls == []
        assert response.response_type == "code"
    
    def test_code_response_with_tools(self):
        """Test code response with tool calls."""
        tool_call = ToolCallResult(
            success=True,
            tool_name="code_generator",
            arguments={"language": "python"},
            result="print('Hello')"
        )
        
        response = CodeAssistanceResponse(
            content="Generated code:",
            has_tool_calls=True,
            tool_calls=[tool_call],
            is_complete=True,
            response_type="code"
        )
        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "code_generator"


class TestContentFilterResult:
    """Test ContentFilterResult model."""
    
    def test_unfiltered_content(self):
        """Test unfiltered content result."""
        result = ContentFilterResult(
            original_content="Hello world",
            filtered_content="Hello world",
            was_filtered=False,
            confidence=1.0
        )
        assert result.was_filtered is False
        assert result.filter_reason is None
        assert result.confidence == 1.0
    
    def test_filtered_content(self):
        """Test filtered content result."""
        result = ContentFilterResult(
            original_content='{"name": "tool", "arguments": {}}',
            filtered_content="",
            was_filtered=True,
            filter_reason="Tool call JSON detected",
            confidence=0.95
        )
        assert result.was_filtered is True
        assert result.filter_reason == "Tool call JSON detected"
        assert result.confidence == 0.95
    
    def test_invalid_confidence_raises_error(self):
        """Test invalid confidence raises error."""
        with pytest.raises(ValidationError):
            ContentFilterResult(
                original_content="test",
                filtered_content="test",
                was_filtered=False,
                confidence=1.5  # Invalid: > 1.0
            )


class TestStreamingChunk:
    """Test StreamingChunk model."""
    
    def test_text_chunk(self):
        """Test text streaming chunk."""
        chunk = StreamingChunk(
            content="Hello",
            chunk_type="text"
        )
        assert chunk.chunk_type == "text"
        assert chunk.should_display is True
        assert chunk.metadata == {}
    
    def test_filtered_chunk(self):
        """Test filtered streaming chunk."""
        chunk = StreamingChunk(
            content='{"tool": "call"}',
            chunk_type="filtered",
            should_display=False,
            metadata={"filter_reason": "tool_call"}
        )
        assert chunk.chunk_type == "filtered"
        assert chunk.should_display is False
        assert chunk.metadata["filter_reason"] == "tool_call"


class TestMultiPathValidation:
    """Test MultiPathValidation model."""
    
    def test_multi_path_validation_creation(self):
        """Test creating multi-path validation."""
        validation = MultiPathValidation(
            attempts=[
                {"result": "valid", "confidence": 0.9},
                {"result": "valid", "confidence": 0.8},
                {"result": "invalid", "confidence": 0.3}
            ],
            consensus={"result": "valid", "confidence": 0.85},
            confidence=0.85
        )
        assert len(validation.attempts) == 3
        assert validation.consensus["result"] == "valid"
        assert validation.mode == ValidationMode.STRICT
    
    def test_insufficient_attempts_raises_error(self):
        """Test insufficient attempts raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MultiPathValidation(
                attempts=[{"result": "valid"}],  # Only 1 attempt
                consensus={"result": "valid"},
                confidence=0.8
            )
        assert "at least 2 attempts" in str(exc_info.value)


class TestAgentStep:
    """Test AgentStep model."""
    
    def test_thought_step(self):
        """Test thought agent step."""
        step = AgentStep(
            action="thought",
            content="I need to generate code",
            reasoning="User asked for Python code"
        )
        assert step.action == "thought"
        assert step.tool_name is None
        assert step.confidence == 0.8
    
    def test_tool_call_step(self):
        """Test tool call agent step."""
        step = AgentStep(
            action="tool_call",
            content="Calling code generator",
            tool_name="code_generator",
            tool_args={"language": "python"},
            confidence=0.9
        )
        assert step.action == "tool_call"
        assert step.tool_name == "code_generator"
        assert step.tool_args == {"language": "python"}
        assert step.confidence == 0.9


class TestDebugInfo:
    """Test DebugInfo model."""
    
    def test_debug_info_creation(self):
        """Test creating debug info."""
        debug = DebugInfo()
        assert debug.raw_chunks == []
        assert debug.processed_chunks == []
        assert debug.total_raw_chars == 0
        assert debug.total_processed_chars == 0
    
    def test_add_raw_chunk(self):
        """Test adding raw chunk."""
        debug = DebugInfo()
        debug.add_raw_chunk("Hello", 1234567890.0)
        
        assert len(debug.raw_chunks) == 1
        assert debug.raw_chunks[0] == "Hello"
        assert debug.total_raw_chars == 5
        assert len(debug.timing_info) == 1
        assert debug.timing_info[0]["type"] == "raw"
    
    def test_add_processed_chunk(self):
        """Test adding processed chunk."""
        debug = DebugInfo()
        debug.add_processed_chunk("Hi", "buffer_state", 1234567890.0)
        
        assert len(debug.processed_chunks) == 1
        assert debug.processed_chunks[0] == "Hi"
        assert debug.total_processed_chars == 2
        assert debug.buffer_states[0] == "buffer_state"
        assert debug.timing_info[0]["type"] == "processed"
    
    def test_get_summary(self):
        """Test getting summary statistics."""
        debug = DebugInfo()
        debug.add_raw_chunk("Hello World")  # 11 chars
        debug.add_processed_chunk("Hello")   # 5 chars
        
        summary = debug.get_summary()
        assert summary["raw_chunks_count"] == 1
        assert summary["processed_chunks_count"] == 1
        assert summary["total_raw_chars"] == 11
        assert summary["total_processed_chars"] == 5
        assert summary["chars_difference"] == 6
        assert summary["processing_efficiency"] == 5/11


class TestValidationIntegration:
    """Integration tests for validation models."""
    
    def test_complete_validation_flow(self):
        """Test complete validation workflow."""
        # Create config
        config = ConfigValidationResult(
            api_base="http://localhost:11434/v1",
            api_key="test-key",
            model_name="llama3",
            temperature=0.1,
            provider="ollama"
        )
        
        # Create tool call
        tool_call = ToolCallResult(
            success=True,
            tool_name="code_generator",
            arguments={"language": "python"},
            result="print('Hello')"
        )
        
        # Create response
        response = CodeAssistanceResponse(
            content="Generated code:",
            has_tool_calls=True,
            tool_calls=[tool_call],
            is_complete=True
        )
        
        # Validate all components
        assert config.status == "valid"
        assert tool_call.success is True
        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1
    
    def test_validation_error_handling(self):
        """Test validation error handling."""
        # Test invalid configuration
        with pytest.raises(ValidationError):
            ConfigValidationResult(
                api_base="invalid-url",
                api_key="test-key",
                model_name="llama3",
                temperature=0.1,
                provider="ollama"
            )
        
        # Test invalid tool call
        with pytest.raises(ValidationError):
            ToolCallResult(
                success=True,
                tool_name="",  # Empty tool name should fail
                arguments={}
            )