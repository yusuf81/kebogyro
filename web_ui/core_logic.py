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
    
    content_stripped = content.strip()
    
    # Check for JSON-like structure with tool call patterns
    if (content_stripped.startswith('{') and content_stripped.endswith('}') and 
        ('"name"' in content_stripped or '"arguments"' in content_stripped) and
        'tool' in content_stripped.lower()):
        try:
            parsed = json.loads(content_stripped)
            # Check if it's a tool call structure
            if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                return True
        except json.JSONDecodeError:
            pass
    
    # Check for markdown code blocks containing tool call JSON
    if _is_markdown_tool_call_json(content_stripped):
        return True
    
    return False


def _is_markdown_tool_call_json(content: str) -> bool:
    """Check if content is a markdown code block containing tool call JSON."""
    if not content or not content.strip():
        return False
    
    content_stripped = content.strip()
    
    # Check for markdown code blocks
    if content_stripped.startswith('```') and content_stripped.endswith('```'):
        # Extract content inside code block
        lines = content_stripped.split('\n')
        if len(lines) < 3:
            return False
        
        # Skip the first line (```json or ```) and last line (```)
        json_content = '\n'.join(lines[1:-1]).strip()
        
        # Check if the content inside is tool call JSON
        if (json_content.startswith('{') and json_content.endswith('}') and
            ('"name"' in json_content or '"arguments"' in json_content) and
            'tool' in json_content.lower()):
            try:
                parsed = json.loads(json_content)
                if isinstance(parsed, dict) and 'name' in parsed and 'arguments' in parsed:
                    return True
            except json.JSONDecodeError:
                pass
    
    return False


