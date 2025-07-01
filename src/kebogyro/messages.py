from typing import Dict, Any, List, Union, AsyncGenerator, Tuple, Optional, Callable

class HumanMessage:
    def __init__(self, content: Union[str, List[Dict[str, Any]]], role: str = "user"):
        self.content = content
        self.role = role

    def to_dict(self):
        return {"role": self.role, "content": self.content}

    def get(self, key, default=None):
        return getattr(self, key, default)

class AIMessageChunk:
    def __init__(self, content: str, reasoning: Optional[str] = None, status: Optional[str] = None, name: Optional[str] = None):
        self.content = content
        self.reasoning = reasoning
        self.status = status
        self.name = name

class AIMessage: 
    def __init__(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.role = "assistant"
    
    def to_dict(self):
        msg_dict: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            msg_dict["tool_calls"] = self.tool_calls
        return msg_dict

class ToolMessage: 
    def __init__(self, content: str, tool_call_id: str):
        self.content = content
        self.tool_call_id = tool_call_id
        self.role = "tool"
    
    def to_dict(self):
        return {"role": self.role, "content": self.content, "tool_call_id": self.tool_call_id}
