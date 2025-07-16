from kebogyro.mcp_adapter.tools import SimpleTool
from pydantic import BaseModel, Field

class CodeAssistantToolInput(BaseModel):
    code_description: str = Field(description="A natural language description of the code to be generated or completed.")
    current_code_context: str = Field(default="", description="Optional. The existing code snippet or context to be worked on.")

class CodeAssistantToolOutput(BaseModel):
    generated_code_snippet: str = Field(description="Structured context and guidance for code generation.")
    explanation: str = Field(default="", description="Explanation of the tool's output and next steps.")

def execute_code_assistant(inputs: CodeAssistantToolInput) -> CodeAssistantToolOutput:
    """
    Code assistant tool that prepares structured context for LLM code generation.
    
    This tool doesn't generate code itself but rather provides structured context
    that helps the LLM understand what kind of code assistance is needed.
    
    Args:
        inputs: Tool input with code description and optional context.
        
    Returns:
        Structured output that guides the LLM's code generation.
    """
    # Analyze the request and provide structured guidance
    context_info = "No existing context provided."
    if inputs.current_code_context.strip():
        context_info = f"Building upon existing context:\n{inputs.current_code_context}"
    
    # Create a structured prompt for the LLM
    structured_prompt = f"""
Code Request Analysis:
- Description: {inputs.code_description}
- Context: {context_info}
- Task: Generate appropriate code based on the description

Please provide:
1. Clean, well-commented code
2. Brief explanation of approach
3. Any relevant best practices or considerations
"""
    
    return CodeAssistantToolOutput(
        generated_code_snippet=structured_prompt,
        explanation="Structured request prepared for code generation. The LLM will use this context to generate appropriate code."
    )

code_assistant_tool = SimpleTool.from_fn(
    name="code_assistant_tool",
    description="Assists with code generation, completion, or explanation. Provides structured context to guide code generation based on natural language description and optional existing code context.",
    fn=execute_code_assistant
)

if __name__ == '__main__':
    # Example usage:
    tool_input = CodeAssistantToolInput(
        code_description="Create a python function that adds two numbers.",
        current_code_context="def my_func():\n    pass"
    )
    output = execute_code_assistant(tool_input)
    print("Tool Input:", tool_input.model_dump_json(indent=2))
    print("Tool Output:", output.model_dump_json(indent=2))

    # SimpleTool instance example
    print("\nSimpleTool instance example:")
    st_output = code_assistant_tool.call_with_string_args(
        f'{{"code_description": "Create a javascript function for alert.", "current_code_context": "console.log(\\"hello\\")"}}'
    )
    print("SimpleTool Output (raw):", st_output)
