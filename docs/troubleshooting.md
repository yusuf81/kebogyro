# 🧯 Troubleshooting Kebogyro

Common issues and how to resolve them.

---

## ❓ Tools not calling

* ✅ Make sure your `SimpleTool` is correctly passed to both `LLMClientWrapper` and `create_agent()`
* 🔍 Check that your function has type annotations
* 🧪 Add `print()` in the tool function to debug

---

## 🔌 MCP tool not resolving

* ✅ Ensure the `BBServerMCPClient` connection URL is reachable
* ❗ Confirm the tool bridge backend supports the correct transport (sse/http)
* 🔁 Try restarting the remote tool bridge service

---

## 🧵 Async issues

* 🔄 All functions should be awaited — use `await agent.ainvoke(...)`
* 🧠 Make sure your event loop isn’t blocked (e.g. use `asyncio.run()` in CLI)

---

## 🧰 Debugging tips

* Use `print()` or `logging` in:

  * `SimpleTool`
  * Tool function itself
  * MCP adapter
* Temporarily disable `llm_cache` to isolate bugs

---

## 🛟 Still stuck?

Open a GitHub issue or start a discussion. PRs with fixes are always welcome!
