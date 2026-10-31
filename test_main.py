from types import SimpleNamespace
from unittest.mock import Mock
from copy import deepcopy

import pytest
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseReasoningItem,
)

import main as agent_main
from state import load_history, save_history

from main import run_agent
import json


def final_message(message_id, text):
    return ResponseOutputMessage(
        id=message_id,
        type="message",
        role="assistant",
        status="completed",
        phase="final_answer",
        content=[ResponseOutputText(type="output_text", text=text, annotations=[])],
    )


def test_run_agent_updates_supplied_empty_history():
    history = []
    message = final_message("msg_empty", "Hello")
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(
        output=[message], output_text="Hello"
    )

    assert run_agent(client, "Hi", history=history) == "Hello"
    assert history == [{"role": "user", "content": "Hi"}, message]
    assert client.responses.create.call_args.kwargs["input"] is history


def test_cli_restores_saved_tool_history_on_next_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(agent_main, "load_dotenv", lambda: None)
    prompts = iter(["Calculate 2 + 3", "What was the result?"])
    monkeypatch.setattr("builtins.input", lambda _: next(prompts))
    first_answer = final_message("msg_first", "5")
    next_answer = final_message("msg_next", "The previous result was 5")
    replies = iter([
        SimpleNamespace(
            output=[
                ResponseReasoningItem(id="rs_cli", type="reasoning", summary=[]),
                ResponseFunctionToolCall(
                    id="fc_cli", type="function_call", name="calculator",
                    arguments='{"a":2,"b":3,"operation":"add"}',
                    call_id="call_cli",
                ),
            ],
            output_text="",
        ),
        SimpleNamespace(output=[first_answer], output_text="5"),
        SimpleNamespace(output=[next_answer], output_text="The previous result was 5"),
    ])
    requests = []
    client = Mock()

    def respond(**kwargs):
        requests.append(deepcopy(kwargs))
        return next(replies)

    client.responses.create.side_effect = respond
    monkeypatch.setattr(agent_main, "OpenAI", lambda **kwargs: client)

    agent_main.main()
    first_saved = load_history("conversation.json")
    assert [item.get("type", item.get("role")) for item in first_saved] == [
        "user", "reasoning", "function_call", "function_call_output", "message"
    ]
    assert first_saved[2]["call_id"] == first_saved[3]["call_id"] == "call_cli"
    assert json.loads(first_saved[3]["output"]) == {"ok": True, "result": 5}
    assert first_saved[-1]["phase"] == "final_answer"

    agent_main.main()
    assert len(requests) == 3
    assert requests[2]["input"] == first_saved + [
        {"role": "user", "content": "What was the result?"}
    ]
    assert load_history("conversation.json") == requests[2]["input"] + [
        next_answer.model_dump(mode="json", exclude_none=True)
    ]


