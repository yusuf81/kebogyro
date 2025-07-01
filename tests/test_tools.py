from kebogyro.mcp_adapter.tools import SimpleTool

def echo(value: str) -> str:
    return value

def test_simpletool_schema():
    tool = SimpleTool.from_fn(
        name="echo",
        description="Echo the input value.",
        fn=echo
    )
    schema = tool.openai_schema()
    assert schema["name"] == "echo"
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
