from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any, AsyncIterator, Literal, Protocol

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from typing_extensions import NotRequired, TypedDict

EncodingErrorHandler = Literal["strict", "ignore", "replace"]

DEFAULT_ENCODING = "utf-8"
DEFAULT_ENCODING_ERROR_HANDLER: EncodingErrorHandler = "strict"

DEFAULT_HTTP_TIMEOUT = 5
DEFAULT_SSE_READ_TIMEOUT = 60 * 5

DEFAULT_STREAMABLE_HTTP_TIMEOUT = timedelta(seconds=30)
DEFAULT_STREAMABLE_HTTP_SSE_READ_TIMEOUT = timedelta(seconds=60 * 5)


class McpHttpClientFactory(Protocol):
    def __call__(
        self,
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        auth: httpx.Auth | None = None,
    ) -> httpx.AsyncClient: ...


class StdioConnection(TypedDict):
    transport: Literal["stdio"]
    command: str
    args: list[str]
    env: dict[str, str] | None
    cwd: str | Path | None
    encoding: str
    encoding_error_handler: EncodingErrorHandler
    session_kwargs: dict[str, Any] | None


class SSEConnection(TypedDict):
    transport: Literal["sse"]
    url: str
    headers: dict[str, Any] | None
    timeout: float
    sse_read_timeout: float
    session_kwargs: dict[str, Any] | None
    httpx_client_factory: McpHttpClientFactory | None
    auth: NotRequired[httpx.Auth]


class StreamableHttpConnection(TypedDict):
    transport: Literal["streamable_http"]
    url: str
    headers: dict[str, Any] | None
    timeout: timedelta
    sse_read_timeout: timedelta
    terminate_on_close: bool
    session_kwargs: dict[str, Any] | None
    httpx_client_factory: McpHttpClientFactory | None
    auth: NotRequired[httpx.Auth]


class WebsocketConnection(TypedDict):
    transport: Literal["websocket"]
    url: str
    session_kwargs: dict[str, Any] | None


Connection = StdioConnection | SSEConnection | StreamableHttpConnection | WebsocketConnection


@asynccontextmanager
async def _create_stdio_session(
    *,
    command: str,
    args: list[str],
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    encoding: str = DEFAULT_ENCODING,
    encoding_error_handler: Literal["strict", "ignore", "replace"] = DEFAULT_ENCODING_ERROR_HANDLER,
    session_kwargs: dict[str, Any] | None = None,
) -> AsyncIterator[ClientSession]:
    env = env or {}
    if "PATH" not in env:
        env["PATH"] = os.environ.get("PATH", "")

    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=env,
        cwd=cwd,
        encoding=encoding,
        encoding_error_handler=encoding_error_handler,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write, **(session_kwargs or {})) as session:
            yield session


@asynccontextmanager
async def _create_sse_session(
    *,
    url: str,
    headers: dict[str, Any] | None = None,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    sse_read_timeout: float = DEFAULT_SSE_READ_TIMEOUT,
    session_kwargs: dict[str, Any] | None = None,
    httpx_client_factory: McpHttpClientFactory | None = None,
    auth: httpx.Auth | None = None,
) -> AsyncIterator[ClientSession]:
    kwargs = {}
    if httpx_client_factory is not None:
        kwargs["httpx_client_factory"] = httpx_client_factory

    async with sse_client(url, headers, timeout, sse_read_timeout, auth=auth, **kwargs) as (
        read,
        write,
    ):
        async with ClientSession(read, write, **(session_kwargs or {})) as session:
            yield session


