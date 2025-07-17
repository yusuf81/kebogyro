import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from kebogyro.messages import AIMessageChunk


@pytest.mark.asyncio
async def test_process_chat_prompt_streams_chunks():
    """Tests that process_chat_prompt correctly yields chunks from a mocked LLMClientWrapper."""
    # Import function first
    from web_ui.core_logic import process_chat_prompt
    
    # Arrange
    mock_prompt = "Hello, LLM!"
    mock_config = MagicMock()
    
    # Mock LLM client
    mock_llm_client_instance = AsyncMock()
    async def mock_chat_completion_stream(*args, **kwargs):
        chunk1 = AIMessageChunk(content="Hello ")
        chunk2 = AIMessageChunk(content="World")
        chunk3 = AIMessageChunk(content="!")
        
        yield ("messages", (chunk1, {}))
        await asyncio.sleep(0.01)
        yield ("messages", (chunk2, {}))
        await asyncio.sleep(0.01)
        yield ("messages", (chunk3, {}))
    
    mock_llm_client_instance.chat_completion_with_tools = MagicMock(
        return_value=mock_chat_completion_stream()
    )
    
    # Mock session manager
    mock_session_manager = MagicMock()
    mock_session_manager.get_chat_client.return_value = mock_llm_client_instance
    
    with patch('web_ui.core_logic.SessionManager', return_value=mock_session_manager):
        # Act
        streamed_responses = []
        async for chunk in process_chat_prompt(mock_prompt, mock_config):
            streamed_responses.append(chunk)
        
        # Assert
        assert streamed_responses == ["Hello ", "World", "!"]
        mock_session_manager.get_chat_client.assert_called_once()
        mock_llm_client_instance.chat_completion_with_tools.assert_called_once_with(
            user_message_content=mock_prompt,
            stream=True
        )


@pytest.mark.asyncio
async def test_process_chat_prompt_handles_llm_error():
    """Tests that process_chat_prompt handles LLM errors gracefully."""
    from web_ui.core_logic import process_chat_prompt
    
    # Arrange
    mock_prompt = "Trigger error"
    mock_config = MagicMock()
    
    # Mock LLM client that yields error
    mock_llm_client_instance = AsyncMock()
    async def mock_chat_completion_error_stream(*args, **kwargs):
        yield ("error", "Simulated LLM Error")
    
    mock_llm_client_instance.chat_completion_with_tools = MagicMock(
        return_value=mock_chat_completion_error_stream()
    )
    
    # Mock session manager
    mock_session_manager = MagicMock()
    mock_session_manager.get_chat_client.return_value = mock_llm_client_instance
    
    with patch('web_ui.core_logic.SessionManager', return_value=mock_session_manager):
        # Act
        streamed_responses = []
        async for chunk in process_chat_prompt(mock_prompt, mock_config):
            streamed_responses.append(chunk)
        
        # Assert
        assert len(streamed_responses) == 1
        assert "Error" in streamed_responses[0] or "error" in streamed_responses[0]


@pytest.mark.asyncio
async def test_process_code_assistance_prompt_streams_chunks():
    """Tests that process_code_assistance_prompt works with tools and stream processing."""
    from web_ui.core_logic import process_code_assistance_prompt
    
    # Arrange
    mock_user_prompt = "Create a python function to add two numbers"
    mock_config = MagicMock()
    
    # Mock LLM client
    mock_llm_client_instance = AsyncMock()
    async def mock_tool_flow_stream(*args, **kwargs):
        # Create chunks that will be buffered and processed together
        chunks = [
            "Here's the function: ",
            "def add(a, b): ",
            "    return a + b\n",
            "# This function adds two numbers"
        ]
        
        for chunk_content in chunks:
            chunk = AIMessageChunk(content=chunk_content)
            yield ("messages", (chunk, {}))
            await asyncio.sleep(0.01)
    
    mock_llm_client_instance.chat_completion_with_tools = MagicMock(
        return_value=mock_tool_flow_stream()
    )
    
    # Mock session manager
    mock_session_manager = MagicMock()
    mock_session_manager.get_code_assistance_client.return_value = mock_llm_client_instance
    
    with patch('web_ui.core_logic.SessionManager', return_value=mock_session_manager):
        # Act
        streamed_responses = []
        async for chunk in process_code_assistance_prompt(mock_user_prompt, mock_config):
            streamed_responses.append(chunk)
        
        # Assert - stream processor batches chunks together
        # So we expect fewer output chunks than input chunks
        assert len(streamed_responses) > 0
        
        # Verify the complete response contains all content
        full_response = "".join(streamed_responses)
        assert "Here's the function:" in full_response
        assert "def add(a, b):" in full_response
        assert "return a + b" in full_response
        assert "This function adds two numbers" in full_response
        
        # Verify mocks were called correctly
        mock_session_manager.get_code_assistance_client.assert_called_once()
        mock_llm_client_instance.chat_completion_with_tools.assert_called_once_with(
            user_message_content=mock_user_prompt,
            stream=True
        )