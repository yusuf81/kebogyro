"""Adapter untuk integrasi Ollama dengan Kebogyro."""

import os
from typing import Optional, Dict, Any
from kebogyro.wrapper import LLMClientWrapper
from kebogyro.config import get_base_url, _llm_config
from web_ui.config import ConfigManager


class OllamaAdapter:
    """Adapter untuk mengintegrasikan Ollama dengan Kebogyro."""
    
    def __init__(self, config: ConfigManager):
        """Initialize adapter dengan konfigurasi."""
        self.config = config
    
    def get_ollama_base_url(self) -> Optional[str]:
        """Get base URL untuk Ollama dari environment variable atau default."""
        # Prioritas: OPENAI_API_BASE env var, kemudian fallback ke default
        return self.config.api_base or "http://localhost:11434/v1"
    
    def create_llm_client(self, system_prompt: str, additional_tools: list = None) -> LLMClientWrapper:
        """Create LLM client dengan konfigurasi yang disesuaikan untuk Ollama."""
        # Untuk Ollama, kita perlu menambahkan base_url ke konfigurasi global sementara
        ollama_base_url = self.get_ollama_base_url()
        
        # Temporarily add ollama to the global config
        original_ollama_url = _llm_config.base_urls.get("ollama")
        
        try:
            # Import pydantic HttpUrl
            from pydantic import HttpUrl
            
            # Add ollama to the global config temporarily
            _llm_config.base_urls["ollama"] = HttpUrl(ollama_base_url)
            
            # Create the client
            model_info = self.config.get_llm_config().copy()
            
            return LLMClientWrapper(
                provider=self.config.llm_provider,
                model_name=self.config.model_name,
                model_info=model_info,
                system_prompt=system_prompt,
                additional_tools=additional_tools or []
            )
            
        finally:
            # Restore original state
            if original_ollama_url is not None:
                _llm_config.base_urls["ollama"] = original_ollama_url
            else:
                _llm_config.base_urls.pop("ollama", None)
    
    def validate_ollama_connection(self) -> Dict[str, Any]:
        """Validate koneksi ke Ollama server."""
        try:
            import httpx
            base_url = self.get_ollama_base_url()
            
            # Test connection dengan timeout
            with httpx.Client(timeout=5.0) as client:
                # Ollama biasanya memiliki endpoint /v1/models
                response = client.get(f"{base_url}/models")
                
                if response.status_code == 200:
                    return {
                        "status": "connected",
                        "base_url": base_url,
                        "message": "Successfully connected to Ollama server"
                    }
                else:
                    return {
                        "status": "error",
                        "base_url": base_url,
                        "message": f"Ollama server responded with status {response.status_code}"
                    }
        except Exception as e:
            return {
                "status": "error", 
                "base_url": self.get_ollama_base_url(),
                "message": f"Failed to connect to Ollama server: {str(e)}"
            }
    
    def get_available_models(self) -> list:
        """Get list of available models dari Ollama server."""
        try:
            import httpx
            base_url = self.get_ollama_base_url()
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{base_url}/models")
                
                if response.status_code == 200:
                    data = response.json()
                    # Ollama API structure might vary, adjust as needed
                    if "data" in data:
                        return [model["id"] for model in data["data"]]
                    elif "models" in data:
                        return [model["name"] for model in data["models"]]
                    else:
                        return []
                else:
                    return []
        except Exception:
            return []
    
    @staticmethod
    def is_ollama_provider(provider: str) -> bool:
        """Check if provider is Ollama."""
        return provider.lower() == "ollama"
    
    @staticmethod
    def get_default_ollama_config() -> Dict[str, str]:
        """Get default configuration for Ollama."""
        return {
            "OPENAI_API_BASE": "http://localhost:11434/v1",
            "OPENAI_API_KEY": "ollama", 
            "KBG_OLLAMA_MODEL": "llama3",
            "KBG_LLM_PROVIDER": "ollama",
            "KBG_LLM_TEMPERATURE": "0.1"
        }