# 🛠 Tool Interface (SimpleTool)

Kebogyro tools follow the OpenAI function-call format but use a simplified internal schema.

---

## 🧱 Define a Tool

```python
from kebogyro.utils import SimpleTool

def greet(name: str) -> str:
    return f"Hello, {name}!"

tool = SimpleTool.from_fn(
    name="greet",
    description="Greets the user by name.",
    fn=greet
)
```

---

## 🔁 Spec Conversion

`SimpleTool` auto-generates the correct JSON schema used by OpenAI-like models.

---

## 🧠 Best Practices

* Use type annotations!
* Keep descriptions concise
* Avoid global state

---

## 📌 Usage

```python
llm = LLMClientWrapper(
    ...,
    additional_tools=[tool]
)

agent = create_agent(
    ..., tools=[tool]
)
```

---

## 🔬 Advanced

You may define tools using Pydantic models manually for finer control.

---

Next → [Troubleshooting](./troubleshooting.md)
