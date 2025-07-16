"""Session management for LLM clients."""

import logging
from typing import Optional, Dict, Any
from kebogyro.wrapper import LLMClientWrapper
from web_ui.config import ConfigManager
from web_ui.tools import code_assistant_tool
from web_ui.ollama_adapter import OllamaAdapter


logger = logging.getLogger(__name__)


class SessionCreationError(Exception):
    """Raised when session creation fails."""
    pass


class SessionManager:
    """Manages LLM client sessions with caching and lifecycle management."""
    
    def __init__(self, config: ConfigManager):
        """Initialize session manager with configuration."""
        self.config = config
        self._chat_client: Optional[LLMClientWrapper] = None
        self._code_client: Optional[LLMClientWrapper] = None
        self._clients_invalidated = False
        
        # Initialize adapter untuk Ollama jika diperlukan
        self.ollama_adapter = None
        if OllamaAdapter.is_ollama_provider(config.llm_provider):
            self.ollama_adapter = OllamaAdapter(config)
    
    def get_chat_client(self) -> LLMClientWrapper:
        """Get or create chat client."""
        if self._chat_client is None or self._clients_invalidated:
            try:
                self._chat_client = self._create_chat_client()
                self._clients_invalidated = False
            except Exception as e:
                logger.error(f"Failed to create chat client: {e}")
                raise SessionCreationError(f"Failed to create chat client: {e}")
        
        return self._chat_client
    
    def get_code_assistance_client(self) -> LLMClientWrapper:
        """Get or create code assistance client with tools."""
        if self._code_client is None or self._clients_invalidated:
            try:
                self._code_client = self._create_code_assistance_client()
                self._clients_invalidated = False
            except Exception as e:
                logger.error(f"Failed to create code assistance client: {e}")
                raise SessionCreationError(f"Failed to create code assistance client: {e}")
        
        return self._code_client
    
    def invalidate_clients(self):
        """Invalidate cached clients, forcing recreation on next access."""
        self._clients_invalidated = True
        self._chat_client = None
        self._code_client = None
        logger.info("Client cache invalidated")
    
    def validate_connection(self) -> Dict[str, Any]:
        """Validate connection to LLM provider."""
        if self.ollama_adapter:
            return self.ollama_adapter.validate_ollama_connection()
        else:
            return {
                "status": "unknown",
                "message": "Connection validation not implemented for this provider"
            }
    
    def get_available_models(self) -> list:
        """Get list of available models from provider."""
        if self.ollama_adapter:
            return self.ollama_adapter.get_available_models()
        else:
            return []
    
    def _create_chat_client(self) -> LLMClientWrapper:
        """Create new chat client instance."""
        if self.ollama_adapter:
            return self.ollama_adapter.create_llm_client(
                system_prompt="You are a helpful AI assistant."
            )
        
        return LLMClientWrapper(
            provider=self.config.llm_provider,
            model_name=self.config.model_name,
            model_info=self.config.get_llm_config(),
            system_prompt="You are a helpful AI assistant."
        )
    
    def _create_code_assistance_client(self) -> LLMClientWrapper:
        """Create new code assistance client instance with tools."""
        system_prompt = (
            "You are a helpful AI code assistant. "
            "When appropriate, use the 'code_assistant_tool' to help with code generation, "
            "completion, or explanation. Provide answers primarily in code blocks if generating code."
        )
        
        if self.ollama_adapter:
            return self.ollama_adapter.create_llm_client(
                system_prompt=system_prompt,
                additional_tools=[code_assistant_tool]
            )
        
        return LLMClientWrapper(
            provider=self.config.llm_provider,
            model_name=self.config.model_name,
            model_info=self.config.get_llm_config(),
            system_prompt=system_prompt,
            additional_tools=[code_assistant_tool]
        )
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get information about current clients."""
        info = {
            "chat_client_active": self._chat_client is not None,
            "code_client_active": self._code_client is not None,
            "clients_invalidated": self._clients_invalidated,
            "provider": self.config.llm_provider,
            "model": self.config.model_name
        }
        
        # Add Ollama-specific info if applicable
        if self.ollama_adapter:
            info["ollama_base_url"] = self.ollama_adapter.get_ollama_base_url()
            info["is_ollama"] = True
        else:
            info["is_ollama"] = False
            
        return info