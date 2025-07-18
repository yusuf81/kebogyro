"""Configuration management for web UI with Outlines validation."""

import os
import hashlib
from typing import Optional
from pathlib import Path

from .outlines_validator import get_validator
from .outlines_models import ConfigValidationResult


class ConfigManager:
    """Manages web UI configuration with Outlines validation."""
    
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
        # Cache for validation results
        self._validation_cache = {}
        self._config_hash = None
    
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
            # Use default temperature if conversion fails
            self.llm_temperature = 0.1
    
    def _get_config_hash(self) -> str:
        """Get hash of current configuration for caching."""
        config_str = f"{self.api_base}|{self.api_key}|{self.model_name}|{self.llm_temperature}|{self.llm_provider}"
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def validate(self) -> ConfigValidationResult:
        """Validate configuration using Outlines structured generation with caching."""
        # Check if config has changed
        current_hash = self._get_config_hash()
        
        # Return cached result if config hasn't changed
        if current_hash == self._config_hash and current_hash in self._validation_cache:
            return self._validation_cache[current_hash]
        
        # Prepare config data for validation
        config_data = {
            "api_base": self.api_base,
            "api_key": self.api_key,
            "model_name": self.model_name,
            "temperature": self.llm_temperature,
            "provider": self.llm_provider
        }
        
        # Use Outlines validator (replaces manual validation spaghetti)
        validator = get_validator()
        result = validator.validate_config(config_data)
        
        # Cache the result
        self._validation_cache[current_hash] = result
        self._config_hash = current_hash
        
        return result
    
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


# Backward compatibility - keep old exception for existing code
class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


# Backward compatibility - keep old ValidationResult for existing code
class ValidationResult:
    """Legacy validation result for backward compatibility."""
    def __init__(self, config_result: ConfigValidationResult):
        self.is_valid = config_result.status == "valid"
        self.missing_vars = []
        self.errors = config_result.errors
        
        # Check for missing variables
        if not config_result.api_base:
            self.missing_vars.append("OPENAI_API_BASE")
        if not config_result.api_key or config_result.api_key == "***":
            self.missing_vars.append("OPENAI_API_KEY")
        if not config_result.model_name:
            self.missing_vars.append("KBG_OLLAMA_MODEL")
        
        # Update validity based on missing vars
        if self.missing_vars:
            self.is_valid = False