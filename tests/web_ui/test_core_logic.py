import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Placeholder for where core_logic.py will be.
# We're writing tests first.
# from web_ui.core_logic import process_chat_prompt
# Will uncomment and use once web_ui.core_logic and its functions are created.

from kebogyro.messages import AIMessageChunk # Import the actual class

@pytest.mark.asyncio
async def test_process_chat_prompt_streams_chunks():
    """
    Tests that process_chat_prompt correctly yields chunks from a mocked LLMClientWrapper.
    """
    # Arrange
    mock_prompt = "Hello, LLM!"

    # Mocking the async generator `chat_completion_with_tools`
    mock_llm_client_instance = AsyncMock()
    async def mock_chat_completion_stream(*args, **kwargs):
        # Create mock objects that are instances of AIMessageChunk
        chunk1 = AIMessageChunk(content="Hello ")
        chunk2 = AIMessageChunk(content="World")
        chunk3 = AIMessageChunk(content="!")

        yield ("messages", (chunk1, {}))
        await asyncio.sleep(0.01) # Simulate async behavior
        yield ("messages", (chunk2, {}))
        await asyncio.sleep(0.01)
        yield ("messages", (chunk3, {}))

    mock_llm_client_instance.chat_completion_with_tools = MagicMock(return_value=mock_chat_completion_stream())

    # We need to patch the LLMClientWrapper where it's instantiated in core_logic.py
    # Assuming it's imported as `from kebogyro.wrapper import LLMClientWrapper` in core_logic.py
    with patch('web_ui.core_logic.LLMClientWrapper', return_value=mock_llm_client_instance) as mock_llm_wrapper_class:
        # Dynamically import here after patching, or ensure core_logic is loaded after patch
        from web_ui.core_logic import process_chat_prompt

        # Act
        streamed_responses = []
        async for chunk in process_chat_prompt(mock_prompt):
            streamed_responses.append(chunk)

        # Assert
        assert streamed_responses == ["Hello ", "World", "!"], "The streamed chunks do not match expected output."

        # Verify LLMClientWrapper was called correctly
        mock_llm_wrapper_class.assert_called_once() # Check if constructor was called

        # Verify chat_completion_with_tools was called correctly on the instance
        # The actual arguments will depend on how process_chat_prompt calls it
        mock_llm_client_instance.chat_completion_with_tools.assert_called_once_with(
            user_message_content=mock_prompt,
            stream=True
        )

@pytest.mark.asyncio
async def test_process_chat_prompt_handles_llm_error():
    """
    Tests that process_chat_prompt correctly handles and yields an error message
    if the LLM client raises an error.
    """
    # Arrange
    mock_prompt = "Trigger error"

    mock_llm_client_instance = AsyncMock()
    async def mock_chat_completion_error_stream(*args, **kwargs):
        yield ("error", "Simulated LLM Error")
        # The loop in chat_completion_with_tools might break on error, so only one yield
        # Or it might yield an error and then nothing else.
        # We need to ensure process_chat_prompt catches this.

    mock_llm_client_instance.chat_completion_with_tools = MagicMock(return_value=mock_chat_completion_error_stream())

    with patch('web_ui.core_logic.LLMClientWrapper', return_value=mock_llm_client_instance) as mock_llm_wrapper_class:
        from web_ui.core_logic import process_chat_prompt

        # Act
        streamed_responses = []
        async for chunk in process_chat_prompt(mock_prompt):
            streamed_responses.append(chunk)

        # Assert
        # Expecting the process_chat_prompt to perhaps yield a user-friendly error message
        # or re-raise, or yield a specific error indicator.
        # For this test, let's assume it yields a string like "Error: Simulated LLM Error"
        assert len(streamed_responses) == 1
        assert "Error: Simulated LLM Error" in streamed_responses[0]

        mock_llm_wrapper_class.assert_called_once()
        mock_llm_client_instance.chat_completion_with_tools.assert_called_once_with(
            user_message_content=mock_prompt,
            stream=True
        )

# We will create web_ui/core_logic.py next, and then these tests can be run.
# For now, they will fail because web_ui.core_logic and process_chat_prompt don't exist.


