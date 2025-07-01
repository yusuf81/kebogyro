# 🧙‍♂️ Kebogyro

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE.md) [![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/) [![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-org/kebogyro/actions) [![Coverage](https://img.shields.io/badge/coverage-90%25-green)](https://github.com/your-org/kebogyro)

> **An async-first, Javanese-coded LLM orchestration toolkit — made for geeks who speak tools.**

`kebogyro` is a Python package born from the union of 🛠️ **Gyro Gearloose’s mechanical genius** and 🎶 **Kebogiro**, the Javanese gamelan suite played in moments of ceremony, transition, and wonder.

Like its namesake, `kebogyro` is all about orchestrating — not music, but function calls, LLM responses, and microservice bridges. It's fast, extendable, and knows its way around a toolbench.

---

## 🎡 What's in a Name?

> "**Gyro**" = Gearloose-style inventiveness and tool-wrangling
> "**Kebo**" = Javanese for buffalo, symbolizing calm power, persistence, and resilience — qualities you want in long-running AI services ⚙️💡

Together: **Kebogyro** — a humble-yet-geeky orchestration layer that never breaks under load, and plays well with others.

---

## 🧬 Why Use `kebogyro`?

Because building LLM apps should be fast, flexible, and async-native:

* 🔁 **Multi-Provider Orchestration** — OpenAI, OpenRouter, Groq, Mistral, and more, with one clean interface.
* 🪛 **Tool Calling** — Let your model invoke Python functions directly.
* 🧠 **Cache Smart** — Redis, Django ORM, or memory-backed tool caching.
* 🔌 **Zero Framework Lock-In** — Integrate with anything: FastAPI, Flask, raw ASGI, or Celery.
* 🛠 **Hackable by Design** — Extend it, override it, plug it in where you want.

---

## 🧠 Core Concepts

Kebogyro is built around three key components:

### 🧵 `LLMClientWrapper`

Wraps any supported LLM provider (OpenAI, OpenRouter, Groq, etc.) with support for:

* Tool-calling via `additional_tools`
* System prompts
* Result caching
* Optional `mcp_client` integration

```python
llm = LLMClientWrapper(
    provider="openrouter",
    model_name="mistralai/mistral-7b-instruct",
    model_info={"api_key": os.getenv("OPENROUTER_API_KEY")},
    system_prompt="You are a helpful AI assistant.",
    mcp_client=mcp_client,                # Optional
    additional_tools=[my_tool],           # Optional
    llm_cache=MyLLMCacheAdapter(),        # Optional
)
```

> Works seamlessly **with or without tools**.

---

### 🛠 `BBServerMCPClient`

Adapter for remote tool orchestration using the MCP protocol. Supports multiple transports:

* `stdio`
* `sse`
* `streamable` HTTP

```python
mcp_client = BBServerMCPClient(
    connections={
        # Keys are namespaces (server names). You can define multiple MCP servers.
        # Each one is scoped separately in cache.
        "workroom_tools": {
            "url": "http://localhost:5000/sse",
            "transport": "sse",
        },
        "finance_tools": {
            "url": "http://localhost:5100/sse",
            "transport": "sse",
        }
    },
    cache_adapter=MyLLMCacheAdapter()
)
```

> Namespaces isolate tools per server and reflect in cache keys.

---

### 🎭 `create_agent`

Creates an orchestration pipeline that connects:

* LLM
* Optional tools
* Optional MCP tools

```python
from kebogyro.agent_executor import create_agent

agent = create_agent(
    llm_client=llm,
    tools=[my_tool],                # Optional standard tools
    mcp_tools=mcp_client,          # Optional BBServerMCPClient
    system_prompt="You're a coding agent.",
    stream=True
)

response = await agent.ainvoke({"input": "What's the weather like in Yogyakarta?"})
```

> You can mix & match standard tools and MCP tools — or use none at all.

---

## ⚡️ Full Example: Caching + Custom Tools

```python
from kebogyro.wrapper import LLMClientWrapper
from kebogyro.mcp_adapter.client import BBServerMCPClient
from kebogyro.agent_executor import create_agent
from kebogyro.cache import AbstractLLMCache
from kebogyro.utils import SimpleTool
import os

class MyLLMCacheAdapter(AbstractLLMCache):
    async def aget_value(self, key): ...
    async def aset_value(self, key, value, expiry_seconds): ...
    async def adelete_value(self, key): ...
    async def is_expired(self, key): ...

def say_hello(name: str) -> str:
    return f"Hello, {name}!"

hello_tool = SimpleTool.from_fn(
    name="say_hello",
    description="Greets the user.",
    fn=say_hello
)

mcp_client = BBServerMCPClient(
    connections={
        "tools": {
            "url": "http://localhost:5000/sse",
            "transport": "sse"
        }
    },
    cache_adapter=MyLLMCacheAdapter()
)

llm = LLMClientWrapper(
    provider="openrouter",
    model_name="mistralai/mistral-7b-instruct",
    model_info={"api_key": os.getenv("OPENROUTER_API_KEY")},
    mcp_client=mcp_client,
    additional_tools=[hello_tool],
    llm_cache=MyLLMCacheAdapter()
)

agent = create_agent(
    llm_client=llm,
    tools=[hello_tool],
    mcp_tools=mcp_client,
    system_prompt="You're a cached, tool-capable agent.",
    stream=False
)

response = await agent.ainvoke({"input": "Say hello to Lantip"})
```

---

## 🌐 LLM Provider Config

Edit `config.py` to register or override providers:

```python
class LLMClientConfig(BaseModel):
    base_urls: Dict[str, HttpUrl] = Field(
        default_factory=lambda: {
            "openrouter": "https://openrouter.ai/api/v1",
            "anthropic": "https://api.anthropic.com/v1/",
            "cerebras": "https://api.cerebras.ai/v1",
            "groq": "https://api.groq.ai/openai/v1",
            "requesty": "https://router.requesty.ai/v1"
        }
    )
    google_default_base_url: HttpUrl = "https://generativelanguage.googleapis.com/v1beta/openai/"
```

Add custom:

```python
config = LLMClientConfig()
config.base_urls["my_llm"] = "https://my-custom-llm.com/api"
```

---

## 📦 Install

```bash
pip install kebogyro
```

---

## 🙌 Contributing

Pull requests, bug reports, ideas, memes — all welcome.

---

## 📄 License

ABRMS — Use it, remix it, extend it. Let the gamelan guide your tools.
