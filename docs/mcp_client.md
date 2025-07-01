# 🔌 BBServerMCPClient

This class connects Kebogyro to remote tool runners using the Model Context Protocol (MCP).

---

## 🛠 Constructor

```python
BBServerMCPClient(
    connections: dict[str, Connection],
    tool_cache_expiration_seconds: int = 3600,
    cache_adapter: Optional[AbstractLLMCache] = None
)
```

---

## 🔁 Transports Supported

- `stdio`: for local subprocesses
- `sse`: for streaming HTTP (ideal for FastAPI bridges)
- `http`: for non-streamable REST endpoints

---

## 📦 Example

```python
from kebogyro.mcp_adapter.client import BBServerMCPClient

mcp_client = BBServerMCPClient(
    connections={
        # "workroom_tools" is a namespace (server_name) — you can define multiple MCP backends under different keys
        "workroom_tools": {
            "url": "http://localhost:5000/sse",
            "transport": "sse"
        },
        "finance_tools": {
            "url": "http://localhost:5100/sse",
            "transport": "sse"
        }
    },
    cache_adapter=MyCache()
)
```

---

## 🧠 Namespaces & Cache

The keys in `connections` (like `workroom_tools`, `finance_tools`, etc.) serve as **namespaces** or **server names**.

They are automatically reflected in the internal cache structure to keep tool specs separate and avoid collisions across multiple MCP backends.

---

## 🔒 Caching

You can cache:
- Remote tool manifests (specs) per namespace
- Response payloads

---

## 📌 Usage

Pass `mcp_client` to `LLMClientWrapper`, or directly as `mcp_tools` to `create_agent()`.

---

Next → [create_agent](./agent_executor.md)
