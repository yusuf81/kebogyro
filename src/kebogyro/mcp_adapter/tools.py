from typing import Any, cast
from pydantic import BaseModel, create_model
import inspect
from mcp import ClientSession
from mcp.server.fastmcp.tools import Tool as FastMCPTool
from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase, FuncMetadata
from mcp.types import (
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    TextContent,
    Tool as MCPTool,
)

from .sessions import Connection, create_session

NonTextContent = ImageContent | EmbeddedResource
MAX_ITERATIONS = 1000


def _convert_call_tool_result(
    call_tool_result: CallToolResult,
) -> tuple[str | list[str], list[NonTextContent] | None]:
    text_contents: list[TextContent] = []
    non_text_contents = []
    for content in call_tool_result.content:
        if isinstance(content, TextContent):
            text_contents.append(content)
        else:
            non_text_contents.append(content)

    tool_content: str | list[str] = [content.text for content in text_contents]
    if not text_contents:
        tool_content = ""
    elif len(text_contents) == 1:
        tool_content = tool_content[0]

    if call_tool_result.isError:
        raise RuntimeError(tool_content)

    return tool_content, non_text_contents or None


async def _list_all_tools(session: ClientSession) -> list[MCPTool]:
    current_cursor: str | None = None
    all_tools: list[MCPTool] = []
    iterations = 0
    while True:
        iterations += 1
        if iterations > MAX_ITERATIONS:
            raise RuntimeError("Reached max of 1000 iterations while listing tools.")
        list_tools_page_result = await session.list_tools(cursor=current_cursor)
        if list_tools_page_result.tools:
            all_tools.extend(list_tools_page_result.tools)
        if list_tools_page_result.nextCursor is None:
            break
        current_cursor = list_tools_page_result.nextCursor
    return all_tools


class SimpleTool:
    def __init__(
        self,
        name: str,
        description: str,
        args_schema: type[BaseModel],
        coroutine: Any,
        metadata: dict[str, Any] | None = None,
    ):
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.coroutine = coroutine
        self.metadata = metadata or {}

    @classmethod
    def from_fn(cls, name: str, description: str, fn: callable, metadata: dict = None):
        sig = inspect.signature(fn)
        fields = {
            param.name: (param.annotation, ...)
            for param in sig.parameters.values()
            if param.annotation != inspect.Parameter.empty
        }
        ArgsModel = create_model(f"{name.title()}Args", **fields)
        return cls(name, description, ArgsModel, coroutine=fn, metadata=metadata)

    def openai_schema(self) -> dict:
        """Return OpenAI-compatible function/tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.args_schema.model_json_schema()
        }

    async def ainvoke(self, args: dict[str, Any]) -> Any:
        return await self.coroutine(**args)

    async def call(self, args: dict[str, Any]) -> Any:
        return await self.coroutine(**args)


def convert_mcp_tool_to_simple_tool(
    session: ClientSession | None,
    tool: MCPTool,
    *,
    connection: Connection | None = None,
) -> SimpleTool:
    if session is None and connection is None:
        raise ValueError("Either a session or a connection config must be provided")

    async def call_tool(**arguments: dict[str, Any]) -> tuple[str | list[str], list[NonTextContent] | None]:
        if session is None:
            async with create_session(connection) as tool_session:
                await tool_session.initialize()
                result = await cast(ClientSession, tool_session).call_tool(tool.name, arguments)
        else:
            result = await session.call_tool(tool.name, arguments)
        return _convert_call_tool_result(result)

    return SimpleTool(
        name=tool.name,
        description=tool.description or "",
        args_schema=tool.inputSchema,
        coroutine=call_tool,
        metadata=tool.annotations.model_dump() if tool.annotations else None,
    )


async def load_mcp_tools(
    session: ClientSession | None,
    *,
    connection: Connection | None = None,
) -> list[SimpleTool]:
    if session is None and connection is None:
        raise ValueError("Either a session or a connection config must be provided")

    if session is None:
        async with create_session(connection) as tool_session:
            await tool_session.initialize()
            tools = await _list_all_tools(tool_session)
    else:
        tools = await _list_all_tools(session)

    return [convert_mcp_tool_to_simple_tool(session, tool, connection=connection) for tool in tools]


def to_fastmcp(tool: SimpleTool) -> FastMCPTool:
    if not issubclass(tool.args_schema, BaseModel):
        raise ValueError("Tool args_schema must be a subclass of pydantic.BaseModel")

    parameters = tool.args_schema.model_json_schema()
    field_definitions = {
        field: (field_info.annotation, field_info)
        for field, field_info in tool.args_schema.model_fields.items()
    }
    arg_model = create_model(f"{tool.name}Arguments", **field_definitions, __base__=ArgModelBase)
    fn_metadata = FuncMetadata(arg_model=arg_model)

    async def fn(**arguments: dict[str, Any]) -> Any:
        return await tool.ainvoke(arguments)

    return FastMCPTool(
        fn=fn,
        name=tool.name,
        description=tool.description,
        parameters=parameters,
        fn_metadata=fn_metadata,
        is_async=True,
    )
