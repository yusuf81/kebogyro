"""Minimal integration tests for Outlines validation system."""

import pytest
from unittest.mock import Mock, patch
from web_ui.outlines_models import (
    ConfigValidationResult,
    ToolCallDetection,
    ContentFilterResult,
    StreamingChunk,
    DebugInfo
)
from web_ui.outlines_validator import get_validator


class TestOutlinesIntegrationMinimal:
    """Minimal integration tests that don't require Ollama model."""
    
    def test_outlines_models_are_importable(self):
        """Test that all Outlines models can be imported and created."""
        # Test ConfigValidationResult
        config_result = ConfigValidationResult(
            api_base="http://localhost:11434/v1",
            api_key="test",
            model_name="llama3",
            temperature=0.1,
            provider="ollama"
        )
        assert config_result.status == "valid"
        assert config_result.is_valid == True
        
        # Test ToolCallDetection
        tool_detection = ToolCallDetection(
            is_tool_call=True,
            should_filter=True,
            confidence=0.9,
            reasoning="Contains tool call pattern"
        )
        assert tool_detection.is_tool_call == True
        assert tool_detection.should_filter == True
        
        # Test ContentFilterResult
        filter_result = ContentFilterResult(
            original_content="test content",
            filtered_content="",
            was_filtered=True,
            confidence=0.8
        )
        assert filter_result.was_filtered == True
        
        # Test StreamingChunk
        chunk = StreamingChunk(
            content="hello",
            chunk_type="text",
            should_display=True
        )
        assert chunk.should_display == True
        
        # Test DebugInfo
        debug_info = DebugInfo()
        debug_info.add_raw_chunk("test chunk")
        assert len(debug_info.raw_chunks) == 1
    
    def test_model_validation_rules(self):
        """Test Pydantic model validation rules."""
        # Test invalid API base
        with pytest.raises(ValueError, match="API base must start with http"):
            ConfigValidationResult(
                api_base="invalid-url",
                api_key="test",
                model_name="llama3",
                temperature=0.1,
                provider="ollama"
            )
        
        # Test invalid temperature
        with pytest.raises(ValueError, match="Input should be less than or equal to 2"):
            ConfigValidationResult(
                api_base="http://localhost:11434/v1",
                api_key="test",
                model_name="llama3",
                temperature=3.0,  # Invalid
                provider="ollama"
            )
        
        # Test confidence validation (should fail with invalid range)
        with pytest.raises(ValueError, match="Input should be less than or equal to 1"):
            ToolCallDetection(
                is_tool_call=True,
                should_filter=True,
                confidence=1.5,  # Invalid
                reasoning="Test"
            )
    
    def test_backward_compatibility_properties(self):
        """Test that backward compatibility properties work."""
        config_result = ConfigValidationResult(
            api_base="http://localhost:11434/v1",
            api_key="test",
            model_name="llama3",
            temperature=0.1,
            provider="ollama"
        )
        
        # Test backward compatibility properties
        assert config_result.is_valid == True
        assert config_result.missing_vars == []
        
        # Test invalid config
        invalid_config = ConfigValidationResult(
            status="invalid",
            api_base="http://localhost:11434/v1",
            api_key="test",
            model_name="llama3",
            temperature=0.1,
            provider="ollama",
            errors=["Test error"]
        )
        
        assert invalid_config.is_valid == False
        assert len(invalid_config.errors) > 0
    
    def test_debug_info_functionality(self):
        """Test DebugInfo model functionality."""
        debug_info = DebugInfo()
        
        # Test adding chunks
        debug_info.add_raw_chunk("chunk 1", 1000.0)
        debug_info.add_raw_chunk("chunk 2", 1001.0)
        debug_info.add_processed_chunk("processed", "filtered", 1002.0)
        
        # Test summary
        summary = debug_info.get_summary()
        assert "raw_chunks_count" in summary
        assert "processed_chunks_count" in summary
        assert "raw_content" in summary
        assert "processed_content" in summary
        
        # Test timing info exists
        assert len(debug_info.timing_info) > 0
        assert debug_info.total_raw_chars > 0
        assert debug_info.total_processed_chars > 0
    
    def test_validator_instance_creation(self):
        """Test that validator can be instantiated without errors."""
        # Test that get_validator() returns a validator instance
        validator = get_validator()
        assert validator is not None
        assert hasattr(validator, 'validate_config')
        assert hasattr(validator, 'detect_tool_call')
        assert hasattr(validator, 'filter_content')
    
    def test_model_schema_generation(self):
        """Test that models generate proper JSON schemas."""
        config_schema = ConfigValidationResult.model_json_schema()
        assert "properties" in config_schema
        assert "api_base" in config_schema["properties"]
        assert "temperature" in config_schema["properties"]
        
        detection_schema = ToolCallDetection.model_json_schema()
        assert "properties" in detection_schema
        assert "is_tool_call" in detection_schema["properties"]
        assert "should_filter" in detection_schema["properties"]
    
    def test_content_filter_result_logic(self):
        """Test ContentFilterResult logic."""
        # Test filtered content
        filtered = ContentFilterResult(
            original_content="tool call json",
            filtered_content="",
            was_filtered=True,
            confidence=0.9,
            filter_reason="Contains tool call pattern"
        )
        assert filtered.was_filtered == True
        assert filtered.filtered_content == ""
        assert filtered.filter_reason is not None
        
        # Test unfiltered content
        unfiltered = ContentFilterResult(
            original_content="normal content",
            filtered_content="normal content",
            was_filtered=False,
            confidence=0.1
        )
        assert unfiltered.was_filtered == False
        assert unfiltered.filtered_content == "normal content"
        assert unfiltered.filter_reason is None
    
    def test_streaming_chunk_display_logic(self):
        """Test StreamingChunk display logic."""
        # Test text chunk (should display)
        text_chunk = StreamingChunk(
            content="hello world",
            chunk_type="text",
            should_display=True
        )
        assert text_chunk.should_display == True
        
        # Test tool call chunk (should not display)
        tool_chunk = StreamingChunk(
            content="tool call",
            chunk_type="tool_call",
            should_display=False
        )
        assert tool_chunk.should_display == False
        
        # Test filtered chunk (should not display)
        filtered_chunk = StreamingChunk(
            content="filtered",
            chunk_type="filtered",
            should_display=False
        )
        assert filtered_chunk.should_display == False