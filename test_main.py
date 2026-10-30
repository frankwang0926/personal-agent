from types import SimpleNamespace
from unittest.mock import Mock

from main import run_agent
import json

def test_run_agent_handles_invalid_arguments():
    bad_call = SimpleNamespace(
        type="function_call",
        name="calculator",
        call_id="call_bad",
        arguments="{bad json",
    )

    good_call = SimpleNamespace(
        type="function_call",
        name="calculator",
        call_id="call_good",
        arguments='{"a": 2, "b": 3, "operation": "add"}',
    )

    first_response = SimpleNamespace(
        output=[bad_call, good_call],
        output_text="",
    )

    final_response = SimpleNamespace(
        output=[],
        output_text="Done: 5",
    )

    client = Mock()
    client.responses.create.side_effect = [
        first_response,
        final_response,
    ]

    response = run_agent(client, "2+3", max_steps=2)
    assert response == "Done: 5"
    assert client.responses.create.call_count == 2, "Expected exactly two model requests"

    second_input = client.responses.create.call_args_list[1].kwargs["input"]
    tool_outputs = [
        item
        for item in second_input
        if isinstance(item, dict)
        and item.get("type") == "function_call_output"
    ]

    assert len(tool_outputs) == 2, "Expected two tool outputs in the second input"
    assert {item["call_id"] for item in tool_outputs} == {
        "call_bad",
        "call_good",
    }

    for item in tool_outputs:
        output = json.loads(item["output"])

        if item["call_id"] == "call_bad":
            assert output["ok"] is False
            assert output["error"]["type"] == "JSONDecodeError"
        elif item["call_id"] == "call_good":
            assert output["ok"] is True
            assert output["result"] == 5







