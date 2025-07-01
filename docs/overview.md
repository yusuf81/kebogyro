# 🧠 Overview

Kebogyro is a **fast, async-first orchestration layer** designed to make it easy to build LLM-powered applications with real tool-calling capabilities.

Inspired by:

* 🛠 **Gyro Gearloose** — a symbol of mechanical cleverness
* 🎶 **Kebogiro** — a Javanese ceremonial gamelan suite

Together: `kebogyro` combines structure, power, and orchestration — but for AI agents.

---

## ✨ Philosophy

* **Async-native**: All I/O is `async def`, suitable for modern event loops.
* **Composable**: Plug in your own LLM provider, cache backend, or tool logic.
* **OpenAI-compatible**: Use OpenAI-style tool specs, but with any provider.
* **No framework lock-in**: Integrate with anything — FastAPI, Flask, Celery, etc.

---

## 🧩 Architecture

* `LLMClientWrapper`: Base abstraction over LLM APIs
* `SimpleTool`: Describe tools with arguments and behavior
* `BBServerMCPClient`: Protocol-aware adapter to remote tool bridges
* `create_agent`: Glues it all together (LLM + tools + MCP)
* `AbstractLLMCache`: Optional caching layer for tool specs/results

---

## 📦 When to Use

Kebogyro is perfect for:

* Multi-provider LLM routing and orchestration
* Tool-enabled agents in async web backends
* LLM interfaces where caching or streaming is required
* Building OpenAI-compatible tool calling into any environment

If you're building a serious LLM agent system that talks to code, services, or other users — Kebogyro is your async Swiss Army knife.

---

Next → [Getting Started](./getting_started.md)
