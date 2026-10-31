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

    if tool_name == "calculator":
        validate_calculator_arguments(arguments)
        
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

def validate_calculator_arguments(arguments: dict) -> None:
    if len(arguments) != 3:
        raise ValueError("Calculator requires exactly three arguments: a, b, and operation.")

    if not all(key in arguments for key in ["a", "b", "operation"]):
        raise ValueError("Missing required arguments for calculator: a, b, and operation.")

    if not isinstance(arguments["a"], (int, float)) or isinstance(arguments["a"], bool):
        raise ValueError("Argument 'a' must be a number.")

    if not isinstance(arguments["b"], (int, float)) or isinstance(arguments["b"], bool):
        raise ValueError("Argument 'b' must be a number.")

    if not isinstance(arguments["operation"], str):
        raise ValueError("Argument 'operation' must be a string.")

    if arguments["operation"] not in {"add", "subtract", "multiply", "divide"}:
        raise ValueError("Invalid operation. Must be one of: add, subtract, multiply, divide.")

    

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