@asynccontextmanager
async def _create_streamable_http_session(
    *,
    url: str,
    headers: dict[str, Any] | None = None,
    timeout: timedelta = DEFAULT_STREAMABLE_HTTP_TIMEOUT,
    sse_read_timeout: timedelta = DEFAULT_STREAMABLE_HTTP_SSE_READ_TIMEOUT,
    terminate_on_close: bool = True,
    session_kwargs: dict[str, Any] | None = None,
    httpx_client_factory: McpHttpClientFactory | None = None,
    auth: httpx.Auth | None = None,
) -> AsyncIterator[ClientSession]:
    kwargs = {}
    if httpx_client_factory is not None:
        kwargs["httpx_client_factory"] = httpx_client_factory

    async with streamablehttp_client(
        url, headers, timeout, sse_read_timeout, terminate_on_close, auth=auth, **kwargs
    ) as (read, write, _):
        async with ClientSession(read, write, **(session_kwargs or {})) as session:
            yield session


@asynccontextmanager
async def _create_websocket_session(
    *,
    url: str,
    session_kwargs: dict[str, Any] | None = None,
) -> AsyncIterator[ClientSession]:
    try:
        from mcp.client.websocket import websocket_client
    except ImportError:
        raise ImportError(
            "Could not import websocket_client. To use Websocket connections, install it via 'pip install mcp[ws]' or 'pip install websockets'"
        ) from None

    async with websocket_client(url) as (read, write):
        async with ClientSession(read, write, **(session_kwargs or {})) as session:
            yield session


@asynccontextmanager
async def create_session(
    connection: Connection,
) -> AsyncIterator[ClientSession]:
    if "transport" not in connection:
        raise ValueError(
            "Configuration error: Missing 'transport' key in server configuration. Each server must include 'transport' with one of: 'stdio', 'sse', 'websocket', 'streamable_http'."
        )

    transport = connection["transport"]
    if transport == "sse":
        if "url" not in connection:
            raise ValueError("'url' parameter is required for SSE connection")
        async with _create_sse_session(
            url=connection["url"],
            headers=connection.get("headers"),
            timeout=connection.get("timeout", DEFAULT_HTTP_TIMEOUT),
            sse_read_timeout=connection.get("sse_read_timeout", DEFAULT_SSE_READ_TIMEOUT),
            session_kwargs=connection.get("session_kwargs"),
            httpx_client_factory=connection.get("httpx_client_factory"),
            auth=connection.get("auth"),
        ) as session:
            yield session
    elif transport == "streamable_http":
        if "url" not in connection:
            raise ValueError("'url' parameter is required for Streamable HTTP connection")
        async with _create_streamable_http_session(
            url=connection["url"],
            headers=connection.get("headers"),
            timeout=connection.get("timeout", DEFAULT_STREAMABLE_HTTP_TIMEOUT),
            sse_read_timeout=connection.get("sse_read_timeout", DEFAULT_STREAMABLE_HTTP_SSE_READ_TIMEOUT),
            session_kwargs=connection.get("session_kwargs"),
            httpx_client_factory=connection.get("httpx_client_factory"),
            auth=connection.get("auth"),
        ) as session:
            yield session
    elif transport == "stdio":
        if "command" not in connection:
            raise ValueError("'command' parameter is required for stdio connection")
        if "args" not in connection:
            raise ValueError("'args' parameter is required for stdio connection")
        async with _create_stdio_session(
            command=connection["command"],
            args=connection["args"],
            env=connection.get("env"),
            cwd=connection.get("cwd"),
            encoding=connection.get("encoding", DEFAULT_ENCODING),
            encoding_error_handler=connection.get("encoding_error_handler", DEFAULT_ENCODING_ERROR_HANDLER),
            session_kwargs=connection.get("session_kwargs"),
        ) as session:
            yield session
    elif transport == "websocket":
        if "url" not in connection:
            raise ValueError("'url' parameter is required for Websocket connection")
        async with _create_websocket_session(
            url=connection["url"],
            session_kwargs=connection.get("session_kwargs"),
        ) as session:
            yield session
    else:
        raise ValueError(
            f"Unsupported transport: {transport}. Must be one of: 'stdio', 'sse', 'websocket', 'streamable_http'"
        )
