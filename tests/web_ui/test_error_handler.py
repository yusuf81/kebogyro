import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


class TestErrorHandler:
    """Tests for centralized error handling."""

    def test_error_handler_formats_user_friendly_messages(self):
        """Test that error handler creates user-friendly error messages."""
        from web_ui.error_handler import ErrorHandler
        
        handler = ErrorHandler()
        
        # Test LLM connection error
        llm_error = Exception("Connection refused")
        result = handler.handle_llm_error(llm_error)
        
        assert result.user_message == "Cannot connect to LLM service. Please check your configuration."
        assert result.is_user_facing is True
        assert result.should_log is True

    def test_error_handler_handles_configuration_errors(self):
        """Test that error handler handles configuration errors appropriately."""
        from web_ui.error_handler import ErrorHandler, ConfigurationError
        
        handler = ErrorHandler()
        
        config_error = ConfigurationError("OPENAI_API_BASE not set")
        result = handler.handle_configuration_error(config_error)
        
        assert "configuration" in result.user_message.lower()
        assert result.is_user_facing is True
        assert result.should_log is False  # config errors shouldn't spam logs

    def test_error_handler_sanitizes_sensitive_information(self):
        """Test that error handler removes sensitive information from error messages."""
        from web_ui.error_handler import ErrorHandler
        
        handler = ErrorHandler()
        
        # Test error with API key in message
        sensitive_error = Exception("API key 'sk-1234567890abcdef' is invalid")
        result = handler.handle_generic_error(sensitive_error)
        
        assert "sk-1234567890abcdef" not in result.user_message
        assert "API key" not in result.user_message
        assert result.user_message == "An unexpected error occurred. Please try again."

    def test_error_handler_logs_full_error_details(self):
        """Test that error handler logs full error details for debugging."""
        from web_ui.error_handler import ErrorHandler
        
        handler = ErrorHandler()
        
        with patch.object(handler, 'logger') as mock_logger:
            error = Exception("Detailed error message")
            handler.handle_generic_error(error)
            
            mock_logger.error.assert_called_once()
            # Check that the logged message contains the full error
            logged_message = mock_logger.error.call_args[0][0]
            assert "Detailed error message" in logged_message

    def test_error_handler_handles_streaming_errors(self):
        """Test that error handler handles streaming-specific errors."""
        from web_ui.error_handler import ErrorHandler
        
        handler = ErrorHandler()
        
        streaming_error = Exception("Stream interrupted")
        result = handler.handle_streaming_error(streaming_error)
        
        assert "streaming" in result.user_message.lower()
        assert result.is_user_facing is True
        assert result.should_retry is True