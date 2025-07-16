import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any


class TestSessionManager:
    """Tests for session management and LLM client lifecycle."""

    def test_session_manager_creates_client_with_correct_config(self):
        """Test that session manager creates LLM client with correct configuration."""
        from web_ui.session_manager import SessionManager
        from web_ui.config import ConfigManager
        
        # Mock config
        mock_config = MagicMock()
        mock_config.llm_provider = "ollama"
        mock_config.model_name = "llama3"
        mock_config.api_key = "test-key"
        mock_config.llm_temperature = 0.1
        mock_config.api_base = "http://localhost:11434/v1"
        mock_config.get_llm_config.return_value = {"api_key": "test-key", "temperature": 0.1}
        
        with patch('web_ui.session_manager.OllamaAdapter') as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter_class.is_ollama_provider.return_value = True
            
            session_manager = SessionManager(mock_config)
            client = session_manager.get_chat_client()
            
            # Verify OllamaAdapter was used for ollama provider
            mock_adapter_class.assert_called_once_with(mock_config)
            mock_adapter.create_llm_client.assert_called_once_with(
                system_prompt="You are a helpful AI assistant."
            )

    def test_session_manager_reuses_client_instance(self):
        """Test that session manager reuses the same client instance."""
        from web_ui.session_manager import SessionManager
        
        mock_config = MagicMock()
        mock_config.llm_provider = "ollama"
        mock_config.model_name = "llama3"
        mock_config.api_key = "test-key"
        mock_config.llm_temperature = 0.1
        mock_config.get_llm_config.return_value = {"api_key": "test-key", "temperature": 0.1}
        
        with patch('web_ui.session_manager.OllamaAdapter') as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter_class.is_ollama_provider.return_value = True
            
            session_manager = SessionManager(mock_config)
            
            client1 = session_manager.get_chat_client()
            client2 = session_manager.get_chat_client()
            
            assert client1 is client2
            # Should only be called once because of caching
            assert mock_adapter.create_llm_client.call_count == 1

    def test_session_manager_creates_code_client_with_tools(self):
        """Test that session manager creates code assistance client with tools."""
        from web_ui.session_manager import SessionManager
        
        mock_config = MagicMock()
        mock_config.llm_provider = "ollama"
        mock_config.model_name = "llama3"
        mock_config.api_key = "test-key"
        mock_config.llm_temperature = 0.1
        mock_config.get_llm_config.return_value = {"api_key": "test-key", "temperature": 0.1}
        
        with patch('web_ui.session_manager.OllamaAdapter') as mock_adapter_class:
            with patch('web_ui.session_manager.code_assistant_tool') as mock_tool:
                mock_adapter = MagicMock()
                mock_adapter_class.return_value = mock_adapter
                mock_adapter_class.is_ollama_provider.return_value = True
                
                session_manager = SessionManager(mock_config)
                client = session_manager.get_code_assistance_client()
                
                # Check that the client was created with the tool
                call_args = mock_adapter.create_llm_client.call_args
                assert 'additional_tools' in call_args.kwargs
                assert mock_tool in call_args.kwargs['additional_tools']

    def test_session_manager_handles_client_creation_failure(self):
        """Test that session manager handles client creation failures."""
        from web_ui.session_manager import SessionManager, SessionCreationError
        
        mock_config = MagicMock()
        mock_config.llm_provider = "ollama"
        mock_config.model_name = "llama3"
        mock_config.api_key = "test-key"
        mock_config.llm_temperature = 0.1
        mock_config.get_llm_config.return_value = {"api_key": "test-key", "temperature": 0.1}
        
        with patch('web_ui.session_manager.OllamaAdapter') as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter_class.is_ollama_provider.return_value = True
            mock_adapter.create_llm_client.side_effect = Exception("Connection failed")
            
            session_manager = SessionManager(mock_config)
            
            with pytest.raises(SessionCreationError) as exc_info:
                session_manager.get_chat_client()
            
            assert "Connection failed" in str(exc_info.value)

    def test_session_manager_invalidates_client_on_error(self):
        """Test that session manager invalidates client cache on error."""
        from web_ui.session_manager import SessionManager
        
        mock_config = MagicMock()
        mock_config.llm_provider = "ollama"
        mock_config.model_name = "llama3"
        mock_config.api_key = "test-key"
        mock_config.llm_temperature = 0.1
        mock_config.get_llm_config.return_value = {"api_key": "test-key", "temperature": 0.1}
        
        with patch('web_ui.session_manager.OllamaAdapter') as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter_class.return_value = mock_adapter
            mock_adapter_class.is_ollama_provider.return_value = True
            # Configure mock to return different instances
            mock_adapter.create_llm_client.side_effect = [MagicMock(), MagicMock()]
            
            session_manager = SessionManager(mock_config)
            
            # First call succeeds
            client1 = session_manager.get_chat_client()
            
            # Simulate an error that should invalidate the client
            session_manager.invalidate_clients()
            
            # Second call should create a new client
            client2 = session_manager.get_chat_client()
            
            assert client1 is not client2
            assert mock_adapter.create_llm_client.call_count == 2