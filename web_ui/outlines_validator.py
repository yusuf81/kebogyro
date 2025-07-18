"""Outlines-based validation system to replace manual validation."""

import logging
from typing import Dict, Any, AsyncGenerator
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
    ContentFilterResult,
    ToolCallDetection,
    StreamingChunk,
    MultiPathValidation,
    AgentStep,
    DebugInfo
)

logger = logging.getLogger(__name__)


class OutlinesValidator:
    """Outlines-based validator using structured generation."""

    def __init__(self, model_name: str = "llama3", use_ollama: bool = True):
        """Initialize validator with model."""
        self.model_name = model_name
        self.use_ollama = use_ollama
        self._model = None
        self._generators = {}

        if not OUTLINES_AVAILABLE:
            raise ImportError("Outlines library is required for structured validation")

    def _get_model(self):
        """Get or create model instance."""
        if self._model is None:
            if self.use_ollama:
                # Use Ollama model - get URL from env
                import ollama
                api_base = os.getenv("OPENAI_API_BASE", "http://localhost:11434")
                # Remove /v1 suffix if present for ollama client
                if api_base.endswith('/v1'):
                    api_base = api_base[:-3]
                client = ollama.Client(host=api_base)
                self._model = outlines.from_ollama(client, self.model_name)
            else:
                # Use OpenAI-compatible model
                self._model = outlines.from_openai(self.model_name)

            logger.info(f"Initialized Outlines model: {self.model_name} at {api_base if self.use_ollama else 'OpenAI'}")

        return self._model

    def _get_generator(self, schema_class):
        """Get or create generator for schema."""
        schema_name = schema_class.__name__

        if schema_name not in self._generators:
            model = self._get_model()
            self._generators[schema_name] = outlines.Generator(model, schema_class)
            logger.debug(f"Created generator for {schema_name}")

        return self._generators[schema_name]

    def validate_config(self, config_data: Dict[str, Any]) -> ConfigValidationResult:
        """Validate configuration using Outlines structured generation."""
        generator = self._get_generator(ConfigValidationResult)

        # Create prompt for config validation
        prompt = f"""
        Validate this configuration and return a structured JSON result:

        Config data: {json.dumps(config_data, indent=2)}

        Requirements:
        - api_base must start with http:// or https://
        - temperature must be between 0.0 and 2.0
        - All required fields must be present

        Return JSON with these fields:
        - status: "valid" or "invalid"
        - api_base: the API base URL
        - api_key: the API key
        - model_name: the model name
        - temperature: the temperature value
        - provider: the provider name
        - errors: array of error messages (empty if valid)

        Analyze the config and return proper structured result:
        """

        result = generator(prompt)
        logger.info(f"Config validation result: {result}")

        # Parse the result if it's a string
        if isinstance(result, str):
            try:
                parsed = json.loads(result)
                return ConfigValidationResult(**parsed)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse config validation result: {e}")
                # Return safe default
                return ConfigValidationResult(
                    status="invalid",
                    api_base=config_data.get("api_base", "http://localhost:11434/v1"),
                    api_key=config_data.get("api_key", "ollama"),
                    model_name=config_data.get("model_name", "qwen2.5-coder:latest"),
                    temperature=0.1,
                    provider=config_data.get("provider", "ollama"),
                    errors=[f"Failed to parse validation result: {e}"]
                )

        return result

    def detect_tool_call(self, content: str) -> ToolCallDetection:
        """Detect tool calls using pure Outlines structured generation."""
        generator = self._get_generator(ToolCallDetection)

        prompt = f"""
        You are an expert at detecting tool call JSON fragments that should be filtered from a user interface.

        Analyze this content: {content}

        CRITICAL RULES - ONLY filter if content contains ALL of these:
        1. Literal string "current_code_context": "" 
        2. Literal string "code_description": 
        3. JSON structure with closing braces followed by ```

        ABSOLUTE NEVER FILTER:
        - Any content starting with ```bash, ```python, ```shell, or any code block
        - Any content containing valid shell script syntax like ((, )), if, for, function definitions
        - Any content with shebang #!/bin/bash
        - Programming code in any language
        - Any content that is clearly code, not JSON metadata

        EXAMPLES TO FILTER (must have ALL markers):
        - Content ending with: "current_code_context": "", "code_description": "some text" followed by ```

        EXAMPLES TO NEVER FILTER:
        - ```bash\\n#!/bin/bash\\nfunction_name()
        - if ((num % i == 0)); then
        - for ((i=2; i*i<=num; i++)); do
        - Any shell script content
        - Any programming code

        Be EXTREMELY CONSERVATIVE. Only filter if you are 100% certain it's a tool call JSON fragment with all required markers.
        When in doubt, DO NOT FILTER.
        """

        result = generator(prompt)
        logger.debug(f"Tool call detection raw: {result}")
        logger.debug(f"Tool call detection type: {type(result)}")

        # Parse the result if it's a string
        if isinstance(result, str):
            import json
            try:
                parsed = json.loads(result)
                # Clamp confidence to valid range
                if 'confidence' in parsed and parsed['confidence'] > 1.0:
                    parsed['confidence'] = 1.0
                elif 'confidence' in parsed and parsed['confidence'] < 0.0:
                    parsed['confidence'] = 0.0
                return ToolCallDetection(**parsed)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse detection result: {e}")
                logger.error(f"Raw result: {result}")
                # Return safe default
                return ToolCallDetection(
                    is_tool_call=False,
                    should_filter=False,
                    confidence=0.0,
                    reasoning=f"Failed to parse result: {e}"
                )

        return result

    def filter_content(self, content: str, context: str = "general") -> ContentFilterResult:
        """Filter content using Outlines structured generation."""
        # First detect if it's a tool call
        detection = self.detect_tool_call(content)

        if detection.should_filter:
            return ContentFilterResult(
                original_content=content,
                filtered_content="",
                was_filtered=True,
                filter_reason=detection.reasoning,
                confidence=detection.confidence
            )
        else:
            return ContentFilterResult(
                original_content=content,
                filtered_content=content,
                was_filtered=False,
                filter_reason=None,
                confidence=detection.confidence
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
        self.buffer = ""
        self.buffer_size_limit = 2000

    async def process_chat_stream(self, stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """Process chat stream with validation."""
        async for chunk in stream:
            # Chat mode: minimal filtering
            chunk_result = self.validator.create_streaming_chunk(chunk, "text")

            if chunk_result.should_display:
                self.debug_info.add_processed_chunk(chunk)
                yield chunk

    async def process_code_stream(self, stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """Process code assistance stream with safe chunk-by-chunk processing."""
        full_content = ""
        
        # Collect all content first
        async for chunk in stream:
            self.debug_info.add_raw_chunk(chunk)
            full_content += chunk
        
        # Process the complete content only once to avoid corrupting partial chunks
        try:
            detection = self.validator.detect_tool_call(full_content)
            
            if detection.should_filter:
                # Tool call detected - filter it out completely
                logger.debug(f"Outlines filtered tool call: {detection.reasoning}")
                # Don't yield anything
                return
            else:
                # Normal content, yield it all at once to avoid corruption
                if full_content.strip():
                    self.debug_info.add_processed_chunk(full_content)
                    yield full_content
                
        except Exception as e:
            logger.error(f"Error in Outlines detection: {e}")
            # On error, be conservative and yield everything (since we can't be sure)
            if full_content.strip():
                self.debug_info.add_processed_chunk(full_content)
                yield full_content


# Global validator instance
_validator_instance = None


def get_validator() -> OutlinesValidator:
    """Get global validator instance."""
    global _validator_instance

    if _validator_instance is None:
        model_name = os.getenv("KBG_OLLAMA_MODEL", "qwen2.5-coder:latest")
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
