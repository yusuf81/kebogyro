"""Core business logic for web UI."""

import logging
import sys
import json
import re
from pathlib import Path
from typing import AsyncGenerator

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kebogyro.messages import AIMessageChunk
from web_ui.config import ConfigManager, ConfigValidationError
from web_ui.session_manager import SessionManager, SessionCreationError
from web_ui.error_handler import ErrorHandler, ConfigurationError

logger = logging.getLogger(__name__)


def _is_tool_call_json(content: str) -> bool:
    """Check if content is a tool call JSON that should be filtered out."""
    if not content or not content.strip():
        return False
    
    # Check for JSON-like structure with tool call patterns
    content = content.strip()
    if (content.startswith('{') and content.endswith('}') and 
        ('"name"' in content or '"arguments"' in content) and
        'tool' in content.lower()):
        try:
            parsed = json.loads(content)
            # Check if it's a tool call structure
            if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                return True
        except json.JSONDecodeError:
            pass
    
    return False

async def process_chat_prompt(prompt: str, config: ConfigManager = None) -> AsyncGenerator[str, None]:
    """
    Processes a user prompt by sending it to an LLM via managed session.

    Args:
        prompt (str): The user's input prompt.
        config (ConfigManager, optional): Configuration manager instance.

    Yields:
        str: Chunks of the LLM's response content or error messages.
    """
    error_handler = ErrorHandler()
    
    try:
        # Initialize configuration if not provided
        if config is None:
            config = ConfigManager.load_from_env_file()
        
        # Create session manager
        session_manager = SessionManager(config)
        
        # Get LLM client
        llm_client = session_manager.get_chat_client()
        
        logger.info(f"Sending prompt to LLM: '{prompt[:50]}...'")
        
        async for event_type, data in llm_client.chat_completion_with_tools(
            user_message_content=prompt,
            stream=True
        ):
            if event_type == "messages":
                message_chunk = data[0]
                if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                    # Filter out tool call JSON from content
                    content = message_chunk.content
                    if not _is_tool_call_json(content):
                        logger.debug(f"Streaming chunk: {content}")
                        yield content
            elif event_type == "tool_call":
                # Tool call event - don't expose to UI, just log
                logger.info(f"Tool call initiated: {data}")
                # Don't yield tool call details to UI
            elif event_type == "tool_output_chunk":
                # Log tool execution but don't expose to UI
                tool_output_chunk = data
                logger.info(f"Tool output chunk: {tool_output_chunk.name if tool_output_chunk else 'N/A'}")
            elif event_type == "chunk":
                # Raw chunk event - don't expose to UI
                logger.debug(f"Raw chunk event received")
            elif event_type == "reasoning_chunk":
                # Reasoning chunk - don't expose to UI
                logger.debug(f"Reasoning chunk received")
            elif event_type == "error":
                error_response = error_handler.handle_llm_error(Exception(str(data)))
                yield error_handler.format_error_for_ui(error_response)
                break
            else:
                # Log unknown event types but don't expose to UI
                logger.debug(f"Unknown event type: {event_type}, data: {data}")
                
    except ConfigValidationError as e:
        error_response = error_handler.handle_configuration_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except SessionCreationError as e:
        error_response = error_handler.handle_llm_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except Exception as e:
        error_response = error_handler.handle_generic_error(e)
        yield error_handler.format_error_for_ui(error_response)



async def process_code_assistance_prompt(prompt: str, config: ConfigManager = None) -> AsyncGenerator[str, None]:
    """
    Processes a user prompt for code assistance using managed session with tools.

    Args:
        prompt (str): The user's input prompt (e.g., code description).
        config (ConfigManager, optional): Configuration manager instance.

    Yields:
        str: Chunks of the LLM's response content or error messages.
    """
    error_handler = ErrorHandler()
    
    try:
        # Initialize configuration if not provided
        if config is None:
            config = ConfigManager.load_from_env_file()
        
        # Create session manager
        session_manager = SessionManager(config)
        
        # Get code assistance client with tools
        llm_client = session_manager.get_code_assistance_client()
        
        logger.info(f"Sending code assistance prompt to LLM: '{prompt[:50]}...'")
        
        async for event_type, data in llm_client.chat_completion_with_tools(
            user_message_content=prompt,
            stream=True
        ):
            if event_type == "messages":
                message_chunk = data[0]
                if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                    # Filter out tool call JSON from content
                    content = message_chunk.content
                    if not _is_tool_call_json(content):
                        logger.debug(f"Streaming code assistance chunk: {content}")
                        yield content
            elif event_type == "tool_output_chunk":
                # Log tool execution but don't expose to UI
                tool_output_chunk = data
                logger.info(f"Tool output chunk: {tool_output_chunk.name if tool_output_chunk else 'N/A'}")
                # Don't yield tool output to UI - it's internal processing
            elif event_type == "tool_call":
                # Tool call event - don't expose to UI, just log
                logger.info(f"Tool call initiated: {data}")
                # Don't yield tool call details to UI - user doesn't need to see this
            elif event_type == "chunk":
                # Raw chunk event - don't expose to UI
                logger.debug(f"Raw chunk event received")
            elif event_type == "reasoning_chunk":
                # Reasoning chunk - don't expose to UI
                logger.debug(f"Reasoning chunk received")
            elif event_type == "error":
                error_response = error_handler.handle_llm_error(Exception(str(data)))
                yield error_handler.format_error_for_ui(error_response)
                break
            else:
                # Log unknown event types but don't expose to UI
                logger.debug(f"Unknown event type: {event_type}, data: {data}")
                
    except ConfigValidationError as e:
        error_response = error_handler.handle_configuration_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except SessionCreationError as e:
        error_response = error_handler.handle_llm_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except Exception as e:
        error_response = error_handler.handle_generic_error(e)
        yield error_handler.format_error_for_ui(error_response)
