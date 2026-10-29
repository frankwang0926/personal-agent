import json


def calculator(a: float, b: float, operation: str) -> float:
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ZeroDivisionError("Denominator cannot be zero")
        return a / b
    else:
        raise ValueError("Invalid operation")

TOOL_REGISTRY = {"calculator": calculator}

def execute_tool(tool_name: str, arguments: dict):
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Tool '{tool_name}' is not registered.")
    
    tool_function = TOOL_REGISTRY[tool_name]
    return tool_function(**arguments)

def execute_tool_safely(tool_name: str, arguments: dict) -> dict:
    try:
        result = execute_tool(tool_name, arguments)
        return {"ok": True, "result": result}
    except (ValueError, ZeroDivisionError) as e:
        return {
            "ok": False, 
            "error": {
                "type": type(e).__name__, 
                "message": str(e)
            }
        }

def parse_tool_arguments(arguments_json: str) -> dict:
    arguments = json.loads(arguments_json)
    if isinstance(arguments, dict):
        return arguments
    else:
        raise ValueError("Tool arguments must be a JSON object.")


CALCULATOR_TOOL = {
    "type": "function",
    "name": "calculator",
    "description": "A simple calculator that can perform basic arithmetic operations.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "The first number."},
            "b": {"type": "number", "description": "The second number."},
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "The arithmetic operation to perform."
            }
        },
        "required": ["a", "b", "operation"],
        "additionalProperties": False
    }
}


