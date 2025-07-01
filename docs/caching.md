# 🧠 Caching in Kebogyro

Caching improves speed and cost efficiency by preventing repeated tool spec fetches and model calls.

---

## 🔧 Interface: AbstractLLMCache

```python
class AbstractLLMCache:
    async def aget_value(self, key: str): ...
    async def aset_value(self, key: str, value: dict, expiry_seconds: int): ...
    async def adelete_value(self, key: str): ...
    async def is_expired(self, key: str, expiry_seconds: int): ...
```

---

## 🔄 Dual Caching Strategy

Kebogyro caches both:

* 🔧 Tool metadata (via `BBServerMCPClient`)
* 📥 Model responses + tool resolution (via `LLMClientWrapper`)

---

## 📦 Example Adapter

```python
class MyCache(AbstractLLMCache):
    async def aget_value(self, key): ...
    async def aset_value(self, key, value, expiry_seconds): ...
    async def adelete_value(self, key): ...
    async def is_expired(self, key, expiry_seconds): ...
```

---

## 🧪 Usage

Pass to both:

```python
llm = LLMClientWrapper(
    ...,
    llm_cache=MyCache()
)

mcp = BBServerMCPClient(
    ...,
    cache_adapter=MyCache()
)
```

---

## 🎯 Tips

* Use Redis or DB cache in production.
* Avoid caching extremely dynamic responses unless necessary.
* Align expiry time with tool volatility.

---

Next → [Extending Providers](./providers.md)
