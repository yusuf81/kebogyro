import pytest
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any


class TestWebUIConfig:
    """Tests for web UI configuration management."""

    def test_config_validates_required_environment_variables(self):
        """Test that config validation identifies missing required variables."""
        # We'll create a ConfigManager class in web_ui/config.py
        from web_ui.config import ConfigManager
        
        # Test missing variables - this should create config with defaults
        with patch.dict(os.environ, {}, clear=True):
            config = ConfigManager()
            
            # Check that defaults are used when environment is empty
            assert config.api_base is None
            assert config.api_key is None
            assert config.model_name is None
            assert config.llm_provider == "ollama"  # Default
            assert config.llm_temperature == 0.1  # Default

    def test_config_validates_with_all_required_variables(self):
        """Test that config validation passes with all required variables."""
        from web_ui.config import ConfigManager
        
        required_env = {
            "OPENAI_API_BASE": "http://localhost:11434/v1",
            "OPENAI_API_KEY": "ollama",
            "KBG_OLLAMA_MODEL": "llama3",
            "KBG_LLM_PROVIDER": "ollama",
            "KBG_LLM_TEMPERATURE": "0.1"
        }
        
        with patch.dict(os.environ, required_env, clear=True):
            config = ConfigManager()
            
            # Check that all variables are loaded correctly
            assert config.api_base == "http://localhost:11434/v1"
            assert config.api_key == "ollama"
            assert config.model_name == "llama3"
            assert config.llm_provider == "ollama"
            assert config.llm_temperature == 0.1

    def test_config_provides_default_values(self):
        """Test that config provides sensible defaults."""
        from web_ui.config import ConfigManager
        
        minimal_env = {
            "OPENAI_API_BASE": "http://localhost:11434/v1",
            "OPENAI_API_KEY": "ollama",
            "KBG_OLLAMA_MODEL": "llama3"
        }
        
        with patch.dict(os.environ, minimal_env, clear=True):
            config = ConfigManager()
            
            assert config.llm_provider == "ollama"  # default
            assert config.llm_temperature == 0.1  # default
            assert config.api_base == "http://localhost:11434/v1"
            assert config.api_key == "ollama"
            assert config.model_name == "llama3"

    def test_config_handles_type_conversion(self):
        """Test that config handles type conversion correctly."""
        from web_ui.config import ConfigManager
        
        env_with_types = {
            "OPENAI_API_BASE": "http://localhost:11434/v1",
            "OPENAI_API_KEY": "ollama",
            "KBG_OLLAMA_MODEL": "llama3",
            "KBG_LLM_TEMPERATURE": "0.5"  # string that should be converted to float
        }
        
        with patch.dict(os.environ, env_with_types, clear=True):
            config = ConfigManager()
            
            assert isinstance(config.llm_temperature, float)
            assert config.llm_temperature == 0.5

    def test_config_handles_invalid_temperature(self):
        """Test that config handles invalid temperature values by using default."""
        from web_ui.config import ConfigManager
        
        env_with_invalid_temp = {
            "OPENAI_API_BASE": "http://localhost:11434/v1",
            "OPENAI_API_KEY": "ollama",
            "KBG_OLLAMA_MODEL": "llama3",
            "KBG_LLM_TEMPERATURE": "invalid"
        }
        
        with patch.dict(os.environ, env_with_invalid_temp, clear=True):
            # Should not raise error, but use default temperature
            config = ConfigManager()
            assert config.llm_temperature == 0.1  # Default temperature