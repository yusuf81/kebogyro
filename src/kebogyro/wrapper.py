from typing import Dict, Any, List, Union, AsyncGenerator, Tuple, Optional, Callable
from .mcp_adapter.client import BBServerMCPClient as MCPServerClient 
from .mcp_adapter.tools import SimpleTool
from .mcp_adapter.utils import convert_tools_to_openai_format
from .cache import AbstractLLMCache
from .messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from .config import get_base_url
from openai import AsyncOpenAI, NOT_GIVEN
from openai.types.chat import (
    ChatCompletionMessageParam, ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam, 
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam, 
    ChatCompletionMessageToolCall 
)
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types import FunctionDefinition as OpenAIFunctionDefinition
import json 
import logging 
import uuid
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class LLMClientWrapper:
    def __init__(self, provider: str, 
        model_name: str, 
        model_info: Dict[str, Any],         
        mcp_client: Optional[MCPServerClient] = None,
        additional_tools: Optional[List[SimpleTool]] = None, 
        system_prompt: Optional[str] = None, 
        cache_key: str = "global_tools_cache",
        llm_cache: Optional[AbstractLLMCache] = None):

        self.logger = logging.getLogger(f"LLMClientWrapper.{model_name}")
        self.provider = provider
        self.model_name = model_name
        self.model_info = model_info
        self.mcp_client = mcp_client
        self.additional_tools = additional_tools
        self.client = self._initialize_openai_client()
        self.system_prompt_content = system_prompt
        self.conversation_history: List[ChatCompletionMessageParam] = []

        self._raw_available_tools_from_mcp: Dict[str, SimpleTool] = {}
        self.available_tools_for_llm: List[ChatCompletionToolParam] = []
        self.cache_key = cache_key
        self.TOOL_CACHE_EXPIRATION_SECONDS = 60 * 60 * 24
        self.llm_cache = llm_cache

        if self.llm_cache is None:
            self.logger.warning("No LLM Cache implementation provided. Tool caching will be disabled.")

    def _initialize_openai_client(self) -> AsyncOpenAI:
        base_url = get_base_url(provider=self.provider)

        self.temperature = self.model_info.get("temperature", 0.0)

        self.logger.info(f"LLMClientWrapper Initializing: Provider={self.provider}, Model={self.model_name}, Base_URL={base_url}, Temp={self.temperature}")

        if base_url:
            return AsyncOpenAI(api_key=self.model_info["api_key"], base_url=base_url)
        else:
            return AsyncOpenAI(api_key=self.model_info["api_key"])

    async def load_tools(self, server_name: str = None, force_refresh: bool = False) -> List[ChatCompletionToolParam]:
        cached_tools_data = None
        
        self.logger.info(f"Attempting to load tools. Cache key: {self.cache_key}, Force Refresh: {force_refresh}")

        if self.llm_cache and not force_refresh:
            try:
                cached_tools_data = await self.llm_cache.aget_value(self.cache_key)
                if cached_tools_data and not await self.llm_cache.is_expired(self.cache_key, self.TOOL_CACHE_EXPIRATION_SECONDS):
                    self.logger.info(f"Using cached tools for key: {self.cache_key}.")
                else:
                    self.logger.info(f"Cache expired or invalid for key: {self.cache_key}. Refreshing.")
                    cached_tools_data = None 
            except Exception as e:
                self.logger.error(f"Error accessing cache for key {self.cache_key}: {e}", exc_info=True)
                if self.llm_cache:
                    await self.llm_cache.adelete_value(self.cache_key) 
                self.logger.warning(f"Malformed/errored cache entry deleted for key: {self.cache_key}.")
                cached_tools_data = None

        if cached_tools_data:
            self.logger.debug("Populating _raw_available_tools_from_mcp for deserialization (if not already).")
            if not self._raw_available_tools_from_mcp: 
                live_tools = self.additional_tools
                if self.mcp_client:
                    live_tools += await self.mcp_client.get_tools(server_name=server_name)
                self._raw_available_tools_from_mcp = {tool.name: tool for tool in live_tools}
            
            deserialized_tools = []
            for tool_data in cached_tools_data:
                tool_name = tool_data.get("name")
                if tool_name and tool_name in self._raw_available_tools_from_mcp:
                    deserialized_tools.append(self._raw_available_tools_from_mcp[tool_name])
                else:
                    self.logger.warning(f"Live tool '{tool_name}' not found for cached entry. Skipping.")

            self.available_tools_for_llm = convert_tools_to_openai_format(deserialized_tools)
            self.logger.info(f"Loaded {len(self.available_tools_for_llm)} tools from cache for LLM.")
            return self.available_tools_for_llm

        self.logger.info("Fetching tools from MCP and updating cache.")
        try:
            live_tools = self.additional_tools
            if self.mcp_client:
                live_tools += await self.mcp_client.get_tools(server_name=server_name)
            self._raw_available_tools_from_mcp = {tool.name: tool for tool in live_tools}

            serialized_tools = []
            for tool in live_tools:
                try:
                    schema = tool.args_schema.model_json_schema()
                except Exception:
                    schema = tool.args_schema
                serialized_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema,
                    "metadata": tool.metadata,
                })

            if self.llm_cache:
                await self.llm_cache.aset_value(
                    self.cache_key,
                    serialized_tools, 
                    self.TOOL_CACHE_EXPIRATION_SECONDS
                )
                self.logger.info(f"Tools fetched from MCP and saved to cache for key: {self.cache_key}.")
            else:
                self.logger.info("Tools fetched from MCP but caching is disabled.")


            self.available_tools_for_llm = convert_tools_to_openai_format(live_tools)
            self.logger.info(f"Prepared {len(self.available_tools_for_llm)} tools for LLM after MCP fetch.")
            return self.available_tools_for_llm

        except Exception as e:
            self.logger.error(f"Failed to fetch or cache tools from MCP: {e}", exc_info=True)
            self.available_tools_for_llm = []
            return []

    def _get_openai_tools_format(self) -> List[ChatCompletionToolParam]:
        return self.available_tools_for_llm

    async def chat_completion_with_tools(self, user_message_content: str, stream: bool = True) -> AsyncGenerator[Tuple[str, Any], None]:
        self.logger.debug(f"Current conversation history: {self.conversation_history}")

        if self.system_prompt_content:
            if not any(msg.get("role") == "system" for msg in self.conversation_history if isinstance(msg, dict)):
                self.conversation_history.insert(0, ChatCompletionSystemMessageParam(role="system", content=self.system_prompt_content))
                self.logger.debug("Added system prompt to conversation history.")
            else:
                self.logger.debug("System prompt already present.")

        last_message = self.conversation_history[-1] if self.conversation_history else None
        if not last_message or not (isinstance(last_message, dict) and last_message.get("role") == "user" and last_message.get("content") == user_message_content):
            self.conversation_history.append(ChatCompletionUserMessageParam(role="user", content=user_message_content))
            self.logger.debug("Appended new user message to history.")
        else:
            self.logger.debug("User message already present or identical, skipping append.")

        self.logger.debug(f"System Prompt: {self.system_prompt_content}")
        self.logger.debug(f"Messages to send to LLM: {self.conversation_history}")

        iteration_count = 0
        max_iterations = 15

        if not self.available_tools_for_llm:
            await self.load_tools()
            self.logger.info("Tools loaded for the first time in this session.")

        while iteration_count < max_iterations:
            iteration_count += 1
            self.logger.info(f"LLM Chat Completion Loop Iteration: {iteration_count}")

            tools_for_llm = self._get_openai_tools_format()
            
            try:
                response_stream = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.conversation_history,
                    tools=tools_for_llm if tools_for_llm else NOT_GIVEN,
                    tool_choice="auto",
                    stream=True,
                    temperature=self.temperature
                )

                accumulated_assistant_content = ""
                accumulated_tool_calls_raw: List[Dict[str, Any]] = []
                accumulated_reasoning = ""
                has_tool_calls_in_current_response = False
                has_content_in_current_response = False

                async for chunk in response_stream:
                    if stream:
                        yield ("chunk", chunk)

                    delta = chunk.choices[0].delta

                    if delta.content:
                        accumulated_assistant_content += delta.content
                        has_content_in_current_response = True
                        if stream:
                            yield ("messages", (AIMessageChunk(content=delta.content), {}))

                    if hasattr(delta, "reasoning") and delta.reasoning:
                        accumulated_reasoning += delta.reasoning
                        if stream:
                            yield ("reasoning_chunk", AIMessageChunk(content="", reasoning=delta.reasoning))

                    if delta.tool_calls:
                        has_tool_calls_in_current_response = True
                        for new_tool_call_obj in delta.tool_calls:
                            index = new_tool_call_obj.index

                            while len(accumulated_tool_calls_raw) <= index:
                                accumulated_tool_calls_raw.append({
                                    "id": f"call_{uuid.uuid4().hex}",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })

                            current_tool_call = accumulated_tool_calls_raw[index]

                            if new_tool_call_obj.id:
                                current_tool_call["id"] = new_tool_call_obj.id
                            if new_tool_call_obj.type:
                                current_tool_call["type"] = new_tool_call_obj.type

                            if new_tool_call_obj.function:
                                if new_tool_call_obj.function.name:
                                    current_tool_call["function"]["name"] = new_tool_call_obj.function.name
                                if new_tool_call_obj.function.arguments:
                                    current_tool_call["function"]["arguments"] += new_tool_call_obj.function.arguments

                final_tool_calls_list: List[ChatCompletionMessageToolCall] = []
                for tc_dict in accumulated_tool_calls_raw:
                    try:
                        json.loads(tc_dict["function"]["arguments"])
                    except json.JSONDecodeError:
                        self.logger.warning(f"Malformed JSON arguments from LLM for tool call '{tc_dict.get('id', 'N/A')}': {tc_dict['function']['arguments']}. Defaulting to empty object string.", exc_info=True)
                        tc_dict["function"]["arguments"] = "{}"

                    final_tool_calls_list.append(
                        ChatCompletionMessageToolCall(
                            id=tc_dict["id"],
                            type="function",
                            function={
                                "name": tc_dict["function"]["name"],
                                "arguments": tc_dict["function"]["arguments"]
                            }
                        )
                    )

                full_response_message: ChatCompletionAssistantMessageParam = ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=accumulated_assistant_content if accumulated_assistant_content else None,
                    tool_calls=final_tool_calls_list if final_tool_calls_list else None
                )

                self.conversation_history.append(full_response_message)
                self.logger.debug(f"Appended assistant message to history: {full_response_message}")

                tool_calls_from_response = full_response_message.get("tool_calls")

                if tool_calls_from_response:
                    tool_outputs_messages: List[ChatCompletionToolMessageParam] = []
                    self.logger.info(f"LLM requested tool calls: {tool_calls_from_response}")

                    for tool_call in tool_calls_from_response:
                        tool_name = tool_call.function.name
                        tool_args_str = tool_call.function.arguments
                        tool_call_id = tool_call.id

                        try:
                            tool_arguments = json.loads(tool_args_str)
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Malformed JSON arguments for tool '{tool_name}': {tool_args_str}. Error: {e}", exc_info=True)
                            error_content = f"Error: Malformed JSON arguments for tool '{tool_name}'. Arguments must be valid JSON."
                            tool_outputs_messages.append(
                                ChatCompletionToolMessageParam(
                                    role="tool",
                                    tool_call_id=tool_call_id,
                                    content=error_content
                                )
                            )
                            if stream:
                                yield ("tool_output_chunk_error", AIMessageChunk(content=error_content, status="error", name=tool_name))
                            continue

                        tool_to_execute = next((t for t in self._raw_available_tools_from_mcp.values() if t.name == tool_name), None)

                        if tool_to_execute:
                            self.logger.info(f"Executing tool: {tool_name} with args: {tool_arguments}")
                            tool_full_output_content = ""
                            try:
                                raw_tool_output = await tool_to_execute.call(tool_arguments)
                                
                                if isinstance(raw_tool_output, tuple) and len(raw_tool_output) > 0:
                                    tool_full_output_content = str(raw_tool_output[0])
                                else:
                                    tool_full_output_content = str(raw_tool_output)
                                
                                self.logger.debug(f"Tool '{tool_name}' output (first 200 chars): {tool_full_output_content[:200]}...")
                                if stream:
                                    yield ("tool_output_chunk", AIMessageChunk(content=tool_full_output_content, name=tool_name))

                            except Exception as tool_e:
                                self.logger.error(f"Error during tool execution for {tool_name}: {tool_e}", exc_info=True)
                                tool_full_output_content = f"Error executing tool '{tool_name}': {tool_e}"
                                if stream:
                                    yield ("tool_output_chunk_error", AIMessageChunk(content=tool_full_output_content, status="error", name=tool_name))
                            
                            tool_outputs_messages.append(
                                ChatCompletionToolMessageParam(
                                    role="tool",
                                    tool_call_id=tool_call_id,
                                    content=tool_full_output_content
                                )
                            )
                        else:
                            error_content = f"Error: Tool '{tool_name}' not found. Ensure tool is correctly loaded in MCP."
                            self.logger.error(error_content)
                            tool_outputs_messages.append(
                                ChatCompletionToolMessageParam(
                                    role="tool",
                                    tool_call_id=tool_call_id,
                                    content=error_content
                                )
                            )
                            if stream:
                                yield ("tool_output_chunk_error", AIMessageChunk(content=error_content, status="error", name=tool_name))

                    self.conversation_history.extend(tool_outputs_messages)
                    self.logger.debug(f"Appended tool outputs to history. Current history length: {len(self.conversation_history)}")

                else:
                    if accumulated_assistant_content:
                        self.logger.info("LLM provided content and no tool calls. Breaking loop.")
                        yield ("values", self.conversation_history)
                        break
                    else:
                        self.logger.warning("LLM response had no tool calls and no content. Continuing loop, model might be stuck.")

            except Exception as e:
                self.logger.error(f"Critical Error during LLMClientWrapper chat completion: {e}", exc_info=True)
                yield ("error", str(e))
                break

        if iteration_count >= max_iterations:
            self.logger.warning(f"LLMClientWrapper recursion limit ({max_iterations}) reached without a final answer.")
            yield ("error", f"Recursion limit reached without a final answer. Max iterations: {max_iterations}. Please refine your prompt or tools.")
