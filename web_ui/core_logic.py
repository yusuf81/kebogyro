"""Core business logic for web UI - Outlines-based validation."""

import logging
import sys
from pathlib import Path
from typing import AsyncGenerator, Optional

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kebogyro.messages import AIMessageChunk
from web_ui.config import ConfigManager, ConfigValidationError
from web_ui.session_manager import SessionManager, SessionCreationError
from web_ui.error_handler import ErrorHandler
from web_ui.outlines_validator import (
    get_validator,
    get_stream_processor,
    DebugInfo
)

logger = logging.getLogger(__name__)


async def process_chat_prompt(prompt: str, config: Optional[ConfigManager] = None) -> AsyncGenerator[str, None]:
    """
    Process chat prompt with Outlines validation.
    
    Chat mode uses minimal filtering since no tools are involved.
    """
    error_handler = ErrorHandler()
    
    try:
        # Initialize configuration
        if config is None:
            config = ConfigManager.load_from_env_file()
        
        # Create session manager
        session_manager = SessionManager(config)
        
        # Get LLM client
        llm_client = session_manager.get_chat_client()
        
        logger.info(f"Sending prompt to LLM: '{prompt[:50]}...'")
        
        # Process stream with Outlines validation
        stream_processor = get_stream_processor()
        
        async def llm_stream():
            async for event_type, data in llm_client.chat_completion_with_tools(
                user_message_content=prompt,
                stream=True
            ):
                if event_type == "messages":
                    message_chunk = data[0]
                    if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                        yield message_chunk.content
                elif event_type == "error":
                    error_response = error_handler.handle_llm_error(Exception(str(data)))
                    yield error_handler.format_error_for_ui(error_response)
                    break
        
        # Process stream through Outlines validator
        async for chunk in stream_processor.process_chat_stream(llm_stream()):
            yield chunk
                
    except ConfigValidationError as e:
        error_response = error_handler.handle_configuration_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except SessionCreationError as e:
        error_response = error_handler.handle_llm_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except Exception as e:
        error_response = error_handler.handle_generic_error(e)
        yield error_handler.format_error_for_ui(error_response)


async def process_code_assistance_prompt(prompt: str, config: Optional[ConfigManager] = None) -> AsyncGenerator[str, None]:
    """
    Process code assistance prompt with Outlines validation.
    
    Replaces the massive ContentBuffer spaghetti with clean Outlines validation.
    """
    error_handler = ErrorHandler()
    
    try:
        # Initialize configuration
        if config is None:
            config = ConfigManager.load_from_env_file()
        
        # Create session manager
        session_manager = SessionManager(config)
        
        # Get code assistance client with tools
        llm_client = session_manager.get_code_assistance_client()
        
        logger.info(f"Sending code assistance prompt to LLM: '{prompt[:50]}...'")
        
        # Process stream with Outlines validation
        stream_processor = get_stream_processor()
        
        async def llm_stream():
            async for event_type, data in llm_client.chat_completion_with_tools(
                user_message_content=prompt,
                stream=True
            ):
                if event_type == "messages":
                    message_chunk = data[0]
                    if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                        yield message_chunk.content
                elif event_type == "tool_output_chunk":
                    # Log tool execution but don't expose to UI
                    tool_output_chunk = data
                    logger.info(f"Tool output: {tool_output_chunk.name if tool_output_chunk else 'N/A'}")
                elif event_type == "tool_call":
                    # Tool call event - log only
                    logger.info(f"Tool call: {data}")
                elif event_type == "error":
                    error_response = error_handler.handle_llm_error(Exception(str(data)))
                    yield error_handler.format_error_for_ui(error_response)
                    break
        
        # Process stream through Outlines validator (replaces ContentBuffer)
        async for chunk in stream_processor.process_code_stream(llm_stream()):
            yield chunk
                
    except ConfigValidationError as e:
        error_response = error_handler.handle_configuration_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except SessionCreationError as e:
        error_response = error_handler.handle_llm_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except Exception as e:
        error_response = error_handler.handle_generic_error(e)
        yield error_handler.format_error_for_ui(error_response)


