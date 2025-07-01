import collections
import inspect
import logging
import types
import hashlib
import uuid
from contextlib import suppress
from typing import Annotated, Any, Callable, Literal, Optional, Union, cast, List, Dict

from pydantic import BaseModel
from pydantic.v1 import BaseModel as BaseModelV1
from typing_extensions import TypedDict, get_args, get_origin, is_typeddict
from .tools import SimpleTool
from .sessions import Connection
import json

logger = logging.getLogger(__name__)


__all__ = ["Connection", "_get_connection_hash", "_get_all_connections_hash"]


class FunctionDescription(TypedDict):
    name: str
    description: str
    parameters: dict


class ToolDescription(TypedDict):
    type: Literal["function"]
    function: FunctionDescription


def _rm_titles(kv: dict, prev_key: str = "") -> dict:
    new_kv = {}
    for k, v in kv.items():
        if k == "title" and not (isinstance(v, dict) and prev_key == "properties"):
            continue
        if isinstance(v, dict):
            new_kv[k] = _rm_titles(v, k)
        else:
            new_kv[k] = v
    return new_kv


def convert_pydantic_to_openai_function(
    model: type,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    rm_titles: bool = True,
) -> FunctionDescription:
    if hasattr(model, "model_json_schema"):
        schema = model.model_json_schema()
    elif hasattr(model, "schema"):
        schema = model.schema
    else:
        raise TypeError("Model must be a Pydantic model.")

    schema.pop("definitions", None)
    schema.pop("$defs", None)
    title = schema.pop("title", "")
    default_description = schema.pop("description", "")
    return {
        "name": name or title,
        "description": description or default_description,
        "parameters": _rm_titles(schema) if rm_titles else schema,
    }


def convert_pydantic_to_openai_tool(
    model: type[BaseModel],
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> ToolDescription:
    function = convert_pydantic_to_openai_function(model, name=name, description=description)
    return {"type": "function", "function": function}


def convert_to_json_schema(
    schema: Union[dict[str, Any], type[BaseModel]],
    *,
    strict: Optional[bool] = None,
) -> dict[str, Any]:
    if isinstance(schema, dict):
        return schema
    elif isinstance(schema, type) and issubclass(schema, BaseModel):
        fn = convert_pydantic_to_openai_function(schema)
        out = {"title": fn["name"], "description": fn["description"]}
        out.update(fn["parameters"])
        return out
    else:
        raise ValueError("Input must be a dict or pydantic.BaseModel subclass")


def convert_function_to_openai_description(function: Callable) -> FunctionDescription:
    func_name = function.__name__
    doc = inspect.getdoc(function) or ""

    sig = inspect.signature(function)
    parameters = {
        name: {
            "type": "string",
            "description": param.annotation.__name__ if param.annotation != inspect._empty else ""
        } for name, param in sig.parameters.items()
    }

    return {
        "name": func_name,
        "description": doc,
        "parameters": {
            "type": "object",
            "properties": parameters,
            "required": list(parameters.keys()),
        },
    }


def tool_example_to_messages(input: str, tool_calls: list[BaseModel], tool_outputs: Optional[list[str]] = None, ai_response: Optional[str] = None) -> list[dict]:
    messages = [{"role": "user", "content": input}]
    openai_tool_calls = [
        {
            "id": str(uuid.uuid4()),
            "type": "function",
            "function": {
                "name": call.__class__.__name__,
                "arguments": call.model_dump_json(),
            },
        }
        for call in tool_calls
    ]
    messages.append({"role": "assistant", "content": "", "tool_calls": openai_tool_calls})
    tool_outputs = tool_outputs or ["You have correctly called this tool."] * len(tool_calls)
    for output, call in zip(tool_outputs, openai_tool_calls):
        messages.append({"role": "tool", "content": output, "tool_call_id": call["id"]})
    if ai_response:
        messages.append({"role": "assistant", "content": ai_response})
    return messages


def convert_tools_to_openai_format(tools: List[SimpleTool]) -> List[Dict[str, Any]]:
    openai_tools = []
    for tool in tools:
        try:
            schema = tool.args_schema.model_json_schema()
        except:
            schema = tool.args_schema
        openai_tools.append({
            "type": "function",  
            "function": {     
                "name": tool.name,
                "description": tool.description,
                "parameters": schema,  
            }
        })
    return openai_tools

def _get_connection_hash(connection: Connection) -> str:
    hashable_parts = {}
    
    if 'transport' in connection:
        hashable_parts['transport'] = connection['transport']
    if 'url' in connection:
        hashable_parts['url'] = connection['url']
    
    if 'headers' in connection and connection['headers'] is not None:
        sorted_headers = sorted(connection['headers'].items())
        hashable_parts['headers'] = sorted_headers

    if connection.get('transport') == 'stdio':
        if 'command' in connection:
            hashable_parts['command'] = connection['command']
        if 'args' in connection:
            hashable_parts['args'] = connection['args']

    try:
        serialized = json.dumps(hashable_parts, sort_keys=True)
    except TypeError as e:
        logging.warning(f"Could not fully serialize connection for hashing: {connection}. Error: {e}")
        serialized = f"{connection.get('transport')}:{connection.get('url')}:{connection.get('command')}"

    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

def _get_all_connections_hash(connections: Dict[str, Connection]) -> str:
    """
    Generates a stable SHA256 hash representing the collection of all connections.
    Useful for caching the aggregated tools from multiple connections.
    """
    
    sorted_connection_names = sorted(connections.keys())
    
    all_hashes = []
    for conn_name in sorted_connection_names:
        conn = connections[conn_name]
        conn_hash = _get_connection_hash(conn)
        all_hashes.append(f"{conn_name}:{conn_hash}")
        
    combined_string = "|".join(all_hashes)
    return hashlib.sha256(combined_string.encode('utf-8')).hexdigest()