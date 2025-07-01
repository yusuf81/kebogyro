from typing import Any, Literal, Union
from dataclasses import dataclass

from mcp import ClientSession
from mcp.types import PromptMessage


@dataclass
class HumanMessage:
    content: str
    role: Literal["user"] = "user"


@dataclass
class AIMessage:
    content: str
    role: Literal["assistant"] = "assistant"


MessageType = Union[HumanMessage, AIMessage]


def convert_mcp_prompt_message_to_custom_message(
    message: PromptMessage,
) -> MessageType:
    if message.content.type == "text":
        if message.role == "user":
            return HumanMessage(content=message.content.text)
        elif message.role == "assistant":
            return AIMessage(content=message.content.text)
        else:
            raise ValueError(f"Unsupported prompt message role: {message.role}")

    raise ValueError(f"Unsupported prompt message content type: {message.content.type}")


async def load_mcp_prompt(
    session: ClientSession,
    name: str,
    *,
    arguments: dict[str, Any] | None = None
) -> list[MessageType]:
    response = await session.get_prompt(name, arguments)
    return [
        convert_mcp_prompt_message_to_custom_message(message)
        for message in response.messages
    ]