class ContentBuffer:
    """Buffer for accumulating streaming content to detect tool call JSON."""
    
    def __init__(self, max_buffer_size: int = 2000):
        self.buffer = ""
        self.max_buffer_size = max_buffer_size
    
    def add_chunk(self, chunk: str) -> tuple[str, bool]:
        """Add chunk to buffer and return (content_to_yield, should_filter)."""
        if not chunk:
            return "", False
        
        # Add to buffer
        self.buffer += chunk
        
        # If buffer exceeds max size, clear old content
        if len(self.buffer) > self.max_buffer_size:
            self.buffer = self.buffer[-self.max_buffer_size//2:]
        
        # Check if current buffer contains tool call JSON
        if _is_tool_call_json(self.buffer):
            # Clear buffer and indicate filtering needed
            self.buffer = ""
            return "", True
        
        # Check for partial tool call patterns that might be streaming
        # Buffer if: chunk has tool patterns OR buffer has tool patterns
        # OR chunk is JSON start (potential tool call beginning)
        # OR we're in a markdown code block
        # OR we're accumulating streaming JSON
        buffer_has_tool_patterns = self._contains_tool_call_pattern(self.buffer)
        chunk_has_tool_patterns = self._contains_tool_call_pattern(chunk)
        chunk_is_json_start = self._is_json_start(chunk)
        chunk_is_markdown_start = chunk.strip().startswith('```')
        is_markdown_continuation = self._is_markdown_continuation(chunk)
        looks_like_streaming_json = self._looks_like_streaming_json_start()
        
        should_buffer = (
            chunk_has_tool_patterns or 
            buffer_has_tool_patterns or
            chunk_is_json_start or
            chunk_is_markdown_start or
            is_markdown_continuation or
            looks_like_streaming_json
        )
        
        # However, if the chunk doesn't have tool patterns and doesn't look like JSON,
        # but the buffer has tool patterns, we might want to yield the accumulated content
        # unless it looks like we're still building JSON or markdown
        if (not chunk_has_tool_patterns and not chunk_is_json_start and not is_markdown_continuation and
            not looks_like_streaming_json and buffer_has_tool_patterns and 
            not self._looks_like_json_continuation(chunk)):
            # Yield the accumulated content
            content_to_yield = self.buffer
            self.buffer = ""
            return content_to_yield, False
        
        if should_buffer:
            # Buffer this chunk but don't yield yet - wait for more content
            return "", False
        
        # Normal content - yield it and clear buffer
        content_to_yield = self.buffer
        self.buffer = ""
        return content_to_yield, False
    
    def _contains_tool_call_pattern(self, content: str) -> bool:
        """Check if content contains patterns that suggest tool call JSON."""
        if not content or not content.strip():
            return False
            
        content_stripped = content.strip()
        
        # Check for JSON-like patterns with tool-specific terms
        tool_patterns = [
            '"name"',
            '"arguments"',
            'code_assistant_tool',
            '"code_description"',
            '"current_code_context"'
        ]
        
        # Must contain JSON structural elements AND tool patterns
        has_json_structure = any(marker in content_stripped for marker in ['{', '}', ':', '"'])
        has_tool_pattern = any(pattern.lower() in content.lower() for pattern in tool_patterns)
        
        return has_json_structure and has_tool_pattern
    
    def _buffer_looks_like_markdown_start(self) -> bool:
        """Check if buffer starts with markdown code block."""
        if not self.buffer:
            return False
        return self.buffer.strip().startswith('```')
    
    def _is_markdown_continuation(self, content: str) -> bool:
        """Check if content might be part of a markdown code block."""
        if not content:
            return False
        # If buffer already starts with ```, consider most content as continuation
        # until we see the closing ```
        if self._buffer_looks_like_markdown_start():
            # Only continue buffering if this looks like a JSON-related markdown block
            # Check if the buffer contains 'json' after the ```
            buffer_lines = self.buffer.split('\n')
            if len(buffer_lines) > 0:
                first_line = buffer_lines[0].strip()
                if first_line == '```json' or first_line == '```':
                    # This might be JSON, continue buffering
                    return not (content.strip() == '```' and '```' in self.buffer[3:])
                else:
                    # This is code (python, js, etc), don't buffer
                    return False
            return not (content.strip() == '```' and '```' in self.buffer[3:])
        return False
    
    def _is_json_start(self, content: str) -> bool:
        """Check if content looks like the start of JSON."""
        if not content or not content.strip():
            return False
        content_stripped = content.strip()
        
        # Only consider it JSON start if it has more than just braces
        # Single characters like '{' by themselves are likely f-string starts
        if content_stripped == '{' or content_stripped == '[':
            return False
            
        return content_stripped.startswith('{') or content_stripped.startswith('[')
    
    def _looks_like_streaming_json_start(self) -> bool:
        """Check if buffer looks like it's starting to accumulate JSON."""
        if not self.buffer:
            return False
        
        # Check if buffer starts with { and has JSON-like patterns
        buffer_stripped = self.buffer.strip()
        if buffer_stripped.startswith('{'):
            # For it to be JSON, it needs more than just curly braces
            # It should have quotes (for keys/values) and colons (for key-value pairs)
            # Simple variable references like {limit} are NOT JSON
            has_quotes = '"' in buffer_stripped
            has_colons = ':' in buffer_stripped
            
            # Must have both quotes and colons to be considered JSON
            # This excludes f-string variables like {limit}, {name}, etc.
            if has_quotes and has_colons:
                return True
            
            # Additional check: if it's a complete single word in braces, it's likely an f-string variable
            if (buffer_stripped.startswith('{') and buffer_stripped.endswith('}') and 
                len(buffer_stripped) > 2):
                inner_content = buffer_stripped[1:-1].strip()
                # If it's just a word without quotes or colons, it's an f-string variable
                if (inner_content.isidentifier() or 
                    (inner_content.replace('_', '').replace('.', '').isalnum())):
                    return False
        
        return False
    
    def _buffer_contains_json_start(self) -> bool:
        """Check if buffer contains JSON start."""
        return self._is_json_start(self.buffer)
    
    def _looks_like_json_continuation(self, content: str) -> bool:
        """Check if content looks like JSON continuation (commas, colons, etc.)."""
        if not content or not content.strip():
            return False
        content_stripped = content.strip()
        json_continuation_chars = [',', ':', '}', ']', '{', '[']
        return any(char in content_stripped for char in json_continuation_chars)
    
    def reset(self):
        """Reset the buffer."""
        self.buffer = ""

async def process_chat_prompt(prompt: str, config: ConfigManager = None) -> AsyncGenerator[str, None]:
    """
    Processes a user prompt by sending it to an LLM via managed session.
    
    Chat mode does NOT use content filtering since:
    1. No tools are used, so no tool call JSON to filter
    2. All content (including code blocks) should be displayed as-is

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
                    # Chat mode: yield content directly without filtering
                    logger.debug(f"Streaming chunk: {message_chunk.content}")
                    yield message_chunk.content
            elif event_type == "error":
                error_response = error_handler.handle_llm_error(Exception(str(data)))
                yield error_handler.format_error_for_ui(error_response)
                break
            else:
                # Log other event types but don't expose to UI
                logger.debug(f"Event type: {event_type}, data: {data}")
                
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
    content_buffer = ContentBuffer()
    
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
                    # Use content buffer to filter out tool call JSON
                    content_to_yield, should_filter = content_buffer.add_chunk(message_chunk.content)
                    if content_to_yield and not should_filter:
                        logger.debug(f"Streaming code assistance chunk: {content_to_yield}")
                        yield content_to_yield
                    elif should_filter:
                        logger.debug(f"Filtered tool call JSON: {message_chunk.content}")
            elif event_type == "tool_output_chunk":
                # Log tool execution but don't expose to UI
                tool_output_chunk = data
                logger.info(f"Tool output chunk: {tool_output_chunk.name if tool_output_chunk else 'N/A'}")
                # Don't yield tool output to UI - it's internal processing
            elif event_type == "tool_call":
                # Tool call event - don't expose to UI, just log
                logger.info(f"Tool call initiated: {data}")
                # Reset buffer when tool call starts
                content_buffer.reset()
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
class DebugInfo:
    """Class to hold debug information for UI display."""
    def __init__(self):
        self.raw_chunks = []
        self.processed_chunks = []
        self.timing_info = []
        self.buffer_states = []
        self.total_raw_chars = 0
        self.total_processed_chars = 0
        
    def add_raw_chunk(self, chunk: str, timestamp: float = None):
        """Add a raw LLM chunk."""
        self.raw_chunks.append(chunk)
        self.total_raw_chars += len(chunk)
        if timestamp:
            self.timing_info.append({"type": "raw", "timestamp": timestamp, "chunk_size": len(chunk)})
    
    def add_processed_chunk(self, chunk: str, buffer_state: str = "", timestamp: float = None):
        """Add a processed chunk with buffer state."""
        self.processed_chunks.append(chunk)
        self.total_processed_chars += len(chunk)
        self.buffer_states.append(buffer_state)
        if timestamp:
            self.timing_info.append({"type": "processed", "timestamp": timestamp, "chunk_size": len(chunk)})
    
    def get_summary(self) -> dict:
        """Get summary statistics."""
        return {
            "raw_chunks_count": len(self.raw_chunks),
            "processed_chunks_count": len(self.processed_chunks),
            "total_raw_chars": self.total_raw_chars,
            "total_processed_chars": self.total_processed_chars,
            "chars_difference": self.total_raw_chars - self.total_processed_chars,
            "raw_content": "".join(self.raw_chunks),
            "processed_content": "".join(self.processed_chunks)
        }


async def process_chat_prompt_with_debug(prompt: str, config: ConfigManager = None, debug_info: DebugInfo = None) -> AsyncGenerator[str, None]:
    """
    Processes a user prompt with debug information capture.
    
    Chat mode does NOT use content filtering since:
    1. No tools are used, so no tool call JSON to filter
    2. All content (including code blocks) should be displayed as-is
    
    Args:
        prompt (str): The user's input prompt.
        config (ConfigManager, optional): Configuration manager instance.
        debug_info (DebugInfo, optional): Debug info collector.
    
    Yields:
        str: Chunks of the LLM's response content or error messages.
    """
    import time
    
    error_handler = ErrorHandler()
    
    try:
        # Initialize configuration if not provided
        if config is None:
            config = ConfigManager.load_from_env_file()
        
        # Initialize session manager
        session_manager = SessionManager(config)
        
        # Get chat client
        llm_client = session_manager.get_chat_client()
        
        logger.info(f"Sending prompt to LLM: '{prompt[:50]}...'")
        
        async for event_type, data in llm_client.chat_completion_with_tools(
            user_message_content=prompt,
            stream=True
        ):
            current_time = time.time()
            
            if event_type == "messages":
                message_chunk = data[0]
                if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                    raw_content = message_chunk.content
                    
                    # Add to debug info
                    if debug_info:
                        debug_info.add_raw_chunk(raw_content, current_time)
                        # In chat mode, processed content = raw content (no filtering)
                        debug_info.add_processed_chunk(
                            raw_content, 
                            "Chat mode: No filtering applied",
                            current_time
                        )
                    
                    # Chat mode: yield content directly without filtering
                    logger.debug(f"Streaming chat chunk: {raw_content}")
                    yield raw_content
            elif event_type == "error":
                error_response = error_handler.handle_llm_error(Exception(str(data)))
                yield error_handler.format_error_for_ui(error_response)
                break
            else:
                # Log other event types but don't expose to UI
                logger.debug(f"Event type: {event_type}, data: {data}")
                
    except ConfigValidationError as e:
        error_response = error_handler.handle_configuration_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except SessionCreationError as e:
        error_response = error_handler.handle_llm_error(e)
        yield error_handler.format_error_for_ui(error_response)
    except Exception as e:
        error_response = error_handler.handle_generic_error(e)
        yield error_handler.format_error_for_ui(error_response)


async def process_code_assistance_prompt_with_debug(prompt: str, config: ConfigManager = None, debug_info: DebugInfo = None) -> AsyncGenerator[str, None]:
    """
    Processes a code assistance prompt with debug information capture.
    
    Args:
        prompt (str): The user's input prompt.
        config (ConfigManager, optional): Configuration manager instance.
        debug_info (DebugInfo, optional): Debug info collector.
    
    Yields:
        str: Chunks of the LLM's response content or error messages.
    """
    import time
    
    error_handler = ErrorHandler()
    content_buffer = ContentBuffer()
    
    try:
        # Initialize configuration if not provided
        if config is None:
            config = ConfigManager.load_from_env_file()
        
        # Initialize session manager
        session_manager = SessionManager(config)
        
        # Get code assistance client with tools
        llm_client = session_manager.get_code_assistance_client()
        
        logger.info(f"Sending code assistance prompt to LLM: '{prompt[:50]}...'")
        
        async for event_type, data in llm_client.chat_completion_with_tools(
            user_message_content=prompt,
            stream=True
        ):
            current_time = time.time()
            
            if event_type == "messages":
                message_chunk = data[0]
                if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                    raw_content = message_chunk.content
                    
                    # Add to debug info
                    if debug_info:
                        debug_info.add_raw_chunk(raw_content, current_time)
                    
                    # Use content buffer to filter out tool call JSON
                    content_to_yield, should_filter = content_buffer.add_chunk(raw_content)
                    
                    if debug_info:
                        debug_info.add_processed_chunk(
                            content_to_yield, 
                            f"Buffer: '{content_buffer.buffer}' | Filter: {should_filter}",
                            current_time
                        )
                    
                    if content_to_yield and not should_filter:
                        logger.debug(f"Streaming code assistance chunk: {content_to_yield}")
                        yield content_to_yield
                    elif should_filter:
                        logger.debug(f"Filtered tool call JSON: {raw_content}")
            elif event_type == "tool_output_chunk":
                # Log tool execution but don't expose to UI
                tool_output_chunk = data
                logger.info(f"Tool output chunk: {tool_output_chunk.name if tool_output_chunk else 'N/A'}")
                # Don't yield tool output to UI - it's internal processing
            elif event_type == "tool_call":
                # Tool call event - don't expose to UI, just log
                logger.info(f"Tool call initiated: {data}")
                # Reset buffer when tool call starts
                content_buffer.reset()
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