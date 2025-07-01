from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Optional, Union

class LLMClientConfig(BaseModel):
    base_urls: Dict[str, HttpUrl] = Field(
        default_factory=lambda: {
            "openrouter": HttpUrl("https://openrouter.ai/api/v1"),
            "anthropic": HttpUrl("https://api.anthropic.com/v1/"),
            "cerebras": HttpUrl("https://api.cerebras.ai/v1"),
            "groq": HttpUrl("https://api.groq.ai/openai/v1"),
            "requesty": HttpUrl("https://router.requesty.ai/v1")
        }
    )
    google_default_base_url: HttpUrl = HttpUrl("https://generativelanguage.googleapis.com/v1beta/openai/")

_llm_config = LLMClientConfig()

def get_base_url(provider: str) -> Optional[str]:
    base_url_obj = _llm_config.base_urls.get(provider)
    if base_url_obj:
        return str(base_url_obj)
    if "google" in provider.lower():
        return str(_llm_config.google_default_base_url)
    
    return None