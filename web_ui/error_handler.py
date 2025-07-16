"""Centralized error handling for web UI."""

import logging
import re
from typing import Union, Optional
from dataclasses import dataclass
from pathlib import Path


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when there's a configuration error."""
    pass


@dataclass
class ErrorResponse:
    """Structured error response."""
    user_message: str
    is_user_facing: bool
    should_log: bool
    should_retry: bool = False
    error_type: str = "generic"


class ErrorHandler:
    """Centralized error handling with user-friendly messages."""
    
    # Patterns to remove sensitive information
    SENSITIVE_PATTERNS = [
        r'sk-[a-zA-Z0-9]{48}',  # OpenAI API keys
        r'api[_-]?key[\'"\s:=]+[a-zA-Z0-9]+',  # Generic API keys
        r'token[\'"\s:=]+[a-zA-Z0-9]+',  # Tokens
        r'password[\'"\s:=]+\w+',  # Passwords
        r'secret[\'"\s:=]+\w+',  # Secrets
    ]
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = logger
    
    def handle_llm_error(self, error: Exception) -> ErrorResponse:
        """Handle LLM-related errors."""
        error_str = str(error).lower()
        
        # Connection errors
        if any(word in error_str for word in ["connection", "refused", "timeout", "unreachable"]):
            return ErrorResponse(
                user_message="Cannot connect to LLM service. Please check your configuration.",
                is_user_facing=True,
                should_log=True,
                should_retry=True,
                error_type="connection"
            )
        
        # Authentication errors
        if any(word in error_str for word in ["authentication", "unauthorized", "invalid api key"]):
            return ErrorResponse(
                user_message="Authentication failed. Please check your API key configuration.",
                is_user_facing=True,
                should_log=True,
                error_type="authentication"
            )
        
        # Rate limiting
        if any(word in error_str for word in ["rate limit", "quota", "too many requests"]):
            return ErrorResponse(
                user_message="Rate limit exceeded. Please try again later.",
                is_user_facing=True,
                should_log=True,
                should_retry=True,
                error_type="rate_limit"
            )
        
        # Generic LLM error
        self.logger.error(f"LLM error: {error}")
        return ErrorResponse(
            user_message="LLM service encountered an error. Please try again.",
            is_user_facing=True,
            should_log=True,
            should_retry=True,
            error_type="llm_error"
        )
    
    def handle_configuration_error(self, error: Union[ConfigurationError, Exception]) -> ErrorResponse:
        """Handle configuration errors."""
        error_str = str(error)
        
        # Don't log configuration errors as they're user-fixable
        if "temperature" in error_str.lower():
            return ErrorResponse(
                user_message="Invalid temperature configuration. Please check your settings.",
                is_user_facing=True,
                should_log=False,
                error_type="configuration"
            )
        
        return ErrorResponse(
            user_message=f"Configuration error: {self._sanitize_error_message(error_str)}",
            is_user_facing=True,
            should_log=False,
            error_type="configuration"
        )
    
    def handle_streaming_error(self, error: Exception) -> ErrorResponse:
        """Handle streaming-specific errors."""
        self.logger.error(f"Streaming error: {error}")
        
        return ErrorResponse(
            user_message="Streaming was interrupted. Please try again.",
            is_user_facing=True,
            should_log=True,
            should_retry=True,
            error_type="streaming"
        )
    
    def handle_generic_error(self, error: Exception) -> ErrorResponse:
        """Handle generic errors."""
        # Log the full error for debugging
        self.logger.error(f"Generic error: {error}")
        
        return ErrorResponse(
            user_message="An unexpected error occurred. Please try again.",
            is_user_facing=True,
            should_log=True,
            error_type="generic"
        )
    
    def _sanitize_error_message(self, message: str) -> str:
        """Remove sensitive information from error messages."""
        sanitized = message
        
        for pattern in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def format_error_for_ui(self, error_response: ErrorResponse) -> str:
        """Format error response for display in UI."""
        if error_response.should_retry:
            return f"⚠️ {error_response.user_message} You can try again."
        else:
            return f"❌ {error_response.user_message}"