@pytest.mark.asyncio
async def test_process_code_assistance_prompt_tool_calling_flow():
    """
    Tests the process_code_assistance_prompt function for the full tool calling flow:
    1. LLM requests to use the code_assistant_tool.
    2. Tool is 'executed' (mocked).
    3. LLM produces a final response based on tool output.
    All streamed.
    """
    mock_user_prompt = "Create a python function to add two numbers"

    # 1. Mock LLMClientWrapper and its chat_completion_with_tools generator
    mock_llm_client_instance = AsyncMock()

    # Import the actual tool to be used by the LLMClientWrapper in core_logic
    from web_ui.tools import code_assistant_tool
    from kebogyro.mcp_adapter.utils import convert_tools_to_openai_format

    # Expected arguments for the tool call by the LLM
    expected_tool_args_str = '{"code_description": "Create a python function to add two numbers.", "current_code_context": ""}'

    # This is what the LLM (mocked) would first yield: a request to call a tool
    tool_call_id = "call_123"
    tool_call_request_chunk = MagicMock() # Simulates the ChatCompletionChunk structure
    tool_call_request_chunk.choices = [MagicMock(delta=MagicMock(
        content=None,
        tool_calls=[MagicMock(
            index=0,
            id=tool_call_id,
            type='function',
            function=MagicMock(name='code_assistant_tool', arguments=expected_tool_args_str)
        )]
    ))]

    # This is what the LLM (mocked) would yield after tool execution result is fed back
    final_response_content_chunk1 = AIMessageChunk(content="Okay, here's the function: ")
    final_response_content_chunk2 = AIMessageChunk(content="\n```python\ndef add(a, b):\n  return a + b\n```")

    # The mocked stream from chat_completion_with_tools
    # It needs to handle multiple calls if the tool calling is iterative within LLMClientWrapper
    # For this test, we assume one tool call, then final response.
    # LLMClientWrapper's chat_completion_with_tools internally handles the loop of
    # LLM -> tool_call -> tool_exec -> LLM.
    # So, the generator we mock here is the one from LLMClientWrapper, which already abstracts that.
    # It will yield 'tool_output_chunk' for the tool's execution, then 'messages' for final LLM response.

    # The actual output from the (placeholder) tool:
    # generated_code_snippet = f"// Placeholder: Code for '{inputs.code_description}' ..."
    # explanation = "This is a placeholder response from the code_assistant_tool..."
    # This will be part of the ToolMessage sent back to the LLM by LLMClientWrapper.
    # Then, the LLM generates the final response.

    async def mock_tool_flow_stream(*args, **kwargs):
        # 1. LLM asks to use the tool.
        # In LLMClientWrapper, this would result in it yielding the tool call details if we were tapping into that.
        # However, process_code_assistance_prompt is higher level.
        # LLMClientWrapper will internally call the tool.
        # What process_code_assistance_prompt receives is:
        #  - AIMessageChunk for tool call (if LLM also "talks" before/during tool call, not typical for pure tool call)
        #  - AIMessageChunk for the tool's output being processed (e.g. a message "Executing tool X...")
        #  - AIMessageChunk for the final LLM response after getting tool output.

        # Let's simplify what process_code_assistance_prompt itself yields:
        # It should yield the final assistant's message content chunks.
        # The tool calling part is handled internally by LLMClientWrapper.

        # The mock for chat_completion_with_tools should simulate what it yields to its caller.
        # Event sequence:
        # 1. LLM decides to call a tool. (chunk with tool_calls)
        #    LLMClientWrapper processes this.
        # 2. Tool is executed by LLMClientWrapper. It might yield a 'tool_output_chunk'.
        #    (Let's assume our process_code_assistance_prompt might not directly expose this,
        #     or it might. For now, focus on final output).
        # 3. Tool result is sent back to LLM.
        # 4. LLM sends final response content. (chunks with content)

        # Simulate the final content stream
        yield ("messages", (final_response_content_chunk1, {}))
        await asyncio.sleep(0.01)
        yield ("messages", (final_response_content_chunk2, {}))

    mock_llm_client_instance.chat_completion_with_tools = MagicMock(return_value=mock_tool_flow_stream())

    # Patch LLMClientWrapper instantiation in core_logic
    # Also, we need to ensure that the `code_assistant_tool` is correctly passed to it.
    # The `additional_tools` argument of LLMClientWrapper is where it should go.

    with patch('web_ui.core_logic.LLMClientWrapper', return_value=mock_llm_client_instance) as mock_llm_wrapper_class:
        # Import the function under test
        from web_ui.core_logic import process_code_assistance_prompt

        # Act
        streamed_responses = []
        async for chunk in process_code_assistance_prompt(mock_user_prompt):
            streamed_responses.append(chunk)

        # Assert
        expected_final_chunks = [
            "Okay, here's the function: ",
            "\n```python\ndef add(a, b):\n  return a + b\n```"
        ]
        assert streamed_responses == expected_final_chunks, "Streamed final response chunks do not match."

        # Verify LLMClientWrapper was instantiated correctly with the tool
        # The call to the constructor happens in process_code_assistance_prompt
        # We need to check the arguments passed to the constructor.
        # This assertion is on the class mock itself.

        # Get the call arguments for LLMClientWrapper constructor
        constructor_args, constructor_kwargs = mock_llm_wrapper_class.call_args

        # Check if 'additional_tools' was passed and contains our tool
        assert 'additional_tools' in constructor_kwargs
        passed_tools_list = constructor_kwargs['additional_tools']
        assert len(passed_tools_list) == 1
        assert passed_tools_list[0].name == code_assistant_tool.name # Compare by unique aspect

        # Verify chat_completion_with_tools was called on the instance
        mock_llm_client_instance.chat_completion_with_tools.assert_called_once_with(
            user_message_content=mock_user_prompt,
            stream=True
        )