async def process_chat_prompt_with_debug(prompt: str, config: Optional[ConfigManager] = None, debug_info: Optional[DebugInfo] = None) -> AsyncGenerator[str, None]:
    """
    Process chat prompt with debug information using Outlines.
    
    Replaces the complex debug tracking with clean Outlines models.
    """
    import time
    error_handler = ErrorHandler()
    
    try:
        # Initialize configuration
        if config is None:
            config = ConfigManager.load_from_env_file()
        
        # Create session manager
        session_manager = SessionManager(config)
        
        # Get chat client
        llm_client = session_manager.get_chat_client()
        
        logger.info(f"Sending prompt to LLM: '{prompt[:50]}...'")
        
        # Get validator and debug info
        validator = get_validator()
        if debug_info is None:
            debug_info = validator.create_debug_info()
        
        async for event_type, data in llm_client.chat_completion_with_tools(
            user_message_content=prompt,
            stream=True
        ):
            current_time = time.time()
            
            if event_type == "messages":
                message_chunk = data[0]
                if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                    raw_chunk = message_chunk.content
                    
                    # Add to debug info
                    debug_info.add_raw_chunk(raw_chunk, current_time)
                    debug_info.add_processed_chunk(
                        raw_chunk,
                        "Chat mode: No filtering applied",
                        current_time
                    )
                    
                    # Chat mode: yield content directly
                    logger.debug(f"Streaming chat chunk: {raw_chunk}")
                    yield raw_chunk
                    
            elif event_type == "error":
                error_response = error_handler.handle_llm_error(Exception(str(data)))
                yield error_handler.format_error_for_ui(error_response)
                break
                
    except ConfigValidationError as e:
        error_response = error_handler.handle_configuration_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except SessionCreationError as e:
        error_response = error_handler.handle_llm_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except Exception as e:
        error_response = error_handler.handle_generic_error(e)
        yield error_handler.format_error_for_ui(error_response)


async def process_code_assistance_prompt_with_debug(prompt: str, config: Optional[ConfigManager] = None, debug_info: Optional[DebugInfo] = None) -> AsyncGenerator[str, None]:
    """
    Process code assistance prompt with debug using Outlines.
    
    Uses stream processor for efficient filtering.
    """
    import time
    error_handler = ErrorHandler()
    
    try:
        # Initialize configuration
        if config is None:
            config = ConfigManager.load_from_env_file()
        
        # Create session manager
        session_manager = SessionManager(config)
        
        # Get code assistance client
        llm_client = session_manager.get_code_assistance_client()
        
        logger.info(f"Sending code assistance prompt to LLM: '{prompt[:50]}...'")
        
        # Get validator and debug info
        validator = get_validator()
        if debug_info is None:
            debug_info = validator.create_debug_info()
        
        # Create stream processor for efficient filtering
        stream_processor = get_stream_processor()
        
        async def llm_stream():
            async for event_type, data in llm_client.chat_completion_with_tools(
                user_message_content=prompt,
                stream=True
            ):
                current_time = time.time()
                
                if event_type == "messages":
                    message_chunk = data[0]
                    if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                        raw_chunk = message_chunk.content
                        
                        # Add to debug info
                        debug_info.add_raw_chunk(raw_chunk, current_time)
                        
                        logger.debug(f"Streaming code assistance chunk: {raw_chunk}")
                        yield raw_chunk
                            
                elif event_type == "tool_output_chunk":
                    tool_output_chunk = data
                    logger.info(f"Tool output: {tool_output_chunk.name if tool_output_chunk else 'N/A'}")
                elif event_type == "tool_call":
                    logger.info(f"Tool call: {data}")
                elif event_type == "error":
                    error_response = error_handler.handle_llm_error(Exception(str(data)))
                    yield error_handler.format_error_for_ui(error_response)
                    break
        
        # Process stream through Outlines validator with debug info
        async for chunk in stream_processor.process_code_stream(llm_stream()):
            if chunk:
                current_time = time.time()
                debug_info.add_processed_chunk(
                    chunk,
                    "Filtered by Outlines stream processor",
                    current_time
                )
                yield chunk
                
    except ConfigValidationError as e:
        error_response = error_handler.handle_configuration_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except SessionCreationError as e:
        error_response = error_handler.handle_llm_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except Exception as e:
        error_response = error_handler.handle_generic_error(e)
        yield error_handler.format_error_for_ui(error_response)


# Backward compatibility exports
__all__ = [
    "process_chat_prompt",
    "process_code_assistance_prompt",
    "process_chat_prompt_with_debug",
    "process_code_assistance_prompt_with_debug"
]
