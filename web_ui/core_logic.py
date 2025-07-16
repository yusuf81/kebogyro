import os
import logging
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kebogyro.wrapper import LLMClientWrapper
from kebogyro.messages import AIMessageChunk

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_chat_prompt(prompt: str):
    """
    Processes a user prompt by sending it to an LLM via Kebogyro's LLMClientWrapper
    and yields streamed response content.

    Args:
        prompt (str): The user's input prompt.

    Yields:
        str: Chunks of the LLM's response content or an error message.
    """
    llm_provider = os.getenv("KBG_LLM_PROVIDER", "ollama")
    llm_model_name = os.getenv("KBG_OLLAMA_MODEL", "llama3") # Default if Ollama
    # OPENAI_API_BASE will be used by openai library if provider is not in kebogyro's config
    # OPENAI_API_KEY also needs to be set, e.g., "ollama"

    # For Ollama, api_key can be anything, as it's not typically used by Ollama itself
    # but openai client library might expect it.
    api_key = os.getenv("OPENAI_API_KEY", "ollama")

    # Temperature could also be configurable
    temperature = float(os.getenv("KBG_LLM_TEMPERATURE", 0.1))

    # Initialize LLMClientWrapper
    # Note: For actual remote Ollama, ensure OPENAI_API_BASE is set in your environment
    # e.g., export OPENAI_API_BASE="http://localhost:11434/v1"
    # The 'provider' field here helps kebogyro find a base_url if defined in its config,
    # but for Ollama, it'll rely on OPENAI_API_BASE.
    llm_client = LLMClientWrapper(
        provider=llm_provider,
        model_name=llm_model_name,
        model_info={"api_key": api_key, "temperature": temperature},
        system_prompt="You are a helpful AI assistant.",
        # llm_cache=... # Optionally add a cache implementation here
        # additional_tools=... # Will be added for code assistant
    )

    try:
        logger.info(f"Sending prompt to LLM: '{prompt[:50]}...'")
        async for event_type, data in llm_client.chat_completion_with_tools(
            user_message_content=prompt,
            stream=True
        ):
            if event_type == "messages":
                # data is (AIMessageChunk, {})
                message_chunk = data[0]
                if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                    logger.debug(f"Streaming chunk: {message_chunk.content}")
                    yield message_chunk.content
            elif event_type == "error":
                error_message = f"Error: {data}"
                logger.error(f"LLM client reported an error: {data}")
                yield error_message
                break # Stop streaming on error
            # We can handle other event_types like 'reasoning_chunk', 'tool_output_chunk' if needed,
            # but for simple chat, 'messages' (content) and 'error' are primary.
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logger.exception("An unexpected error occurred during LLM interaction.")
        yield error_message

# Example of how to test this locally (not part of the actual file usually)
async def _test_run():
    # Ensure OPENAI_API_BASE and OPENAI_API_KEY are set in your environment
    # e.g.
    # export OPENAI_API_BASE="http://localhost:11434/v1"
    # export OPENAI_API_KEY="ollama"
    # export KBG_OLLAMA_MODEL="your-ollama-model" (e.g., llama3)

    print(f"OPENAI_API_BASE: {os.getenv('OPENAI_API_BASE')}")
    print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")
    print(f"KBG_OLLAMA_MODEL: {os.getenv('KBG_OLLAMA_MODEL')}")

    if not os.getenv('OPENAI_API_BASE'):
        print("Warning: OPENAI_API_BASE is not set. Ollama calls will likely fail.")
        return

    test_prompt = "Tell me a short story about a robot."
    print(f"\n--- Testing process_chat_prompt with prompt: '{test_prompt}' ---")
    async for chunk in process_chat_prompt(test_prompt):
        print(chunk, end="", flush=True)
    print("\n--- Test finished ---")

if __name__ == "__main__":
    import asyncio
    # To run this test part:
    # 1. Make sure kebogyro and its dependencies are installed.
    # 2. Set environment variables as mentioned above.
    # 3. Run `python web_ui/core_logic.py`
    # asyncio.run(_test_run()) # Comment out when not testing directly
    pass


async def process_code_assistance_prompt(prompt: str):
    """
    Processes a user prompt for code assistance by sending it to an LLM
    via Kebogyro's LLMClientWrapper, with the code_assistant_tool enabled.
    Yields streamed response content.

    Args:
        prompt (str): The user's input prompt (e.g., code description).

    Yields:
        str: Chunks of the LLM's response content or an error message.
    """
    llm_provider = os.getenv("KBG_LLM_PROVIDER", "ollama")
    llm_model_name = os.getenv("KBG_OLLAMA_MODEL", "llama3")
    api_key = os.getenv("OPENAI_API_KEY", "ollama")
    temperature = float(os.getenv("KBG_LLM_TEMPERATURE", 0.1))

    # Import the tool
    from web_ui.tools import code_assistant_tool

    # System prompt tailored for code assistance
    system_prompt = (
        "You are a helpful AI code assistant. "
        "When appropriate, use the 'code_assistant_tool' to help with code generation, "
        "completion, or explanation. Provide answers primarily in code blocks if generating code."
    )

    llm_client = LLMClientWrapper(
        provider=llm_provider,
        model_name=llm_model_name,
        model_info={"api_key": api_key, "temperature": temperature},
        system_prompt=system_prompt,
        additional_tools=[code_assistant_tool] # Add the code assistant tool here
        # llm_cache=...
    )

    try:
        logger.info(f"Sending code assistance prompt to LLM: '{prompt[:50]}...'")
        async for event_type, data in llm_client.chat_completion_with_tools(
            user_message_content=prompt,
            stream=True
        ):
            if event_type == "messages":
                message_chunk = data[0]
                if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                    logger.debug(f"Streaming code assistance chunk: {message_chunk.content}")
                    yield message_chunk.content
            elif event_type == "tool_output_chunk": # Handle tool output if needed by UI
                # This event type comes from LLMClientWrapper when a tool is run.
                # We might want to display something in the UI, e.g., "Running tool X..."
                # For now, we'll just log it and not yield it to the Streamlit UI directly,
                # as the final LLM response is what we primarily want to stream there.
                tool_output_chunk = data # This is an AIMessageChunk
                logger.info(f"Tool output chunk from LLMClientWrapper: {tool_output_chunk.name if tool_output_chunk else 'N/A'}")
                # Example: if tool_output_chunk.content: yield f"[Tool: {tool_output_chunk.name} output: {tool_output_chunk.content[:50]}...]\n"
            elif event_type == "error":
                error_message = f"Error: {data}"
                logger.error(f"LLM client reported an error during code assistance: {data}")
                yield error_message
                break
    except Exception as e:
        error_message = f"An unexpected error occurred during code assistance: {str(e)}"
        logger.exception("An unexpected error occurred during code assistance LLM interaction.")
        yield error_message
