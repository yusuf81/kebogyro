# 🌐 Extending LLM Providers

Kebogyro supports multiple LLM providers via base URL mapping in `config.py`.

---

## 🧱 Config Structure

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

---

## ➕ Add a Custom Provider

```python
config = LLMClientConfig()
config.base_urls["my_custom"] = "https://my.custom-llm.com/v1"
```

---

## ✅ Usage

Then instantiate your wrapper with:

```python
llm = LLMClientWrapper(
    provider="my_custom",
    model_name="awesome-model",
    model_info={"api_key": "..."}
)
```

---

## 💡 Notes

* Kebogyro assumes OpenAI-style endpoints unless extended.
* Custom adapters may be required for non-OpenAI-compatible APIs.

---

Next → [Tool Interface](./tools.md)
