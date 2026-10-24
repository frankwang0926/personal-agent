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
