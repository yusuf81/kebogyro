# 🧵 LLMClientWrapper

`LLMClientWrapper` is the main interface for invoking LLMs, managing tool calls, and optionally integrating with a cache or MCP client.

---

## 🔧 Constructor

```python
LLMClientWrapper(
    provider: str,
    model_name: str,
    model_info: dict[str, Any],
    mcp_client: Optional[MCPServerClient] = None,
    additional_tools: Optional[list[SimpleTool]] = None,
    system_prompt: Optional[str] = None,
    cache_key: str = "global_tools_cache",
    llm_cache: Optional[AbstractLLMCache] = None
)
```

---

## 💡 Example

```python
llm = LLMClientWrapper(
    provider="openrouter",
    model_name="mistralai/mistral-7b-instruct",
    model_info={"api_key": "sk-..."},
    system_prompt="You are a helpful AI.",
    additional_tools=[my_tool],
    llm_cache=MyCache()
)
```

---

## 🔍 Features

* Supports OpenAI-compatible chat endpoints
* Can combine standard tools and MCP tools
* Works with or without tools
* Fully async: use `await llm.achat()` or `await agent.ainvoke()`

---

## 🧪 Tool Support

Tools passed to `additional_tools` will be formatted to OpenAI-style `function_call` specs.
You can dynamically combine with tools from `BBServerMCPClient`.

---

## 🧠 Notes

* Set `system_prompt` for context-specific system messages
* `llm_cache` can cache both tool specs and call responses

---

Next → [BBServerMCPClient](./mcp_client.md)
