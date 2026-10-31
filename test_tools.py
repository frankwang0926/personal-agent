import pytest
from tools import calculator, execute_tool, execute_tool_safely, parse_tool_arguments, validate_calculator_arguments

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

def test_execute_tool_rejects_invalid_calculator_fields():
    with pytest.raises(ValueError):
        execute_tool("calculator", {"a": "hello", "b": 3, "operation": "add"})

def test_execute_tool_safely_reports_invalid_calculator_fields():
    result = execute_tool_safely(
        "calculator", {"a": "hello", "b": 3, "operation": "add"}
    )
    assert result["ok"] is False
    assert result["error"]["type"] == "ValueError"
    assert isinstance(result["error"]["message"], str)
    assert result["error"]["message"].strip()

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
            "message": "Invalid operation. Must be one of: add, subtract, multiply, divide."
        }
    }

def test_parse_tool_arguments_valid():
    arguments_json = '{"a": 2}'
    result = parse_tool_arguments(arguments_json)
    assert result == {"a": 2}

def test_parse_tool_arguments_empty():
    arguments_json = '{}'
    result = parse_tool_arguments(arguments_json)
    assert result == {}

def test_parse_tool_arguments_invalid_json():
    arguments_json = '{bad json'
    with pytest.raises(ValueError):
        parse_tool_arguments(arguments_json)

def test_parse_tool_arguments_array():
    arguments_json = '[2, 3]'
    with pytest.raises(ValueError):
        parse_tool_arguments(arguments_json)

def test_parse_tool_arguments_null():
    arguments_json = 'null'
    with pytest.raises(ValueError):
        parse_tool_arguments(arguments_json)

def test_parse_tool_arguments_number():
    arguments_json = '42'
    with pytest.raises(ValueError):
        parse_tool_arguments(arguments_json)

def test_validate_calculator_arguments_int():
    arguments = {"a": 2, "b": 3, "operation": "add"}
    # Should not raise any exception
    assert validate_calculator_arguments(arguments) is None

def test_validate_calculator_arguments_float():
    arguments = {"a": 2.5, "b": 3.5, "operation": "add"}
    # Should not raise any exception
    assert validate_calculator_arguments(arguments) is None

def test_validate_calculator_arguments_negative():
    arguments = {"a": -2.5, "b": -3.5, "operation": "add"}
    # Should not raise any exception
    assert validate_calculator_arguments(arguments) is None

def test_validate_calculator_arguments_missing_key():
    arguments = {"a": 2, "b": 3}
    with pytest.raises(ValueError):
        validate_calculator_arguments(arguments)

def test_validate_calculator_arguments_extra_key():
    arguments = {"a": 2, "b": 3, "operation": "add", "extra": 1}
    with pytest.raises(ValueError):
        validate_calculator_arguments(arguments)

def test_validate_calculator_arguments_non_number_a():
    arguments = {"a": "not a number", "b": 3, "operation": "add"}
    with pytest.raises(ValueError):
        validate_calculator_arguments(arguments)

def test_validate_calculator_arguments_bool_b():
    arguments = {"a": 2, "b": True, "operation": "add"}
    with pytest.raises(ValueError):
        validate_calculator_arguments(arguments)

def test_validate_calculator_arguments_non_string_operation():
    arguments = {"a": 2, "b": 3, "operation": 123}
    with pytest.raises(ValueError):
        validate_calculator_arguments(arguments)

def test_validate_calculator_arguments_invalid_operation():
    arguments = {"a": 2, "b": 3, "operation": "invalid"}
    with pytest.raises(ValueError):
        validate_calculator_arguments(arguments)

def test_validate_calculator_arguments_division_by_zero():
    arguments = {"a": 2, "b": 0, "operation": "divide"}
    assert validate_calculator_arguments(arguments) is None  # This should pass validation, as the check for division by zero is done in the calculator function itself

def test_validate_calculator_arguments_no_changes_to_input():
    arguments = {"a": 2, "b": 3, "operation": "add"}
    original_arguments = arguments.copy()
    validate_calculator_arguments(arguments)
    assert arguments == original_arguments
