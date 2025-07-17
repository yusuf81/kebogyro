"""Outlines-based validation models for web UI."""

from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ConfigValidationResult(BaseModel):
    """Guaranteed valid configuration result."""
    status: Literal["valid", "invalid"] = "valid"
    api_base: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key (masked)")
    model_name: str = Field(..., description="Model name")
    temperature: float = Field(ge=0.0, le=2.0, description="Temperature between 0.0 and 2.0")
    provider: str = Field(..., description="LLM provider")
    errors: List[str] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Backward compatibility property."""
        return self.status == "valid"

    @property
    def missing_vars(self) -> List[str]:
        """Backward compatibility property."""
        missing = []
        if not self.api_base:
            missing.append("OPENAI_API_BASE")
        if not self.api_key or self.api_key == "***":
            missing.append("OPENAI_API_KEY")
        if not self.model_name:
            missing.append("KBG_OLLAMA_MODEL")
        return missing

    @field_validator('api_base')
    @classmethod
    def validate_api_base(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('API base must start with http:// or https://')
        return v


class ToolCallResult(BaseModel):
    """Guaranteed valid tool call result."""
    success: bool = Field(..., description="Whether tool call succeeded")
    tool_name: str = Field(..., min_length=1, description="Name of the tool called")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")
    result: Optional[str] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    is_filtered: bool = Field(default=False, description="Whether content was filtered")


class ChatResponse(BaseModel):
    """Guaranteed valid chat response."""
    content: str = Field(..., description="Response content")
    is_complete: bool = Field(..., description="Whether response is complete")
    contains_code: bool = Field(default=False, description="Whether response contains code")
    response_type: Literal["normal", "code", "error"] = "normal"


class CodeAssistanceResponse(BaseModel):
    """Guaranteed valid code assistance response."""
    content: str = Field(..., description="Response content")
    has_tool_calls: bool = Field(default=False, description="Whether response has tool calls")
    tool_calls: List[ToolCallResult] = Field(default_factory=list)
    is_complete: bool = Field(..., description="Whether response is complete")
    response_type: Literal["code", "explanation", "error"] = "code"


class ContentFilterResult(BaseModel):
    """Guaranteed valid content filter result."""
    original_content: str = Field(..., description="Original content")
    filtered_content: str = Field(..., description="Filtered content")
    was_filtered: bool = Field(..., description="Whether content was filtered")
    filter_reason: Optional[str] = Field(None, description="Reason for filtering")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in filtering decision")


class ToolCallDetection(BaseModel):
    """Structured tool call detection using Outlines."""
    is_tool_call: bool = Field(..., description="Whether content is a tool call")
    tool_name: Optional[str] = Field(None, description="Name of the tool if detected")
    arguments: Optional[Dict[str, Any]] = Field(None, description="Tool arguments if detected")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in detection")
    reasoning: str = Field(..., description="Explanation of the detection")
    should_filter: bool = Field(..., description="Whether this content should be filtered from UI")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        # Clamp confidence to valid range
        if v > 1.0:
            return 1.0
        elif v < 0.0:
            return 0.0
        return v


class StreamingChunk(BaseModel):
    """Guaranteed valid streaming chunk."""
    content: str = Field(..., description="Chunk content")
    chunk_type: Literal["text", "code", "tool_call", "filtered"] = "text"
    should_display: bool = Field(default=True, description="Whether to display to user")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationMode(str, Enum):
    """Validation modes for different contexts."""
    STRICT = "strict"
    PERMISSIVE = "permissive"
    DEVELOPMENT = "development"


class MultiPathValidation(BaseModel):
    """Multi-path validation result with consensus."""
    attempts: List[Dict[str, Any]] = Field(..., description="All validation attempts")
    consensus: Dict[str, Any] = Field(..., description="Consensus result")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in consensus")
    mode: ValidationMode = ValidationMode.STRICT

    @field_validator('attempts')
    @classmethod
    def validate_attempts(cls, v):
        if len(v) < 2:
            raise ValueError('Multi-path validation requires at least 2 attempts')
        return v


class AgentStep(BaseModel):
    """Agent step for ReAct pattern."""
    action: Literal["thought", "tool_call", "result", "finish"] = "thought"
    content: str = Field(..., description="Step content")
    tool_name: Optional[str] = Field(None, description="Tool name if tool_call")
    tool_args: Optional[Dict[str, Any]] = Field(None, description="Tool arguments if tool_call")
    reasoning: Optional[str] = Field(None, description="Reasoning for this step")
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class DebugInfo(BaseModel):
    """Debug information for development."""
    raw_chunks: List[str] = Field(default_factory=list)
    processed_chunks: List[str] = Field(default_factory=list)
    timing_info: List[Dict[str, Any]] = Field(default_factory=list)
    buffer_states: List[str] = Field(default_factory=list)
    total_raw_chars: int = Field(default=0)
    total_processed_chars: int = Field(default=0)

    def add_raw_chunk(self, chunk: str, timestamp: Optional[float] = None):
        """Add raw chunk with timestamp."""
        self.raw_chunks.append(chunk)
        self.total_raw_chars += len(chunk)
        if timestamp:
            self.timing_info.append({
                "type": "raw",
                "timestamp": timestamp,
                "chunk_size": len(chunk)
            })

    def add_processed_chunk(self, chunk: str, buffer_state: str = "", timestamp: Optional[float] = None):
        """Add processed chunk with buffer state."""
        self.processed_chunks.append(chunk)
        self.total_processed_chars += len(chunk)
        self.buffer_states.append(buffer_state)
        if timestamp:
            self.timing_info.append({
                "type": "processed",
                "timestamp": timestamp,
                "chunk_size": len(chunk)
            })

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "raw_chunks_count": len(self.raw_chunks),
            "processed_chunks_count": len(self.processed_chunks),
            "total_raw_chars": self.total_raw_chars,
            "total_processed_chars": self.total_processed_chars,
            "chars_difference": self.total_raw_chars - self.total_processed_chars,
            "processing_efficiency": (
                self.total_processed_chars / self.total_raw_chars
                if self.total_raw_chars > 0 else 0
            ),
            "raw_content": "".join(self.raw_chunks),
            "processed_content": "".join(self.processed_chunks)
        }
