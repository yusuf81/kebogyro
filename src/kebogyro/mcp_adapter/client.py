import asyncio
import logging
import json
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Any, AsyncIterator, Dict, List, Optional

from ..cache import AbstractLLMCache 

from datetime import datetime, timedelta, timezone

from mcp import ClientSession
from mcp.types import Tool as MCPTool 

from .prompts import load_mcp_prompt
from .resources import load_mcp_resources
from .sessions import (
    Connection,
    McpHttpClientFactory,
    SSEConnection,
    StdioConnection,
    StreamableHttpConnection,
    WebsocketConnection,
    create_session,
)

from .utils import _get_connection_hash, _get_all_connections_hash 
from .tools import load_mcp_tools, SimpleTool, convert_mcp_tool_to_simple_tool, _list_all_tools


logger = logging.getLogger(__name__)

ASYNC_CONTEXT_MANAGER_ERROR = (
    "BBServerMCPClient cannot be used as a context manager.\n"
    "Instead, use it like:\n"
    "client = BBServerMCPClient(...)\n"
    "tools = await client.get_tools()\n"
    "or\n"
    "async with client.session(server_name) as session: tools = await load_mcp_tools(session)"
)

DEFAULT_TOOL_CACHE_EXPIRATION_SECONDS = 300

class BBServerMCPClient:
    def __init__(
        self,
        connections: dict[str, Connection] | None = None,
        tool_cache_expiration_seconds: int = DEFAULT_TOOL_CACHE_EXPIRATION_SECONDS,
        cache_adapter: Optional[AbstractLLMCache] = None,
    ) -> None:
        self.connections: dict[str, Connection] = connections if connections is not None else {}
        self.tool_cache_expiration_seconds = tool_cache_expiration_seconds
        self.cache_adapter = cache_adapter
        
        self._connection_name_map: Dict[str, Connection] = {name: conn for name, conn in self.connections.items()}


    @asynccontextmanager
    async def session(
        self,
        server_name: str,
        *,
        auto_initialize: bool = True,
    ) -> AsyncIterator[ClientSession]:
        if server_name not in self.connections:
            raise ValueError(
                f"Couldn't find a server with name '{server_name}', expected one of '{list(self.connections.keys())}'"
            )

        async with create_session(self.connections[server_name]) as session:
            if auto_initialize:
                logger.debug(f"Initializing session for {server_name}")
                await session.initialize()
            yield session

    async def get_tools(self, *, server_name: str | None = None) -> list[SimpleTool]:
        cache_key_prefix = "mcp_tools"
        
        if server_name is not None:
            if server_name not in self.connections:
                raise ValueError(f"Connection '{server_name}' not found in client configuration.")
            
            conn_config = self.connections[server_name]
            conn_hash = _get_connection_hash(conn_config)
            cache_key = f"{cache_key_prefix}:{server_name}:{conn_hash}"
            connections_to_fetch = {server_name: conn_config}
        else:
            all_conns_hash = _get_all_connections_hash(self.connections)
            cache_key = f"{cache_key_prefix}:all_connections:{all_conns_hash}"
            connections_to_fetch = self.connections

        cached_mcp_tools_data: Optional[Dict[str, Any]] = None

        if self.cache_adapter:
            is_expired = await self.cache_adapter.is_expired(cache_key, self.tool_cache_expiration_seconds)
            if not is_expired:
                cached_mcp_tools_data = await self.cache_adapter.aget_value(cache_key)
                if cached_mcp_tools_data:
                    logger.info(f"Retrieved raw MCPTool data from cache for key: {cache_key}")
                    try:
                        all_deserialized_simple_tools = []
                        for conn_name, raw_mcp_tools_list in cached_mcp_tools_data.items():
                            connection_for_tool_recreation = self._connection_name_map.get(conn_name)
                            if not connection_for_tool_recreation:
                                logger.warning(f"Connection config '{conn_name}' not found for cached tools. Skipping.")
                                continue
                            
                            deserialized_mcp_tools = [MCPTool.model_validate(raw) for raw in raw_mcp_tools_list]
                            
                            for mcp_tool in deserialized_mcp_tools:
                                all_deserialized_simple_tools.append(
                                    convert_mcp_tool_to_simple_tool(None, mcp_tool, connection=connection_for_tool_recreation)
                                )
                        logger.info(f"Successfully deserialized {len(all_deserialized_simple_tools)} tools from cache.")
                        return all_deserialized_simple_tools
                    except Exception as e:
                        logger.error(f"Failed to deserialize or re-create SimpleTools from cache for {cache_key}: {e}")
            else:
                logger.info(f"Cache for {cache_key} is expired or not found. Fetching from MCP.")
        else:
            logger.info("No cache adapter provided. Fetching tools directly from MCP.")


        fetched_mcp_tools_by_connection: Dict[str, List[MCPTool]] = {}
        all_simple_tools: List[SimpleTool] = []

        load_mcp_tool_tasks = []
        for conn_name, connection in connections_to_fetch.items():
            logger.info(f"PROCESSING {conn_name} -- {connection}")
            async def _fetch_and_convert(cn: str, conn: Connection):
                async with self.session(cn) as list_session:
                    mcp_tools = await _list_all_tools(list_session)
                    logger.info(f"GET TOOLS {mcp_tools}")
                    fetched_mcp_tools_by_connection[cn] = mcp_tools 
                    
                    converted_simple_tools = []
                    for mcp_tool in mcp_tools:
                        converted_simple_tools.append(
                            convert_mcp_tool_to_simple_tool(list_session, mcp_tool, connection=conn)
                        )
                    return converted_simple_tools
            
            load_mcp_tool_tasks.append(asyncio.create_task(_fetch_and_convert(conn_name, connection)))
        
        list_of_simple_tool_lists = await asyncio.gather(*load_mcp_tool_tasks)
        for simple_tool_list in list_of_simple_tool_lists:
            all_simple_tools.extend(simple_tool_list)

        if self.cache_adapter:
            try:
                serializable_data = {}
                for conn_name, mcp_tools_list in fetched_mcp_tools_by_connection.items():
                    serializable_data[conn_name] = [tool.model_dump() for tool in mcp_tools_list] 
                
                await self.cache_adapter.aset_value(
                    key=cache_key,
                    value=serializable_data,
                    expiry_seconds=self.tool_cache_expiration_seconds
                )
                logger.info(f"Stored raw MCPTool data in database cache for key: {cache_key}.")
            except Exception as e:
                logger.error(f"Failed to store raw MCPTool data in cache for {cache_key}: {e}")

        return all_simple_tools


    async def get_prompt(
        self, server_name: str, prompt_name: str, *, arguments: dict[str, Any] | None = None
    ) -> list[Any]:
        async with self.session(server_name) as session:
            prompt = await load_mcp_prompt(session, prompt_name, arguments=arguments)
            return prompt

    async def get_resources(
        self, server_name: str, *, uris: str | list[str] | None = None
    ) -> list[Any]:
        async with self.session(server_name) as session:
            resources = await load_mcp_resources(session, uris=uris)
            return resources

    async def __aenter__(self) -> "BBServerMCPClient":
        raise NotImplementedError(ASYNC_CONTEXT_MANAGER_ERROR)

    def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError(ASYNC_CONTEXT_MANAGER_ERROR)


__all__ = [
    "BBServerMCPClient",
    "McpHttpClientFactory",
    "SSEConnection",
    "StdioConnection",
    "StreamableHttpConnection",
    "WebsocketConnection",
]