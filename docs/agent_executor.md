# 🎭 Agent Executor

Use `create_agent()` to wire up your LLM, tools, and optional MCP connection into a single callable agent.

---

## 🔧 Function Signature

```python
def create_agent(
    llm_client: LLMClientWrapper,
    tools: Optional[List[SimpleTool]],
    mcp_tools: Optional[BBServerMCPClient],
    system_prompt: str,
    stream: bool
) -> BBAgentExecutor:
```

---

## 📦 Example

```python
from kebogyro.agent_executor import create_agent

agent = create_agent(
    llm_client=llm,
    tools=[my_tool],
    mcp_tools=mcp_client,
    system_prompt="You're a debugging assistant.",
    stream=True
)

response = await agent.ainvoke({"input": "Diagnose my Python bug."})
```

---

## 💡 Notes

* `stream=True` enables partial token streaming.
* All arguments optional except `llm_client` and `system_prompt`.
* Combine LLM + tool logic + remote orchestration in one step.

---

Next → [Caching](./caching.md)
