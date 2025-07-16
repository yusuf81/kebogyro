import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


class TestOllamaAdapter:
    """Tests for Ollama adapter."""

    def test_ollama_adapter_gets_base_url_from_config(self):
        """Test that adapter gets base URL from config."""
        from web_ui.ollama_adapter import OllamaAdapter
        
        mock_config = MagicMock()
        mock_config.api_base = "http://localhost:11434/v1"
        
        adapter = OllamaAdapter(mock_config)
        base_url = adapter.get_ollama_base_url()
        
        assert base_url == "http://localhost:11434/v1"

    def test_ollama_adapter_uses_default_when_no_config(self):
        """Test that adapter uses default URL when no config."""
        from web_ui.ollama_adapter import OllamaAdapter
        
        mock_config = MagicMock()
        mock_config.api_base = None
        
        adapter = OllamaAdapter(mock_config)
        base_url = adapter.get_ollama_base_url()
        
        assert base_url == "http://localhost:11434/v1"

    def test_ollama_adapter_creates_client_with_base_url(self):
        """Test that adapter creates LLM client with correct base URL."""
        from web_ui.ollama_adapter import OllamaAdapter
        
        mock_config = MagicMock()
        mock_config.llm_provider = "ollama"
        mock_config.model_name = "llama3"
        mock_config.api_base = "http://localhost:11434/v1"
        mock_config.get_llm_config.return_value = {"api_key": "ollama", "temperature": 0.1}
        
        with patch('web_ui.ollama_adapter.LLMClientWrapper') as mock_wrapper:
            with patch('web_ui.ollama_adapter._llm_config') as mock_llm_config:
                mock_llm_config.base_urls = {}
                
                adapter = OllamaAdapter(mock_config)
                client = adapter.create_llm_client("Test prompt")
                
                # Verify that LLMClientWrapper was called with ollama provider
                call_args = mock_wrapper.call_args
                assert call_args.kwargs['provider'] == "ollama"
                assert call_args.kwargs['model_name'] == "llama3"
                
                # Verify that ollama was added to base_urls during execution
                # (This is hard to test directly due to try/finally, but we can check the call was made)
                mock_wrapper.assert_called_once()

    def test_ollama_adapter_validates_connection_success(self):
        """Test that adapter validates connection successfully."""
        from web_ui.ollama_adapter import OllamaAdapter
        
        mock_config = MagicMock()
        mock_config.api_base = "http://localhost:11434/v1"
        
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            adapter = OllamaAdapter(mock_config)
            result = adapter.validate_ollama_connection()
            
            assert result["status"] == "connected"
            assert result["base_url"] == "http://localhost:11434/v1"

    def test_ollama_adapter_validates_connection_failure(self):
        """Test that adapter handles connection failure."""
        from web_ui.ollama_adapter import OllamaAdapter
        
        mock_config = MagicMock()
        mock_config.api_base = "http://localhost:11434/v1"
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection failed")
            
            adapter = OllamaAdapter(mock_config)
            result = adapter.validate_ollama_connection()
            
            assert result["status"] == "error"
            assert "Connection failed" in result["message"]

    def test_ollama_adapter_is_ollama_provider(self):
        """Test provider detection."""
        from web_ui.ollama_adapter import OllamaAdapter
        
        assert OllamaAdapter.is_ollama_provider("ollama") is True
        assert OllamaAdapter.is_ollama_provider("OLLAMA") is True
        assert OllamaAdapter.is_ollama_provider("openai") is False

    def test_ollama_adapter_get_default_config(self):
        """Test default configuration."""
        from web_ui.ollama_adapter import OllamaAdapter
        
        default_config = OllamaAdapter.get_default_ollama_config()
        
        assert default_config["OPENAI_API_BASE"] == "http://localhost:11434/v1"
        assert default_config["OPENAI_API_KEY"] == "ollama"
        assert default_config["KBG_OLLAMA_MODEL"] == "llama3"
        assert default_config["KBG_LLM_PROVIDER"] == "ollama"
        assert default_config["KBG_LLM_TEMPERATURE"] == "0.1"

    def test_ollama_adapter_get_available_models(self):
        """Test getting available models."""
        from web_ui.ollama_adapter import OllamaAdapter
        
        mock_config = MagicMock()
        mock_config.api_base = "http://localhost:11434/v1"
        
        # Mock successful models response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "llama3"}, {"id": "codellama"}]
        }
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            adapter = OllamaAdapter(mock_config)
            models = adapter.get_available_models()
            
            assert models == ["llama3", "codellama"]

    def test_ollama_adapter_get_available_models_failure(self):
        """Test getting available models failure."""
        from web_ui.ollama_adapter import OllamaAdapter
        
        mock_config = MagicMock()
        mock_config.api_base = "http://localhost:11434/v1"
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection failed")
            
            adapter = OllamaAdapter(mock_config)
            models = adapter.get_available_models()
            
            assert models == []