def test_cli_does_not_overwrite_saved_history_after_failed_turn(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(agent_main, "load_dotenv", lambda: None)
    monkeypatch.setattr(agent_main, "OpenAI", lambda **kwargs: Mock())
    monkeypatch.setattr("builtins.input", lambda _: "New request")
    path = tmp_path / "conversation.json"
    save_history(str(path), [{"role": "user", "content": "Previously saved"}])
    before = path.read_bytes()

    def fail(client, user_request, history):
        history.append({"role": "user", "content": user_request})
        raise RuntimeError("Simulated failed turn")

    monkeypatch.setattr(agent_main, "run_agent", fail)
    with pytest.raises(RuntimeError, match="Simulated failed turn"):
        agent_main.main()
    assert path.read_bytes() == before

def test_agent_recalls_memory_with_fresh_conversation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def run_memory_turn(name, arguments, prompt, answer):
        requests = []
        client = Mock()
        replies = iter([
            SimpleNamespace(
                output=[ResponseFunctionToolCall(
                    id=f"fc_{name}", type="function_call", name=name,
                    call_id=f"call_{name}", arguments=json.dumps(arguments),
                )],
                output_text="",
            ),
            SimpleNamespace(
                output=[final_message(f"msg_{name}", answer)], output_text=answer
            ),
        ])

        def respond(**kwargs):
            requests.append(deepcopy(kwargs))
            return next(replies)

        client.responses.create.side_effect = respond
        history = []
        assert run_agent(client, prompt, max_steps=2, history=history) == answer
        assert len(requests) == 2
        assert requests[0]["input"] == [{"role": "user", "content": prompt}]
        assert {tool["name"] for tool in requests[0]["tools"]} >= {
            "calculator", "remember", "recall"
        }
        results = [item for item in requests[1]["input"]
                   if isinstance(item, dict)
                   and item.get("type") == "function_call_output"]
        assert len(results) == 1
        assert results[0]["call_id"] == f"call_{name}"
        return json.loads(results[0]["output"])

    stored = run_memory_turn(
        "remember", {"key": "project_name", "value": "Mini Agent"},
        "Remember project_name as Mini Agent", "Stored",
    )
    assert stored == {"ok": True, "result": None}
    assert json.loads((tmp_path / "memory.json").read_text(encoding="utf-8")) == {
        "project_name": "Mini Agent"
    }

    retrieved = run_memory_turn(
        "recall", {"key": "project_name"},
        "Recall project_name", "Mini Agent",
    )
    assert retrieved == {"ok": True, "result": "Mini Agent"}
    assert not (tmp_path / "conversation.json").exists()


def test_agent_reports_missing_memory_and_continues(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = Mock()
    requests = []
    replies = iter([
        SimpleNamespace(output=[ResponseFunctionToolCall(
            id="fc_missing", type="function_call", name="recall",
            call_id="call_missing", arguments='{"key":"unknown"}',
        )], output_text=""),
        SimpleNamespace(output=[], output_text="No stored fact was found"),
    ])

    def respond(**kwargs):
        requests.append(deepcopy(kwargs))
        return next(replies)

    client.responses.create.side_effect = respond
    assert run_agent(client, "Recall unknown", max_steps=2) == "No stored fact was found"
    assert len(requests) == 2
    result = requests[1]["input"][-1]
    assert result["type"] == "function_call_output"
    assert result["call_id"] == "call_missing"
    payload = json.loads(result["output"])
    assert payload["ok"] is False
    assert payload["error"]["type"] == "ValueError"
    assert payload["error"]["message"]
    assert not (tmp_path / "memory.json").exists()


def test_agent_task_lifecycle_with_fresh_history(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def run_turn(prompt, calls):
        requests = []
        replies = iter([
            *[
                SimpleNamespace(
                    output=[ResponseFunctionToolCall(
                        id=f"fc_task_{index}", type="function_call", name=name,
                        call_id=f"call_task_{index}", arguments=json.dumps(arguments),
                    )],
                    output_text="",
                )
                for index, (name, arguments) in enumerate(calls)
            ],
            SimpleNamespace(output=[], output_text="Mock final response"),
        ])
        client = Mock()

        def respond(**kwargs):
            requests.append(deepcopy(kwargs))
            return next(replies)

        client.responses.create.side_effect = respond
        assert run_agent(client, prompt, history=[]) == "Mock final response"
        assert len(requests) == len(calls) + 1
        assert requests[0]["input"] == [{"role": "user", "content": prompt}]
        assert {tool["name"] for tool in requests[0]["tools"]} == {
            "calculator", "remember", "recall",
            "create_task", "list_tasks", "update_task",
        }
        outputs = [item for item in requests[-1]["input"]
                   if isinstance(item, dict)
                   and item.get("type") == "function_call_output"]
        assert [item["call_id"] for item in outputs] == [
            f"call_task_{index}" for index in range(len(calls))
        ]
        return [json.loads(item["output"]) for item in outputs]

    created = run_turn("I need to call Pu", [("create_task", {"title": "Call Pu"})])[0]
    assert created["ok"] is True
    task_id = created["result"]["id"]
    assert created["result"] == {"id": task_id, "title": "Call Pu", "status": "open"}

    listed = run_turn("What tasks do I have?", [("list_tasks", {})])[0]
    assert listed == {"ok": True, "result": [created["result"]]}

    renamed = run_turn("Rename that task to Call Pu about lunch", [
        ("list_tasks", {}),
        ("update_task", {"task_id": task_id, "title": "Call Pu about lunch", "status": None}),
    ])[-1]
    assert renamed == {"ok": True, "result": {
        "id": task_id, "title": "Call Pu about lunch", "status": "open",
    }}

    completed = run_turn("I just called Pu", [
        ("list_tasks", {}),
        ("update_task", {"task_id": task_id, "title": None, "status": "done"}),
    ])[-1]
    assert completed == {"ok": True, "result": {
        "id": task_id, "title": "Call Pu about lunch", "status": "done",
    }}
    assert json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8")) == [
        completed["result"]
    ]

    before = (tmp_path / "tasks.json").read_bytes()
    failed = run_turn("Rename the task to a blank title", [
        ("update_task", {"task_id": task_id, "title": "  ", "status": None}),
    ])[0]
    assert failed["ok"] is False
    assert failed["error"]["type"] == "ValueError"
    assert (tmp_path / "tasks.json").read_bytes() == before
    assert not (tmp_path / "conversation.json").exists()
    assert not (tmp_path / "memory.json").exists()


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







