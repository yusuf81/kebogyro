import pytest
from kebogyro.wrapper import LLMClientWrapper

@pytest.mark.asyncio
async def test_llm_wrapper_basic_init():
    llm = LLMClientWrapper(
        provider="openrouter",
        model_name="mistralai/mistral-7b-instruct",
        model_info={"api_key": "sk-test"}
    )
    assert llm.model_name == "mistralai/mistral-7b-instruct"
    assert llm.provider == "openrouter"
