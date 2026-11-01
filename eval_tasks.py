"""Run the five live task cases in isolated temporary working directories.

This script makes paid API requests. It never loads personal task/history files.
Results require human review; mock tests remain separate.
"""

from contextlib import redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from dotenv import load_dotenv
from openai import OpenAI

import main as agent


ROOT = Path(__file__).resolve().parent
CASES = [
    ("capture_name", "I need to call Pu.", []),
    ("infer_completion", "I just called Pu.", [
        {"id": "task-pu", "title": "Call Pu", "status": "open"},
    ]),
    ("ambiguous_reference", "Mark the call with Pu complete.", [
        {"id": "task-lunch", "title": "Call Pu about lunch", "status": "open"},
        {"id": "task-work", "title": "Call Pu about work", "status": "open"},
    ]),
    ("partial_update", "Rename Review code to Review error handling.", [
        {"id": "task-review", "title": "Review code", "status": "done"},
    ]),
    ("fresh_retrieval", "What tasks do I have?", [
        {"id": "task-groceries", "title": "Buy groceries", "status": "open"},
    ]),
]


def run_case(client, case):
    name, prompt, initial = case
    history = []
    calls = []
    requests = []
    real_execute = agent.execute_tool_safely

    def record_response(**kwargs):
        # Real request, using exactly the model/prompt selected by run_agent.
        response = client.responses.create(**kwargs)
        requests.append({
            "model": response.model,
            "status": response.status,
            "item_types": [item.type for item in response.output],
            "usage": response.usage.model_dump(mode="json") if response.usage else None,
        })
        for item in response.output:
            if item.type == "function_call":
                calls.append({"name": item.name, "arguments": item.arguments,
                              "call_id": item.call_id})
        return response

    def isolated_execute(tool_name, arguments):
        # Test fixtures use default paths inside the temporary directory. The
        # model is not permitted to redirect a tool to files outside that fixture.
        if "path" in arguments:
            return {"ok": False, "error": {
                "type": "ValueError", "message": "Evaluation cannot override storage paths."
            }}
        return real_execute(tool_name, arguments)

    proxy = SimpleNamespace(responses=SimpleNamespace(create=record_response))
    record = {"case": name, "prompt": prompt, "before": initial}
    old_directory = Path.cwd()
    with TemporaryDirectory(prefix="mini-agent-task-eval-") as directory:
        try:
            os.chdir(directory)
            Path("tasks.json").write_text(json.dumps(initial), encoding="utf-8")
            with patch.object(agent, "execute_tool_safely", isolated_execute):
                with redirect_stdout(StringIO()):
                    try:
                        record["answer"] = agent.run_agent(
                            proxy, prompt, max_steps=5, history=history
                        )
                    except Exception as error:
                        # API error strings can contain credential fragments.
                        # Record the class and status only, never the message.
                        record["error"] = {"type": type(error).__name__,
                                           "status": getattr(error, "status_code", None)}
            record["after"] = json.loads(Path("tasks.json").read_text(encoding="utf-8"))
        finally:
            os.chdir(old_directory)

    record["calls"] = calls
    record["requests"] = requests
    record["tool_results"] = [item for item in history if isinstance(item, dict)
                              and item.get("type") == "function_call_output"]
    record["review"] = "pending"
    return record


def main():
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not configured; no requests made.")

    output_directory = ROOT / "eval-results"
    output_directory.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_path = output_directory / f"tasks-{timestamp}.json"
    report = {
        "created_at_utc": timestamp,
        "instructions": agent.system_prompt,
        "prompt_sha256": sha256(agent.system_prompt.encode()).hexdigest(),
        "max_requests_per_case": 5,
        "sdk_retries": 0,
        "cases": [],
    }
    with OpenAI(timeout=60, max_retries=0) as client:
        for case in CASES:
            result = run_case(client, case)
            report["cases"].append(result)
            output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False), flush=True)
            # An infrastructure/configuration failure is not evidence about the
            # model's decisions; stop instead of repeating broken requests.
            if result.get("error", {}).get("type") in {
                "AuthenticationError", "PermissionDeniedError", "APIConnectionError",
                "APITimeoutError", "RateLimitError", "NotFoundError", "BadRequestError",
            }:
                break
    print(f"Report: {output_path}", flush=True)


if __name__ == "__main__":
    main()
