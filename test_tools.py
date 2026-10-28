import pytest
from tools import calculator, execute_tool, execute_tool_safely

def test_add_positive():
    assert calculator(2, 3, "add") == 5

def test_add_negative():
    assert calculator(-1, -1, "add") == -2

def test_subtract():
    assert calculator(5, 3, "subtract") == 2

def test_multiply():
    assert calculator(2, 3, "multiply") == 6

def test_divide():
    assert calculator(10, 2, "divide") == 5

def test_nonexistent_operation():
    with pytest.raises(ValueError):
        calculator(10, 2, "power")

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        calculator(10, 0, "divide")

def test_execute_tool_calculator():
    assert execute_tool("calculator", {"a": 2, "b": 3, "operation": "add"}) == 5

def test_execute_tool_invalid_tool():
    with pytest.raises(ValueError):
        execute_tool("nonexistent_tool", {"a": 2, "b": 3, "operation": "add"})

def test_execute_tool_calculator_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        execute_tool("calculator", {"a": 10, "b": 0, "operation": "divide"})

def test_execute_tool_safely_calculator():
    result = execute_tool_safely("calculator", {"a": 2, "b": 3, "operation": "add"})
    assert result == {"ok": True, "result": 5}

def test_execute_tool_safely_calculator_divide_by_zero():
    result = execute_tool_safely("calculator", {"a": 10, "b": 0, "operation": "divide"})
    assert result == {
        "ok": False,
        "error": {
            "type": "ZeroDivisionError",
            "message": "Denominator cannot be zero"
        }
    }

def test_execute_tool_safely_invalid_tool():
    result = execute_tool_safely("nonexistent_tool", {"a": 2, "b": 3, "operation": "add"})
    assert result == {
        "ok": False,
        "error": {
            "type": "ValueError",
            "message": "Tool 'nonexistent_tool' is not registered."
        }
    }

def test_execute_tool_safely_invalid_operation():
    result = execute_tool_safely("calculator", {"a": 2, "b": 3, "operation": "power"})
    assert result == {
        "ok": False,
        "error": {
            "type": "ValueError",
            "message": "Invalid operation"
        }
    }