import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


class TestSessionManagerNonOllama:
    """Tests for session manager with non-Ollama providers."""

    def test_session_manager_uses_regular_client_for_non_ollama(self):
        """Test that session manager uses regular LLMClientWrapper for non-Ollama providers."""
        from web_ui.session_manager import SessionManager
        
        # Mock config for non-Ollama provider
        mock_config = MagicMock()
        mock_config.llm_provider = "openai"
        mock_config.model_name = "gpt-4"
        mock_config.api_key = "test-key"
        mock_config.llm_temperature = 0.1
        mock_config.get_llm_config.return_value = {"api_key": "test-key", "temperature": 0.1}
        
        with patch('web_ui.session_manager.LLMClientWrapper') as mock_wrapper:
            with patch('web_ui.session_manager.OllamaAdapter') as mock_adapter_class:
                mock_adapter_class.is_ollama_provider.return_value = False
                
                session_manager = SessionManager(mock_config)
                client = session_manager.get_chat_client()
                
                # Verify regular LLMClientWrapper was used
                mock_wrapper.assert_called_once_with(
                    provider="openai",
                    model_name="gpt-4",
                    model_info={"api_key": "test-key", "temperature": 0.1},
                    system_prompt="You are a helpful AI assistant."
                )
                
                # Verify OllamaAdapter was not created
                mock_adapter_class.assert_not_called()

    def test_session_manager_client_info_for_non_ollama(self):
        """Test that get_client_info returns correct info for non-Ollama providers."""
        from web_ui.session_manager import SessionManager
        
        # Mock config for non-Ollama provider
        mock_config = MagicMock()
        mock_config.llm_provider = "anthropic"
        mock_config.model_name = "claude-3"
        
        with patch('web_ui.session_manager.LLMClientWrapper'):
            with patch('web_ui.session_manager.OllamaAdapter') as mock_adapter_class:
                mock_adapter_class.is_ollama_provider.return_value = False
                
                session_manager = SessionManager(mock_config)
                info = session_manager.get_client_info()
                
                assert info["provider"] == "anthropic"
                assert info["model"] == "claude-3"
                assert info["is_ollama"] is False
                assert "ollama_base_url" not in info

    def test_session_manager_validation_for_non_ollama(self):
        """Test that validate_connection returns generic response for non-Ollama providers."""
        from web_ui.session_manager import SessionManager
        
        # Mock config for non-Ollama provider
        mock_config = MagicMock()
        mock_config.llm_provider = "openai"
        mock_config.model_name = "gpt-4"
        
        with patch('web_ui.session_manager.LLMClientWrapper'):
            with patch('web_ui.session_manager.OllamaAdapter') as mock_adapter_class:
                mock_adapter_class.is_ollama_provider.return_value = False
                
                session_manager = SessionManager(mock_config)
                result = session_manager.validate_connection()
                
                assert result["status"] == "unknown"
                assert "Connection validation not implemented" in result["message"]

    def test_session_manager_get_models_for_non_ollama(self):
        """Test that get_available_models returns empty list for non-Ollama providers."""
        from web_ui.session_manager import SessionManager
        
        # Mock config for non-Ollama provider
        mock_config = MagicMock()
        mock_config.llm_provider = "openai"
        mock_config.model_name = "gpt-4"
        
        with patch('web_ui.session_manager.LLMClientWrapper'):
            with patch('web_ui.session_manager.OllamaAdapter') as mock_adapter_class:
                mock_adapter_class.is_ollama_provider.return_value = False
                
                session_manager = SessionManager(mock_config)
                models = session_manager.get_available_models()
                
                assert models == []