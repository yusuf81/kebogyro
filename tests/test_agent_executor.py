import pytest
from kebogyro.wrapper import LLMClientWrapper
from kebogyro.agent_executor import create_agent
from kebogyro.mcp_adapter.tools import SimpleTool

@pytest.mark.asyncio
async def test_create_agent_runs():
    def mock_tool(x: int) -> int:
        return x * 2

    tool = SimpleTool.from_fn("doubler", "Doubles a number", mock_tool)
    llm = LLMClientWrapper(
        provider="openrouter",
        model_name="mistralai/mistral-7b-instruct",
        model_info={"api_key": "test-key"},
        additional_tools=[tool]
    )

    agent = create_agent(
        llm_client=llm,
        tools=[tool],
        mcp_tools=None,
        system_prompt="Act as a multiplier",
        stream=False
    )

    assert agent.llm_client == llm
    assert agent.system_prompt == "Act as a multiplier"
