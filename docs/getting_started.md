# 🚀 Getting Started with Kebogyro

Welcome! Here's how to get up and running with `kebogyro` in under 5 minutes.

---

## ✅ Requirements

* Python 3.10+
* A supported LLM provider API key (e.g. OpenRouter, OpenAI)

---

## 📦 Install

```bash
pip install ./src/kebogyro
```

---

## ⚙️ Minimal Setup

### 1. Define a Simple Tool

```python
from kebogyro.utils import SimpleTool

def greet(name: str) -> str:
    return f"Hello, {name}!"

greet_tool = SimpleTool.from_fn(
    name="greet",
    description="Greet the user by name",
    fn=greet
)
```

### 2. Create a LLM Client

```python
from kebogyro.wrapper import LLMClientWrapper

llm = LLMClientWrapper(
    provider="openrouter",
    model_name="mistralai/mistral-7b-instruct",
    model_info={"api_key": "sk-..."},
    additional_tools=[greet_tool]
)
```

### 3. Create the Agent

```python
from kebogyro.agent_executor import create_agent

agent = create_agent(
    llm_client=llm,
    tools=[greet_tool],
    mcp_tools=None,
    system_prompt="You're a greeting agent.",
    stream=False
)
```

### 4. Run It

```python
response = await agent.ainvoke({"input": "Greet Lantip."})
print(response)
```

---

## 🧱 Optional: Use MCP + Caching

```python
from kebogyro.mcp_adapter.client import BBServerMCPClient
from kebogyro.cache import AbstractLLMCache

class MyCache(AbstractLLMCache):
    async def aget_value(self, key): ...
    async def aset_value(self, key, value, expiry_seconds): ...
    async def adelete_value(self, key): ...
    async def is_expired(self, key, expiry_seconds): ...

mcp = BBServerMCPClient(
    connections={
        "tools": {
            "url": "http://localhost:5000/.../sse",
            "transport": "sse"
        }
    },
    cache_adapter=MyCache()
)
```

Pass `mcp_tools=mcp` when calling `create_agent`.

---

Next → [LLMClientWrapper](./llm_wrapper.md)
