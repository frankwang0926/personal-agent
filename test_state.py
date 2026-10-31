import json

import pytest
from openai.types.responses import ResponseFunctionToolCall, ResponseReasoningItem

from state import load_history, save_history


def test_load_missing_history(tmp_path):
    assert load_history(str(tmp_path / "missing.json")) == []


def test_history_round_trip_preserves_messages_and_sdk_items(tmp_path):
    path = tmp_path / "conversation.json"
    history = [
        {"role": "user", "content": "计算 2 + 3"},
        ResponseReasoningItem(id="rs_test", summary=[], type="reasoning"),
        ResponseFunctionToolCall(
            id="fc_test",
            type="function_call",
            name="calculator",
            arguments='{"a":2,"b":3,"operation":"add"}',
            call_id="call_test",
        ),
        {"type": "function_call_output", "call_id": "call_test", "output": "5"},
        {
            "type": "message",
            "role": "assistant",
            "phase": "final_answer",
            "content": [{"type": "output_text", "text": "5", "annotations": []}],
        },
    ]

    save_history(str(path), history)
    restored = load_history(str(path))

    assert restored == [
        history[0],
        {"id": "rs_test", "summary": [], "type": "reasoning"},
        {
            "id": "fc_test",
            "type": "function_call",
            "name": "calculator",
            "arguments": '{"a":2,"b":3,"operation":"add"}',
            "call_id": "call_test",
        },
        history[3],
        history[4],
    ]
    assert "计算" in path.read_text(encoding="utf-8")


def test_load_malformed_history_raises(tmp_path):
    path = tmp_path / "conversation.json"
    path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_history(str(path))


def test_load_non_list_history_raises(tmp_path):
    path = tmp_path / "conversation.json"
    path.write_text('{"unexpected": "object"}', encoding="utf-8")

    with pytest.raises(ValueError):
        load_history(str(path))
