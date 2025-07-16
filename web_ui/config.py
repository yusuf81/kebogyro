"""Configuration management for web UI."""

import os
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    missing_vars: List[str]
    errors: List[str]


class ConfigManager:
    """Manages web UI configuration with validation and defaults."""
    
    # Required environment variables
    REQUIRED_VARS = [
        "OPENAI_API_BASE",
        "OPENAI_API_KEY", 
        "KBG_OLLAMA_MODEL"
    ]
    
    # Default values
    DEFAULTS = {
        "KBG_LLM_PROVIDER": "ollama",
        "KBG_LLM_TEMPERATURE": "0.1"
    }
    
    def __init__(self):
        """Initialize configuration manager."""
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables."""
        # Basic required variables
        self.api_base = os.getenv("OPENAI_API_BASE")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("KBG_OLLAMA_MODEL")
        
        # Optional variables with defaults
        self.llm_provider = os.getenv("KBG_LLM_PROVIDER", self.DEFAULTS["KBG_LLM_PROVIDER"])
        
        # Handle temperature conversion
        temp_str = os.getenv("KBG_LLM_TEMPERATURE", self.DEFAULTS["KBG_LLM_TEMPERATURE"])
        try:
            self.llm_temperature = float(temp_str)
        except ValueError:
            raise ConfigValidationError(f"Invalid temperature value: {temp_str}. Must be a number.")
        
        # Validate temperature range
        if not (0.0 <= self.llm_temperature <= 2.0):
            raise ConfigValidationError(f"Temperature must be between 0.0 and 2.0, got: {self.llm_temperature}")
    
    def validate(self) -> ValidationResult:
        """Validate current configuration."""
        missing_vars = []
        errors = []
        
        # Check required variables
        for var in self.REQUIRED_VARS:
            if not os.getenv(var):
                missing_vars.append(var)
        
        # Check API base URL format
        if self.api_base and not self.api_base.startswith(("http://", "https://")):
            errors.append("OPENAI_API_BASE must start with http:// or https://")
        
        is_valid = len(missing_vars) == 0 and len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            missing_vars=missing_vars,
            errors=errors
        )
    
    def get_display_config(self) -> dict:
        """Get configuration for display in UI (with sensitive data masked)."""
        return {
            "OPENAI_API_BASE": self.api_base or "Not set",
            "KBG_OLLAMA_MODEL": self.model_name or "Not set",
            "OPENAI_API_KEY": "***" if self.api_key else "Not set",
            "KBG_LLM_PROVIDER": self.llm_provider,
            "KBG_LLM_TEMPERATURE": str(self.llm_temperature)
        }
    
    def get_llm_config(self) -> dict:
        """Get configuration for LLM client."""
        return {
            "api_key": self.api_key,
            "temperature": self.llm_temperature
        }
    
    @classmethod
    def load_from_env_file(cls, env_path: Optional[Path] = None) -> "ConfigManager":
        """Load configuration from .env file."""
        if env_path is None:
            env_path = Path.cwd() / ".env"
        
        if env_path.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_path)
            except ImportError:
                # python-dotenv not available, skip loading
                pass
        
        return cls()