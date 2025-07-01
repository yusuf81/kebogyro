import asyncio
import json
import time
import logging
import inspect
import aiohttp
import uuid
import async_timeout
from typing import Dict, Any, List, Union, AsyncGenerator, Tuple, Optional, Callable
from datetime import datetime
from .wrapper import LLMClientWrapper
from .mcp_adapter.client import BBServerMCPClient
from .mcp_adapter.tools import SimpleTool
from .messages import HumanMessage, AIMessage, AIMessageChunk

from openai.types.chat import (
    ChatCompletionMessageParam, ChatCompletionUserMessageParam
)

import logging 
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class BBAgentExecutor:
    def __init__(self, 
        llm_client: LLMClientWrapper, 
        tools: Optional[List[SimpleTool]] = None, 
        mcp_tools: Optional[BBServerMCPClient] = None, 
        system_prompt: Optional[str] = None, 
        stream: bool = True):

        self.llm_client = llm_client
        self.tools = tools if tools is not None else []
        self.llm_client.additional_tools = self.tools
        self.llm_client.mcp_client = mcp_tools
        self.system_prompt = system_prompt
        if self.system_prompt and not self.llm_client.system_prompt_content:
            self.llm_client.system_prompt_content = self.system_prompt
        self.stream = stream

    async def astream(self, input_messages: Dict[str, Any], stream_mode: List[str], config: Dict, debug: bool = False) -> AsyncGenerator:
        user_message_content = ""
        logger.info(f"PROCESSING INPUT MESSAGE: {input_messages}")

        if "messages" in input_messages and isinstance(input_messages["messages"], list):
            processed_history_for_llm_client: List[ChatCompletionMessageParam] = []
            final_user_message_from_history = None

            for msg in input_messages["messages"]:
                if isinstance(msg, dict):
                    processed_history_for_llm_client.append(msg)
                    if msg.get("role") == "user":
                        content_data = msg.get("content")
                        if isinstance(content_data, str):
                            final_user_message_from_history = content_data
                        elif isinstance(content_data, list):
                            for item in content_data:
                                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                                    final_user_message_from_history = item["text"]
                                    break
                elif isinstance(msg, HumanMessage):
                    if msg.role == "user":
                        if isinstance(msg.content, str):
                            processed_history_for_llm_client.append(ChatCompletionUserMessageParam(role="user", content=msg.content))
                            final_user_message_from_history = msg.content
                        elif isinstance(msg.content, list):
                            temp_content_list = []
                            for item in msg.content:
                                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                                    temp_content_list.append(item)
                                    final_user_message_from_history = item["text"]
                            processed_history_for_llm_client.append(ChatCompletionUserMessageParam(role="user", content=temp_content_list))
                else:
                    logger.warning(f"Unknown message type in input_messages: {type(msg)}")

            user_message_content = final_user_message_from_history or user_message_content
            self.llm_client.conversation_history = processed_history_for_llm_client
            
        if not user_message_content:
            logger.error("No valid user message found after checking all messages.")
            yield ("error", "No valid user message found in input_messages for astream.")
            return

        try:
            async for item_type, data in self.llm_client.chat_completion_with_tools(user_message_content, stream=self.stream):
                if debug:
                    logger.debug(f"BBAgentExecutor astream emitting: Type={item_type}, Data={data}")

                if item_type == "messages": 
                    if isinstance(data, tuple) and len(data) > 0 and isinstance(data[0], AIMessageChunk):
                        message_data: AIMessageChunk = data[0]
                        yield ("messages", (message_data, {})) 
                    else:
                        logger.error(f"Invalid message data format for 'messages' chunk_type. Expected (AIMessageChunk, {{}}), got: {data}")

                elif item_type == "reasoning_chunk":
                    if isinstance(data, AIMessageChunk):
                        yield ("messages", (data, {})) 
                    else:
                        logger.error(f"Invalid message data format for 'reasoning_chunk'. Expected AIMessageChunk, got: {data}")

                elif item_type == "tool_output_chunk": 
                    if isinstance(data, AIMessageChunk):
                        yield ("messages", (data, {}))
                    else:
                        logger.error(f"Invalid message data format for 'tool_output_chunk'. Expected AIMessageChunk, got: {data}")

                elif item_type == "tool_output_chunk_error":
                    if isinstance(data, AIMessageChunk):
                        yield ("messages", (data, {}))
                    else:
                        logger.error(f"Invalid message data format for 'tool_output_chunk_error'. Expected AIMessageChunk, got: {data}")

                elif item_type == "chunk": 
                    yield ("chunk", data) 

                elif item_type == "values": 
                    if "values" in stream_mode: 
                        yield ("values", data)
                elif item_type == "error":
                    logger.error(f"Error received from LLMClientWrapper: {data}")
                    yield ("error", data)
                    return
        except Exception as e:
            logger.error(f"Unhandled error in BBAgentExecutor astream loop: {e}", exc_info=True)
            yield ("error", str(e))
            return

def create_agent(
        llm_client: LLMClientWrapper, 
        tools: Optional[List[SimpleTool]], 
        mcp_tools: Optional[BBServerMCPClient], 
        system_prompt: str, 
        stream: bool) -> BBAgentExecutor:    
    return BBAgentExecutor(
        llm_client=llm_client, 
        tools=tools, 
        mcp_tools=mcp_tools,
        system_prompt=system_prompt, 
        stream=stream)        