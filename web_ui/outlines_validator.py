"""Outlines-based validation system to replace manual validation."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from collections import Counter
import json
import os

try:
    import outlines
    OUTLINES_AVAILABLE = True
except ImportError:
    OUTLINES_AVAILABLE = False

from .outlines_models import (
    ConfigValidationResult,
    ToolCallResult,
    ChatResponse,
    CodeAssistanceResponse,
    ContentFilterResult,
    StreamingChunk,
    MultiPathValidation,
    AgentStep,
    DebugInfo,
    ValidationMode
)

logger = logging.getLogger(__name__)


class OutlinesValidator:
    """Outlines-based validator to replace manual validation spaghetti."""
    
    def __init__(self, model_name: str = "llama3", use_ollama: bool = True):
        """Initialize validator with model."""
        self.model_name = model_name
        self.use_ollama = use_ollama
        self._model = None
        self._generators = {}
        
        if not OUTLINES_AVAILABLE:
            logger.warning("Outlines library not available. Falling back to manual validation.")
    
    def _get_model(self):
        """Get or create model instance."""
        if self._model is None and OUTLINES_AVAILABLE:
            try:
                if self.use_ollama:
                    # Use Ollama model - correct import and usage
                    import outlines
                    self._model = outlines.models.ollama(self.model_name)
                else:
                    # Use OpenAI-compatible model
                    import outlines
                    self._model = outlines.models.openai(self.model_name)
                    
                logger.info(f"Initialized Outlines model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Outlines model: {e}")
                logger.info("Falling back to manual validation")
                self._model = None
        
        return self._model
    
    def _get_generator(self, schema_class):
        """Get or create generator for schema."""
        schema_name = schema_class.__name__
        
        if schema_name not in self._generators:
            model = self._get_model()
            if model is not None and OUTLINES_AVAILABLE:
                try:
                    import outlines
                    self._generators[schema_name] = outlines.generate.json(model, schema_class)
                    logger.debug(f"Created generator for {schema_name}")
                except Exception as e:
                    logger.error(f"Failed to create generator for {schema_name}: {e}")
                    logger.info("Using manual validation fallback")
                    self._generators[schema_name] = None
            else:
                self._generators[schema_name] = None
        
        return self._generators[schema_name]
    
    def validate_config(self, config_data: Dict[str, Any]) -> ConfigValidationResult:
        """Validate configuration using Outlines."""
        generator = self._get_generator(ConfigValidationResult)
        
        if generator is None:
            # Fallback to manual validation
            return self._manual_config_validation(config_data)
        
        try:
            # Create prompt for config validation
            prompt = f"""
            Validate this configuration and return a structured result:
            
            Config data: {json.dumps(config_data, indent=2)}
            
            Requirements:
            - api_base must start with http:// or https://
            - temperature must be between 0.0 and 2.0
            - All required fields must be present
            
            Return structured validation result:
            """
            
            result = generator(prompt)
            logger.info(f"Config validation result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Outlines config validation failed: {e}")
            return self._manual_config_validation(config_data)
    
    def _manual_config_validation(self, config_data: Dict[str, Any]) -> ConfigValidationResult:
        """Manual fallback for config validation."""
        try:
            # Apply basic validation with None handling
            api_base = config_data.get("api_base") or ""
            if api_base and not api_base.startswith(("http://", "https://")):
                raise ValueError("API base must start with http:// or https://")
            
            temperature = float(config_data.get("temperature", 0.1))
            if not (0.0 <= temperature <= 2.0):
                raise ValueError("Temperature must be between 0.0 and 2.0")
            
            # Ensure no None values
            safe_api_base = api_base or "http://localhost:11434/v1"
            safe_api_key = config_data.get("api_key") or "***"
            safe_model_name = config_data.get("model_name") or "unknown"
            safe_provider = config_data.get("provider") or "ollama"
            
            return ConfigValidationResult(
                status="valid",
                api_base=safe_api_base,
                api_key=safe_api_key,
                model_name=safe_model_name,
                temperature=temperature,
                provider=safe_provider
            )
        except Exception as e:
            # For invalid configs, use safe defaults to avoid Pydantic validation errors
            safe_api_base = config_data.get("api_base") or ""
            if not safe_api_base or not safe_api_base.startswith(("http://", "https://")):
                safe_api_base = "http://localhost:11434/v1"  # Safe default
            
            return ConfigValidationResult(
                status="invalid",
                api_base=safe_api_base,
                api_key="***",
                model_name=config_data.get("model_name") or "unknown",
                temperature=0.1,
                provider=config_data.get("provider") or "ollama",
                errors=[str(e)]
            )
    
    def filter_content(self, content: str, context: str = "general") -> ContentFilterResult:
        """Filter content using Outlines structured generation."""
        generator = self._get_generator(ContentFilterResult)
        
        if generator is None:
            return self._manual_content_filtering(content, context)
        
        try:
            prompt = f"""
            Analyze this content and determine if it should be filtered:
            
            Content: {content}
            Context: {context}
            
            Filter criteria:
            - Tool call JSON (contains "name", "arguments", tool-related patterns)
            - Markdown code blocks with tool calls
            - Internal system messages
            
            Return structured filter result:
            """
            
            result = generator(prompt)
            logger.debug(f"Content filter result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Outlines content filtering failed: {e}")
            return self._manual_content_filtering(content, context)
    
    def _manual_content_filtering(self, content: str, context: str) -> ContentFilterResult:
        """Manual fallback for content filtering."""
        # Simple heuristic-based filtering
        content_lower = content.lower()
        
        # Check for tool call patterns
        tool_patterns = ['"name"', '"arguments"', 'tool', 'function']
        has_tool_pattern = any(pattern in content_lower for pattern in tool_patterns)
        
        # Check for JSON structure
        is_json_like = content.strip().startswith('{') and content.strip().endswith('}')
        
        should_filter = has_tool_pattern and is_json_like
        
        return ContentFilterResult(
            original_content=content,
            filtered_content="" if should_filter else content,
            was_filtered=should_filter,
            filter_reason="Tool call JSON detected" if should_filter else None,
            confidence=0.8 if should_filter else 0.9
        )
    
    def create_streaming_chunk(self, content: str, chunk_type: str = "text") -> StreamingChunk:
        """Create validated streaming chunk."""
        # Determine if should display
        should_display = chunk_type not in ["tool_call", "filtered"]
        
        # Cast to proper literal type
        valid_chunk_type = chunk_type if chunk_type in ["text", "code", "tool_call", "filtered"] else "text"
        
        return StreamingChunk(
            content=content,
            chunk_type=valid_chunk_type,  # type: ignore
            should_display=should_display
        )
    
    def multi_path_validation(self, validation_func, *args, attempts: int = 3, **kwargs) -> MultiPathValidation:
        """Perform multi-path validation with consensus."""
        results = []
        
        for i in range(attempts):
            try:
                result = validation_func(*args, **kwargs)
                results.append({
                    "attempt": i + 1,
                    "result": result,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "attempt": i + 1,
                    "error": str(e),
                    "success": False
                })
        
        # Find consensus
        successful_results = [r for r in results if r.get("success")]
        if successful_results:
            # Use most common result
            result_values = [r["result"] for r in successful_results]
            consensus = Counter(result_values).most_common(1)[0][0]
            confidence = len(successful_results) / attempts
        else:
            # All failed
            consensus = {"error": "All validation attempts failed"}
            confidence = 0.0
        
        return MultiPathValidation(
            attempts=results,
            consensus=consensus,
            confidence=confidence
        )
    
    def create_agent_step(self, action: str, content: str, **kwargs) -> AgentStep:
        """Create validated agent step."""
        # Cast to proper literal type
        valid_action = action if action in ["thought", "tool_call", "result", "finish"] else "thought"
        
        return AgentStep(
            action=valid_action,  # type: ignore
            content=content,
            **kwargs
        )
    
    def create_debug_info(self) -> DebugInfo:
        """Create debug info collector."""
        return DebugInfo()


class OutlinesStreamProcessor:
    """Process streaming content using Outlines validation."""
    
    def __init__(self, validator: OutlinesValidator):
        self.validator = validator
        self.debug_info = validator.create_debug_info()
    
    async def process_chat_stream(self, stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """Process chat stream with validation."""
        async for chunk in stream:
            # Chat mode: minimal filtering
            chunk_result = self.validator.create_streaming_chunk(chunk, "text")
            
            if chunk_result.should_display:
                self.debug_info.add_processed_chunk(chunk)
                yield chunk
    
    async def process_code_stream(self, stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """Process code assistance stream with validation."""
        async for chunk in stream:
            self.debug_info.add_raw_chunk(chunk)
            
            # Filter content
            filter_result = self.validator.filter_content(chunk, "code_assistance")
            
            if not filter_result.was_filtered and filter_result.filtered_content:
                chunk_result = self.validator.create_streaming_chunk(
                    filter_result.filtered_content, 
                    "text"
                )
                
                if chunk_result.should_display:
                    self.debug_info.add_processed_chunk(filter_result.filtered_content)
                    yield filter_result.filtered_content
            else:
                # Content was filtered
                filtered_chunk = self.validator.create_streaming_chunk(
                    chunk,
                    "filtered"
                )
                logger.debug(f"Filtered chunk: {chunk}")


# Global validator instance
_validator_instance = None


def get_validator() -> OutlinesValidator:
    """Get global validator instance."""
    global _validator_instance
    
    if _validator_instance is None:
        model_name = os.getenv("KBG_OLLAMA_MODEL", "llama3")
        _validator_instance = OutlinesValidator(model_name=model_name)
    
    return _validator_instance


def get_stream_processor() -> OutlinesStreamProcessor:
    """Get stream processor instance."""
    validator = get_validator()
    return OutlinesStreamProcessor(validator)


# Convenience functions for backward compatibility
def validate_config(config_data: Dict[str, Any]) -> ConfigValidationResult:
    """Validate configuration."""
    return get_validator().validate_config(config_data)


def filter_content(content: str, context: str = "general") -> ContentFilterResult:
    """Filter content."""
    return get_validator().filter_content(content, context)


def create_streaming_chunk(content: str, chunk_type: str = "text") -> StreamingChunk:
    """Create streaming chunk."""
    return get_validator().create_streaming_chunk(content, chunk_type)


def multi_path_validation(validation_func, *args, attempts: int = 3, **kwargs) -> MultiPathValidation:
    """Perform multi-path validation."""
    return get_validator().multi_path_validation(validation_func, *args, attempts=attempts, **kwargs)