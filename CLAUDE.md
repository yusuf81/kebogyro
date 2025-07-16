# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development Setup
```bash
# Install dependencies (Python 3.10+ required)
pip install -e .

# Run tests
pytest

# Run specific test
pytest tests/test_agent_executor.py

# Run tests with asyncio support
pytest -x --tb=short -v
```

### Web UI
```bash
# Run Streamlit web interface (recommended)
python run_webui.py

# Or manually:
streamlit run web_ui/app.py

# Or from project root:
python -m streamlit run web_ui/app.py
```

### Environment Setup
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Required variables for Ollama:
# OPENAI_API_BASE=http://localhost:11434/v1
# OPENAI_API_KEY=ollama
# KBG_OLLAMA_MODEL=llama3
# KBG_LLM_PROVIDER=ollama
# KBG_LLM_TEMPERATURE=0.1
```

### Building and Documentation
```bash
# Build documentation (if mkdocs is setup)
mkdocs build
mkdocs serve

# Build package
python -m build
```

## Architecture Overview

Kebogyro is an async-first LLM orchestration toolkit with three core components:

### 1. LLMClientWrapper (`src/kebogyro/wrapper.py`)
- Central LLM client that wraps OpenAI-compatible providers
- Supports tool calling via `additional_tools` parameter
- Handles conversation history and streaming responses
- Integrates with caching via `AbstractLLMCache`
- Provider configuration in `src/kebogyro/config.py`

### 2. BBServerMCPClient (`src/kebogyro/mcp_adapter/client.py`)
- MCP (Model Context Protocol) client for remote tool orchestration
- Supports multiple transports: `stdio`, `sse`, `streamable` HTTP
- Namespace-based tool isolation per MCP server
- Tool caching with configurable expiration

### 3. Agent Executor (`src/kebogyro/agent_executor.py`)
- Orchestrates LLM + tools + MCP tools
- Created via `create_agent()` function
- Handles streaming responses and tool execution loops
- Max 15 iterations to prevent infinite loops

## Key Architectural Patterns

### Tool System
- `SimpleTool` base class in `src/kebogyro/mcp_adapter/tools.py`
- Tools can be local Python functions or remote MCP tools
- Tools are cached for performance (`DEFAULT_TOOL_CACHE_EXPIRATION_SECONDS = 300`)
- OpenAI function calling format conversion

### Async-First Design
- All major operations are async (`chat_completion_with_tools`, `load_tools`, etc.)
- Streaming responses supported throughout
- Uses `AsyncGenerator` for real-time processing

### Caching Layer
- Abstract base class `AbstractLLMCache` in `src/kebogyro/cache.py`
- Supports Redis, Django ORM, or custom implementations
- Tool definitions and LLM responses can be cached

### Message System
- Custom message types: `HumanMessage`, `AIMessage`, `AIMessageChunk`, `ToolMessage`
- Conversation history management
- OpenAI format compatibility

## Provider Configuration

Edit `src/kebogyro/config.py` to add/modify LLM providers:

```python
# Default providers: openrouter, anthropic, cerebras, groq, requesty
# Google models use google_default_base_url
# Custom providers can be added to base_urls dict
```

## Web UI Architecture

The Streamlit web interface (`web_ui/`) provides:
- Chat interface with streaming responses
- Two modes: "Chat Biasa" (normal chat) and "Bantuan Kode" (code assistance)
- Ollama integration via environment variables
- Async operation handling in Streamlit context

## Environment Variables

Required for Ollama integration:
- `OPENAI_API_BASE`: Ollama URL (e.g., `http://localhost:11434/v1`)
- `OPENAI_API_KEY`: API key (e.g., `ollama`)
- `KBG_OLLAMA_MODEL`: Model name (e.g., `llama3`)
- `KBG_LLM_PROVIDER`: Provider name (e.g., `ollama`)
- `KBG_LLM_TEMPERATURE`: Temperature setting (e.g., `0.1`)

## Testing

- Test files in `tests/` directory
- Async tests use `pytest-asyncio`
- Test coverage includes core components: wrapper, agent executor, MCP client, tools
- Web UI tests in `tests/web_ui/`

## Directory Structure

```
src/kebogyro/           # Main package
├── mcp_adapter/        # MCP protocol implementation
│   ├── client.py       # MCP client
│   ├── tools.py        # Tool definitions
│   ├── sessions.py     # Connection management
│   └── utils.py        # Utilities
├── wrapper.py          # LLM client wrapper
├── agent_executor.py   # Agent orchestration
├── cache.py           # Caching abstractions
├── config.py          # Provider configuration
└── messages.py        # Message types

web_ui/                # Streamlit interface
├── app.py             # Main Streamlit app
├── core_logic.py      # Business logic
└── tools.py           # UI-specific tools

tests/                 # Test suite
docs/                  # Documentation
```

### Coding Rules

1. First think through the problem, read the codebase for relevant files, and write a plan to tasks/todo.md.
2. The plan should have a list of todo items that you can check off as you complete them
3. Before you begin working, check in with me and I will verify the plan.
4. Then, begin working on the todo items, marking them as complete as you go.
5. Please every step of the way just give me a high level explanation of what changes you made
6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
7. Finally, add a review section to the tasks/todo.md file with a summary of the changes you made and any other relevant information.
8. Please run pytest chatterbot_app/test every change, to make sure no error.
9. Please use TDD (London School) for all aspect of source code modification
10. jalankan pyright dan flake8 --ignore=E501,W504,W503 untuk setiap files yang di edit, dan perbaiki error yang muncul
11. jalankan pytest untuk fungsi-fungsi yang terkait
